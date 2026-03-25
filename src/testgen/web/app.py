"""FastAPI web application with HTMX for TestGen."""

from __future__ import annotations

import io
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from testgen.config import (
    GenerationResult,
    ISTQBTechnique,
    STEP_FORMAT_MAP,
    StepFormat,
    TECHNIQUE_SHORT_MAP,
    get_settings,
)
from testgen.exporters.json_exporter import to_json_string
from testgen.exporters.markdown_exporter import render_markdown
from testgen.exporters.pdf_exporter import export_pdf
from testgen.exporters.xlsx_exporter import export_xlsx
from testgen.generator.llm_client import create_llm_client
from testgen.generator.test_case_generator import TestCaseGenerator
from testgen.parser.text_parser import parse_requirements

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(title="TestGen", version="1.0.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory session storage for generated results
MAX_SESSIONS = 100
_sessions: dict[str, GenerationResult] = {}

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "techniques": [
            ("ep", "Equivalence Partitioning"),
            ("bva", "Boundary Value Analysis"),
            ("dt", "Decision Table"),
            ("st", "State Transition"),
            ("eg", "Error Guessing"),
        ],
        "priorities": ["High", "Medium", "Low"],
        "types": ["Functional", "Negative", "Boundary", "Security", "Performance", "Accessibility"],
        "step_formats": [("gwt", "Given / When / Then"), ("ser", "Step / Expected Result")],
    })


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    requirements_text: str = Form(...),
    techniques: list[str] = Form(default=[]),
    priorities: list[str] = Form(default=[]),
    types: list[str] = Form(default=[]),
    step_format: str = Form(default="gwt"),
    tc_per_req: int = Form(default=5),
) -> HTMLResponse:
    """Generate test cases from submitted requirements."""
    if not requirements_text.strip():
        raise HTTPException(status_code=400, detail="Requirements text is required.")

    # Parse requirements
    requirements = parse_requirements(requirements_text)
    if not requirements:
        raise HTTPException(status_code=400, detail="No requirements could be parsed from the input.")

    # Resolve techniques
    technique_list: list[ISTQBTechnique] | None = None
    if techniques:
        technique_list = [
            TECHNIQUE_SHORT_MAP[t]
            for t in techniques
            if t in TECHNIQUE_SHORT_MAP
        ]

    # Resolve step format
    resolved_step_format = STEP_FORMAT_MAP.get(step_format.lower(), StepFormat.GWT)

    # Generate test cases
    settings = get_settings()
    try:
        llm_client = create_llm_client(settings)
        generator = TestCaseGenerator(llm_client)
        result = generator.generate(
            requirements,
            techniques=technique_list or None,
            priorities=priorities or None,
            types=types or None,
            step_format=resolved_step_format,
            tc_per_req=max(3, min(15, tc_per_req)),
        )
    except (ValueError, ImportError) as exc:
        logger.error("Generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Evict oldest sessions if at capacity
    if len(_sessions) >= MAX_SESSIONS:
        oldest_key = next(iter(_sessions))
        del _sessions[oldest_key]

    # Store in session
    _sessions[result.session_id] = result

    return templates.TemplateResponse("results.html", {
        "request": request,
        "result": result,
        "test_cases": result.test_cases,
        "summary": result.summary,
        "session_id": result.session_id,
        "step_format": result.step_format,
    })


@app.get("/results/{session_id}", response_class=HTMLResponse)
async def results(request: Request, session_id: str) -> HTMLResponse:
    """View results for a specific session."""
    result = _sessions.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found.")

    return templates.TemplateResponse("results_page.html", {
        "request": request,
        "result": result,
        "test_cases": result.test_cases,
        "summary": result.summary,
        "session_id": session_id,
        "step_format": result.step_format,
    })


@app.post("/update-test-case/{session_id}/{tc_id}", response_class=HTMLResponse)
async def update_test_case(
    request: Request,
    session_id: str,
    tc_id: str,
    title: str = Form(...),
    priority: str = Form(...),
    expected_result: str = Form(...),
) -> HTMLResponse:
    """Update a test case (HTMX partial response)."""
    result = _sessions.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found.")

    for tc in result.test_cases:
        if tc.id == tc_id:
            tc.title = title
            from testgen.config import Priority
            for p in Priority:
                if p.value.lower() == priority.lower():
                    tc.priority = p
                    break
            tc.expected_result = expected_result
            break

    return templates.TemplateResponse("partials/test_cases_table.html", {
        "request": request,
        "test_cases": result.test_cases,
        "session_id": session_id,
        "step_format": result.step_format,
    })


@app.get("/download/{session_id}/{fmt}")
async def download(session_id: str, fmt: str) -> StreamingResponse:
    """Download test cases in the specified format."""
    result = _sessions.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found.")

    filename = f"test-cases-{session_id}"

    if fmt == "md":
        content = render_markdown(result)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}.md"},
        )

    if fmt == "json":
        content = to_json_string(result)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )

    if fmt == "xlsx":
        buf = io.BytesIO()
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            export_xlsx(result, tmp.name)
            tmp_path = Path(tmp.name)
        data = tmp_path.read_bytes()
        tmp_path.unlink()
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )

    if fmt == "pdf":
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            export_pdf(result, tmp.name)
            tmp_path = Path(tmp.name)
        data = tmp_path.read_bytes()
        tmp_path.unlink()
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
        )

    raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}
