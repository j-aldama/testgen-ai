"""Parse raw text input into structured requirements."""

from __future__ import annotations

import re

from testgen.config import Requirement


_REQUIREMENT_PATTERNS = [
    # Numbered requirements: "1. The system shall...", "1) The user must..."
    re.compile(r"^\s*\d+[\.\)]\s+(.+)", re.MULTILINE),
    # Bullet points: "- The system shall...", "* The user must..."
    re.compile(r"^\s*[-*]\s+(.+)", re.MULTILINE),
    # User stories: "As a ... I want ... so that ..."
    re.compile(r"(As an?\s+.+?(?:so that\s+.+?)?\.)", re.IGNORECASE | re.DOTALL),
    # "REQ-XXX:" or "FR-XXX:" prefixed
    re.compile(r"^\s*(?:REQ|FR|NFR|US)-?\d+[:\s]+(.+)", re.MULTILINE | re.IGNORECASE),
]

_SENTENCE_SPLITTER = re.compile(r"(?<=[.!])\s+(?=[A-Z])")

_GHERKIN_PATTERN = re.compile(
    r"(?:Feature|Scenario|Given|When|Then|And|But)\s*[:\s]",
    re.IGNORECASE,
)


def detect_format(text: str) -> str:
    """Detect the input format of the text."""
    if _GHERKIN_PATTERN.search(text):
        return "gherkin"
    for pattern in _REQUIREMENT_PATTERNS[:2]:
        if pattern.search(text):
            return "structured"
    return "freeform"


def parse_requirements(text: str, source: str = "user_input") -> list[Requirement]:
    """Parse input text into a list of individual requirements.

    Supports numbered lists, bullet points, user stories, requirement IDs,
    Gherkin scenarios, and plain sentences.
    """
    text = text.strip()
    if not text:
        return []

    fmt = detect_format(text)

    if fmt == "gherkin":
        return _parse_gherkin(text, source)

    requirements: list[Requirement] = []
    seen_texts: set[str] = set()

    # Try structured patterns first
    for pattern in _REQUIREMENT_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            clean = match.strip().rstrip(".")
            if clean and clean not in seen_texts and len(clean) > 10:
                seen_texts.add(clean)
                req_id = f"REQ-{len(requirements) + 1:03d}"
                requirements.append(Requirement(id=req_id, text=clean, source=source))

    # If no structured patterns matched, split by sentences
    if not requirements:
        requirements = _parse_freeform(text, source)

    return requirements


def _parse_gherkin(text: str, source: str) -> list[Requirement]:
    """Parse Gherkin-formatted text into requirements."""
    requirements: list[Requirement] = []
    scenario_pattern = re.compile(
        r"(?:Scenario(?:\s+Outline)?)\s*:\s*(.+?)(?=\n\s*Scenario|\n\s*Feature|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    scenarios = scenario_pattern.findall(text)

    if scenarios:
        for i, scenario in enumerate(scenarios, 1):
            clean = scenario.strip()
            if clean:
                # Take just the first line as the title, rest as the body
                lines = clean.split("\n")
                title = lines[0].strip()
                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else title
                full_text = f"{title}: {body}" if body != title else title
                req_id = f"REQ-{i:03d}"
                requirements.append(Requirement(id=req_id, text=full_text, source=source))
    else:
        # Treat the whole Gherkin block as one requirement
        requirements.append(Requirement(id="REQ-001", text=text, source=source))

    return requirements


def _parse_freeform(text: str, source: str) -> list[Requirement]:
    """Parse freeform text by splitting into sentences."""
    requirements: list[Requirement] = []

    # Split by double newlines first (paragraphs)
    paragraphs = re.split(r"\n\s*\n", text)

    if len(paragraphs) > 1:
        for i, para in enumerate(paragraphs, 1):
            clean = para.strip()
            if clean and len(clean) > 10:
                req_id = f"REQ-{i:03d}"
                requirements.append(Requirement(id=req_id, text=clean, source=source))
    else:
        # Split by sentences
        sentences = _SENTENCE_SPLITTER.split(text)
        for i, sentence in enumerate(sentences, 1):
            clean = sentence.strip()
            if clean and len(clean) > 10:
                req_id = f"REQ-{i:03d}"
                requirements.append(Requirement(id=req_id, text=clean, source=source))

    # If still nothing, treat the whole text as one requirement
    if not requirements and len(text) > 10:
        requirements.append(Requirement(id="REQ-001", text=text, source=source))

    return requirements
