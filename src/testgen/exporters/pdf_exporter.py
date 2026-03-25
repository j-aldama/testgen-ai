"""Export test cases to PDF via Markdown → HTML → PDF (xhtml2pdf, pure Python)."""

from __future__ import annotations

import io
from pathlib import Path

import markdown
from xhtml2pdf import pisa

from testgen.config import GenerationResult
from testgen.exporters.markdown_exporter import render_markdown

_PDF_CSS = """\
@page {
  size: A4;
  margin: 2cm 1.5cm;
}
body {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10pt;
  line-height: 1.6;
  color: #1a1a1a;
}
h1 {
  font-size: 20pt;
  color: #1e3a5f;
  border-bottom: 2pt solid #3182ce;
  padding-bottom: 4pt;
}
h2 {
  font-size: 14pt;
  color: #1e3a5f;
  border-bottom: 1pt solid #3182ce;
  padding-bottom: 3pt;
  margin-top: 18pt;
}
h3 {
  font-size: 12pt;
  color: #2c5282;
  margin-top: 14pt;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 8pt 0;
  font-size: 9pt;
}
th {
  background-color: #2c5282;
  color: white;
  padding: 6pt 8pt;
  text-align: left;
  font-weight: bold;
  font-size: 8pt;
}
td {
  padding: 5pt 8pt;
  border-bottom: 1pt solid #e2e8f0;
  vertical-align: top;
}
tr:nth-child(even) td {
  background-color: #f7fafc;
}
code {
  background-color: #edf2f7;
  padding: 1pt 4pt;
  border-radius: 2pt;
  font-family: Courier, monospace;
  font-size: 8pt;
}
hr {
  border: none;
  border-top: 1pt solid #e2e8f0;
  margin: 12pt 0;
}
strong {
  color: #2c5282;
}
ul, ol {
  margin: 4pt 0;
  padding-left: 16pt;
}
li {
  margin-bottom: 2pt;
}
"""


def export_pdf(result: GenerationResult, output_path: str | Path) -> Path:
    """Export generation result to PDF.

    Flow: render_markdown() → markdown lib (MD→HTML) → xhtml2pdf (HTML→PDF)
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Render markdown (reuse existing exporter)
    md_content = render_markdown(result)

    # Step 2: Convert markdown to HTML
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code"],
    )

    # Step 3: Wrap in full HTML with CSS
    html_full = f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{_PDF_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # Step 4: Convert HTML to PDF
    with open(str(path), "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(io.BytesIO(html_full.encode("utf-8")), dest=pdf_file)

    if pisa_status.err:
        raise RuntimeError(f"PDF generation failed with {pisa_status.err} errors")

    return path


# Backward compat
def render_pdf_html(result: GenerationResult) -> str:
    return ""


def _build_traceability_map(result: GenerationResult) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for tc in result.test_cases:
        mapping.setdefault(tc.traceability, []).append(tc.id)
    return mapping
