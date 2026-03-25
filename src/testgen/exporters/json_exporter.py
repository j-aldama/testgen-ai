"""Export test cases to JSON format."""

from __future__ import annotations

import json
from pathlib import Path

from testgen.config import GenerationResult


def export_json(result: GenerationResult, output_path: str | Path) -> Path:
    """Export generation result to a JSON file.

    Args:
        result: The generation result containing test cases.
        output_path: Path for the output JSON file.

    Returns:
        Path to the created file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "session_id": result.session_id,
        "summary": result.summary,
        "requirements": [r.to_dict() for r in result.requirements],
        "test_cases": [tc.to_dict() for tc in result.test_cases],
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def to_json_string(result: GenerationResult) -> str:
    """Convert generation result to a JSON string."""
    data = {
        "session_id": result.session_id,
        "summary": result.summary,
        "requirements": [r.to_dict() for r in result.requirements],
        "test_cases": [tc.to_dict() for tc in result.test_cases],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
