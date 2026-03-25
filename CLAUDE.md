# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is TestGen

AI-powered test case generator that takes requirements (text, user stories, PRDs, Gherkin) and produces ISTQB-aligned test cases. Exports to Markdown, PDF, Excel, and JSON. Offers both a Typer CLI and a FastAPI + HTMX web interface.

## Commands

```bash
# Install (editable with dev deps)
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run a single test file or class
pytest tests/test_generator.py -v
pytest tests/test_generator.py::TestParseRawTestCases -v

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/testgen/ --ignore-missing-imports

# CLI usage (requires TESTGEN_ANTHROPIC_API_KEY in .env)
testgen generate "requirement text"
testgen generate --file requirements.md --format xlsx --output test-cases.xlsx

# Web UI
testgen serve --port 8000

# Docker
docker compose up
```

## Architecture

The pipeline flows: **Input parsing -> LLM generation -> ISTQB technique enrichment -> Export**.

### Core data model (`config.py`)
- `Requirement`, `TestCase`, `Step`, `GenerationResult` are dataclasses
- `Priority`, `TestType`, `ISTQBTechnique` are `StrEnum`s
- `Settings` uses pydantic-settings with `TESTGEN_` env prefix

### Pipeline (`generator/`)
- `TestCaseGenerator` orchestrates: sends requirements to LLM, parses JSON response into `TestCase` objects, then optionally enriches with `apply_techniques()`
- `LLMClient` wraps the Anthropic SDK; expects raw JSON array from Claude (no markdown fences), with fallback parsing via regex
- `techniques.py` has deterministic (non-LLM) implementations of EP, BVA, Decision Table, State Transition, and Error Guessing that generate additional test cases by analyzing requirement text with regex

### Parsers (`parser/`)
- `text_parser.py`: detects format (gherkin, structured, freeform) and splits text into `Requirement` objects
- `file_parser.py`: handles .txt, .md, .pdf (via PyMuPDF) file reading

### Exporters (`exporters/`)
Each exporter takes a `GenerationResult` and writes to a file path. PDF uses WeasyPrint (requires system libs: libpango, libpangocairo, libgdk-pixbuf). XLSX uses openpyxl with 3 sheets (Summary, Test Cases, Traceability). Markdown uses Jinja2.

### Web (`web/app.py`)
FastAPI app with HTMX. In-memory session storage (`_sessions` dict, max 100). HTMX partial responses for test case editing. Download endpoints generate files in-memory via tempfiles.

## Testing

Tests mock the LLM client (`MagicMock(spec=LLMClient)`) — no real API calls needed. `conftest.py` provides shared fixtures: `sample_requirements`, `sample_test_cases`, `sample_generation_result`. pytest-asyncio is configured with `asyncio_mode = "auto"`.

## Config

All settings via env vars with `TESTGEN_` prefix (see `.env.example`). Key ones:
- `TESTGEN_ANTHROPIC_API_KEY` (required for real generation)
- `TESTGEN_ANTHROPIC_MODEL` (default: claude-sonnet-4-20250514)
- `TESTGEN_MAX_TOKENS`, `TESTGEN_TEMPERATURE`

## Ruff config

`line-length = 100`, `target-version = "py312"`, lint rules: `E, F, W, I, N, UP, B, SIM`.
