import os
import re
import subprocess
import tempfile


def generate_pdf(latex_code: str, sections: list) -> bytes:
    """
    Compiles LaTeX source via pdflatex and returns the resulting PDF as bytes.

    Strategy:
      - If latex_code is a complete LaTeX document (has \\documentclass), compile it directly.
      - If only sections are available (no full document), wrap them in a minimal template first.
      - pdflatex is run twice so cross-references and page numbers resolve correctly.
      - All temp files are cleaned up automatically after compilation.

    Args:
        latex_code: full LaTeX string from Gemini (may or may not be a complete document)
        sections:   list of {"title": str, "content": str} — used as fallback if needed

    Returns:
        PDF file as bytes

    Raises:
        RuntimeError: if pdflatex fails (stderr included in message for debugging)
    """

    # ── Step 1: Decide what LaTeX source to compile ──
    if _is_complete_document(latex_code):
        # Gemini returned a full document — compile it as-is
        source = latex_code
    elif sections:
        # Gemini returned sections without a document wrapper — build one
        source = _wrap_sections_in_template(sections)
    else:
        # Last resort: wrap whatever raw text we have
        source = _wrap_plain_text(latex_code)

    # ── Step 2: Write .tex to a temp dir and compile ──
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "output.tex")
        pdf_path = os.path.join(tmpdir, "output.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(source)

        # Run pdflatex twice — needed for correct page numbers / references
        for _ in range(2):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",   # don't pause on errors
                    "-output-directory", tmpdir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=60                        # safety timeout (seconds)
            )

        # ── Step 3: Check output exists ──
        if not os.path.exists(pdf_path):
            # Dump pdflatex log for debugging
            log_path = os.path.join(tmpdir, "output.log")
            log_text = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                    log_text = lf.read()[-3000:]   # last 3000 chars is usually the relevant error

            raise RuntimeError(
                f"pdflatex failed — PDF not produced.\n"
                f"STDERR:\n{result.stderr[-1000:]}\n"
                f"LOG (tail):\n{log_text}"
            )

        # ── Step 4: Read and return PDF bytes ──
        with open(pdf_path, "rb") as f:
            return f.read()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_complete_document(latex_code: str) -> bool:
    """Returns True if the string contains a full LaTeX document structure."""
    return (
        r"\documentclass" in latex_code and
        r"\begin{document}" in latex_code and
        r"\end{document}" in latex_code
    )


def _wrap_sections_in_template(sections: list) -> str:
    """
    Wraps parsed section dicts into a minimal but properly formatted LaTeX document.
    Used when Gemini returned section content without a full document wrapper.
    """
    body_parts = []
    for sec in sections:
        title   = _escape_latex(sec.get("title", ""))
        content = sec.get("content", "").strip()
        body_parts.append(f"\\section*{{{title}}}\n{content}\n")

    body = "\n".join(body_parts)

    return f"""\\documentclass[12pt,a4paper]{{article}}
\\usepackage[margin=2.5cm]{{geometry}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{enumitem}}
\\usepackage{{parskip}}
\\pagestyle{{plain}}
\\begin{{document}}
{body}
\\end{{document}}
"""


def _wrap_plain_text(text: str) -> str:
    """
    Last-resort wrapper: escapes and wraps raw text in a minimal LaTeX document.
    """
    escaped = _escape_latex(text)
    return f"""\\documentclass[12pt,a4paper]{{article}}
\\usepackage[margin=2.5cm]{{geometry}}
\\usepackage{{parskip}}
\\pagestyle{{plain}}
\\begin{{document}}
{escaped}
\\end{{document}}
"""


def _escape_latex(text: str) -> str:
    """
    Escapes special LaTeX characters in plain text strings
    (used only for fallback wrapping — not applied to raw LaTeX source).
    """
    replacements = [
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)
    return text