# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is TestGen

AI-powered test case generator that takes requirements (text, user stories, PRDs, Gherkin) and produces ISTQB-aligned test cases. Supports multiple LLM providers (Anthropic, OpenAI, Ollama). Exports to Markdown, PDF, Excel, and JSON. Offers both a Typer CLI and a FastAPI + HTMX web interface with dark/light mode and EN/ES i18n.

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

# CLI usage (requires API key in .env)
testgen generate "requirement text"
testgen generate --file requirements.md --format xlsx --output test-cases.xlsx
testgen generate --step-format ser --count 10

# Web UI
testgen serve --port 8000

# Docker
docker compose up
```

## Architecture

The pipeline flows: **Input parsing -> LLM generation -> ISTQB technique enrichment -> Export**.

### Core data model (`config.py`)
- `Requirement`, `TestCase`, `Step`, `GenerationResult` are dataclasses
- `Priority`, `TestType`, `ISTQBTechnique`, `StepFormat` are `StrEnum`s
- `Settings` uses pydantic-settings with `TESTGEN_` env prefix
- `Step` supports two formats: GWT (given/when/then) and SER (step/expected)

### LLM Client (`generator/llm_client.py`)
- `BaseLLMClient` ABC with `generate()` method
- `AnthropicLLMClient` wraps Anthropic SDK
- `OpenAILLMClient` wraps OpenAI SDK (also works with Ollama, LM Studio via `base_url`)
- `create_llm_client(settings)` factory selects provider based on `TESTGEN_LLM_PROVIDER`
- `parse_json_response()` handles markdown fences, wrapped objects, regex fallback

### Pipeline (`generator/`)
- `TestCaseGenerator` orchestrates: builds system prompt (language-aware, step format, count), sends to LLM, parses JSON into `TestCase` objects, enriches with `apply_techniques()`
- `prompts.py`: `build_system_prompt(step_format, tc_per_req)` generates the prompt dynamically. Rule #9 forces same-language output. User prompt also reinforces language matching.
- `techniques.py` has deterministic (non-LLM) implementations of EP, BVA, Decision Table, State Transition, Error Guessing. Uses `_make_step()` helper to create steps in the correct format.

### Parsers (`parser/`)
- `text_parser.py`: detects format (gherkin, structured, freeform) and splits text into `Requirement` objects. Gherkin detection requires keywords at start of line to avoid false positives with "and"/"then" in normal text.
- `file_parser.py`: handles .txt, .md, .pdf (via PyMuPDF) file reading

### Exporters (`exporters/`)
- Each exporter takes a `GenerationResult` and writes to a file path
- PDF uses MD->HTML->xhtml2pdf pipeline (pure Python, full Unicode, no system deps)
- XLSX uses openpyxl with 3 sheets (Summary, Test Cases, Traceability). Column layout adapts to step format.
- Markdown uses Jinja2 with conditional step format rendering
- All exporters read `result.step_format` to render GWT or SER steps

### Web (`web/app.py`)
- FastAPI app with HTMX. In-memory session storage (`_sessions` dict, max 100)
- HTMX partial responses for test case editing. Download endpoints generate files in-memory via tempfiles.
- Dark/light mode via Tailwind `class` strategy + localStorage
- EN/ES i18n via client-side JS translation dict (`data-i18n` attributes)
- Supports `?theme=dark&lang=es` query params for screenshots/automation
- Loading state on generate button prevents double-click

## Testing

Tests mock the LLM client (`MagicMock(spec=BaseLLMClient)`) — no real API calls needed. `conftest.py` provides shared fixtures: `sample_requirements`, `sample_test_cases`, `sample_generation_result`. pytest-asyncio configured with `asyncio_mode = "auto"`.

## Config

All settings via env vars with `TESTGEN_` prefix (see `.env.example`):
- `TESTGEN_LLM_PROVIDER` — `anthropic` (default) or `openai`
- `TESTGEN_ANTHROPIC_API_KEY`, `TESTGEN_ANTHROPIC_MODEL`
- `TESTGEN_OPENAI_API_KEY`, `TESTGEN_OPENAI_MODEL`, `TESTGEN_OPENAI_BASE_URL`
- `TESTGEN_MAX_TOKENS`, `TESTGEN_TEMPERATURE`

## Ruff config

`line-length = 100`, `target-version = "py312"`, lint rules: `E, F, W, I, N, UP, B, SIM`.
