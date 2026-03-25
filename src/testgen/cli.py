"""Typer + Rich CLI for TestGen."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from testgen.config import (
    GenerationResult,
    ISTQBTechnique,
    STEP_FORMAT_MAP,
    StepFormat,
    TECHNIQUE_SHORT_MAP,
    get_settings,
)
from testgen.exporters.json_exporter import export_json
from testgen.exporters.markdown_exporter import export_markdown
from testgen.exporters.pdf_exporter import export_pdf
from testgen.exporters.xlsx_exporter import export_xlsx
from testgen.generator.llm_client import create_llm_client
from testgen.generator.test_case_generator import TestCaseGenerator
from testgen.parser.file_parser import parse_file
from testgen.parser.text_parser import parse_requirements

app = typer.Typer(
    name="testgen",
    help="AI-powered test case generator using ISTQB techniques.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()

EXPORT_FORMATS = {"md", "pdf", "xlsx", "json", "all"}


def _resolve_techniques(raw: str | None) -> list[ISTQBTechnique] | None:
    """Parse comma-separated technique short names into enum values."""
    if not raw:
        return None
    result: list[ISTQBTechnique] = []
    for part in raw.split(","):
        key = part.strip().lower()
        if key in TECHNIQUE_SHORT_MAP:
            result.append(TECHNIQUE_SHORT_MAP[key])
        else:
            console.print(f"[yellow]Warning: unknown technique '{key}', skipping.[/yellow]")
    return result or None


def _display_results(result: GenerationResult) -> None:
    """Display generated test cases in a Rich table."""
    summary = result.summary

    # Summary panel
    summary_text = (
        f"[bold]Total:[/bold] {summary['total']} test cases\n"
        f"[bold]Requirements:[/bold] {summary['requirements_count']}\n"
        f"[bold]Priority:[/bold] {', '.join(f'{k}: {v}' for k, v in summary.get('by_priority', {}).items())}\n"
        f"[bold]Types:[/bold] {', '.join(f'{k}: {v}' for k, v in summary.get('by_type', {}).items())}"
    )
    console.print(Panel(summary_text, title="Generation Summary", border_style="blue"))

    # Test cases table
    table = Table(title="Generated Test Cases", show_lines=True)
    table.add_column("ID", style="bold cyan", width=8)
    table.add_column("Title", style="white", max_width=40)
    table.add_column("Priority", justify="center", width=10)
    table.add_column("Type", width=14)
    table.add_column("Technique", width=25)
    table.add_column("Trace", width=10)

    priority_colors = {"High": "red", "Medium": "yellow", "Low": "green"}

    for tc in result.test_cases:
        p_color = priority_colors.get(tc.priority.value, "white")
        table.add_row(
            tc.id,
            tc.title,
            f"[{p_color}]{tc.priority.value}[/{p_color}]",
            tc.type.value,
            tc.istqb_technique.value,
            tc.traceability,
        )

    console.print(table)


def _export_result(
    result: GenerationResult,
    fmt: str,
    output: str | None,
    output_dir: str | None,
) -> None:
    """Export the result in the specified format(s)."""
    if fmt == "all":
        base_dir = Path(output_dir) if output_dir else Path("./output")
        base_dir.mkdir(parents=True, exist_ok=True)
        base_name = f"test-cases-{result.session_id}"

        formats_and_funcs = [
            ("md", export_markdown),
            ("json", export_json),
            ("xlsx", export_xlsx),
        ]

        for ext, func in formats_and_funcs:
            out_path = base_dir / f"{base_name}.{ext}"
            func(result, out_path)
            console.print(f"[green]Exported:[/green] {out_path}")

        # PDF separately (may fail if WeasyPrint not installed)
        try:
            pdf_path = base_dir / f"{base_name}.pdf"
            export_pdf(result, pdf_path)
            console.print(f"[green]Exported:[/green] {pdf_path}")
        except ImportError:
            console.print("[yellow]PDF export skipped (WeasyPrint not installed).[/yellow]")

        return

    # Single format
    ext_map = {
        "md": (".md", export_markdown),
        "pdf": (".pdf", export_pdf),
        "xlsx": (".xlsx", export_xlsx),
        "json": (".json", export_json),
    }

    if fmt not in ext_map:
        console.print(f"[red]Unknown format: {fmt}[/red]")
        raise typer.Exit(1)

    ext, func = ext_map[fmt]
    out_path = Path(output) if output else Path(f"test-cases-{result.session_id}{ext}")
    func(result, out_path)
    console.print(f"[green]Exported:[/green] {out_path}")


@app.command()
def generate(
    text: Annotated[
        Optional[str],
        typer.Argument(help="Requirements text to generate test cases from."),
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Input file (.txt, .md, .pdf)."),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: md, pdf, xlsx, json, all."),
    ] = "md",
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output file path."),
    ] = None,
    output_dir: Annotated[
        Optional[str],
        typer.Option("--output-dir", help="Output directory (for --format all)."),
    ] = None,
    techniques: Annotated[
        Optional[str],
        typer.Option("--techniques", "-t", help="Comma-separated: ep,bva,dt,st,eg"),
    ] = None,
    priority: Annotated[
        Optional[str],
        typer.Option("--priority", "-p", help="Filter: high,medium,low"),
    ] = None,
    types: Annotated[
        Optional[str],
        typer.Option("--types", help="Filter: functional,negative,boundary,security"),
    ] = None,
    step_format: Annotated[
        str,
        typer.Option("--step-format", help="Step format: gwt (Given/When/Then) or ser (Step/Expected Result)."),
    ] = "gwt",
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Number of test cases per requirement (3-15)."),
    ] = 5,
) -> None:
    """Generate test cases from requirements text or file."""
    if not text and not file:
        console.print("[red]Error: Provide requirements text or --file.[/red]")
        raise typer.Exit(1)

    if format not in EXPORT_FORMATS:
        console.print(f"[red]Error: Invalid format '{format}'. Use: {', '.join(EXPORT_FORMATS)}[/red]")
        raise typer.Exit(1)

    # Parse requirements
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing requirements...", total=None)
        if file:
            requirements = parse_file(file)
        else:
            requirements = parse_requirements(text or "")
        progress.update(task, description=f"Found {len(requirements)} requirements")

    if not requirements:
        console.print("[red]No requirements found in the input.[/red]")
        raise typer.Exit(1)

    # Show parsed requirements
    req_table = Table(title="Parsed Requirements")
    req_table.add_column("ID", style="bold")
    req_table.add_column("Text", max_width=70)
    for req in requirements:
        req_table.add_row(req.id, req.text[:100])
    console.print(req_table)

    # Parse options
    technique_list = _resolve_techniques(techniques)
    priority_list = [p.strip().capitalize() for p in priority.split(",")] if priority else None
    type_list = [t.strip().capitalize() for t in types.split(",")] if types else None
    resolved_step_format = STEP_FORMAT_MAP.get(step_format.lower(), StepFormat.GWT)

    # Generate test cases
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating test cases with AI...", total=None)

        settings = get_settings()
        try:
            llm_client = create_llm_client(settings)
        except (ValueError, ImportError) as exc:
            console.print(f"[red]Error: {exc}[/red]")
            raise typer.Exit(1) from exc

        generator = TestCaseGenerator(llm_client)
        result = generator.generate(
            requirements,
            techniques=technique_list,
            priorities=priority_list,
            types=type_list,
            step_format=resolved_step_format,
            tc_per_req=max(3, min(15, count)),
        )
        progress.update(task, description=f"Generated {len(result.test_cases)} test cases")

    # Display results
    _display_results(result)

    # Export
    _export_result(result, format, output, output_dir)


@app.command()
def serve(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to run the web server on."),
    ] = 8000,
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to."),
    ] = "0.0.0.0",
) -> None:
    """Start the TestGen web UI."""
    console.print(
        Panel(
            f"Starting TestGen Web UI at [bold]http://{host}:{port}[/bold]\n"
            "Press Ctrl+C to stop.",
            title="TestGen Web Server",
            border_style="green",
        )
    )
    try:
        import uvicorn
        uvicorn.run(
            "testgen.web.app:app",
            host=host,
            port=port,
            reload=False,
        )
    except ImportError:
        console.print("[red]uvicorn is required. Install with: pip install uvicorn[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
