"""Parse various file formats into raw text for requirement extraction."""

from __future__ import annotations

from pathlib import Path

from testgen.config import Requirement
from testgen.parser.text_parser import parse_requirements


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def parse_file(file_path: str | Path) -> list[Requirement]:
    """Parse a file and extract requirements from its content.

    Supports .txt, .md, and .pdf files.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    text = _extract_text(path)
    source = path.name
    return parse_requirements(text, source=source)


def _extract_text(path: Path) -> str:
    """Extract raw text from a file based on its extension."""
    ext = path.suffix.lower()

    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8")

    if ext == ".pdf":
        return _extract_pdf_text(path)

    raise ValueError(f"No extractor for: {ext}")


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF is required for PDF parsing. Install with: pip install pymupdf"
        ) from exc

    doc = fitz.open(str(path))
    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return "\n\n".join(pages_text)
