import os
import re
import shutil
import subprocess
import tempfile


def _find_binary(name: str, fallbacks: list) -> str:
    """
    Locates a binary by name — checks PATH first, then fallback paths.
    Raises RuntimeError if not found anywhere.
    """
    path = shutil.which(name)
    if path:
        return path
    for p in fallbacks:
        if os.path.isfile(p):
            return p
    raise RuntimeError(
        f"{name} not found. Install TeX Live: "
        "apt-get install texlive-xetex texlive-latex-base texlive-latex-recommended texlive-latex-extra"
    )


def _find_xelatex() -> str:
    return _find_binary("xelatex", [
        "/usr/bin/xelatex",
        "/usr/local/bin/xelatex",
        "/opt/texlive/bin/xelatex",
    ])


def _find_pdflatex() -> str:
    return _find_binary("pdflatex", [
        "/usr/bin/pdflatex",
        "/usr/local/bin/pdflatex",
        "/opt/texlive/bin/pdflatex",
    ])


def _needs_xelatex(latex_code: str) -> bool:
    """
    Returns True if the LaTeX source contains non-ASCII characters
    (Gujarati, Hindi, Arabic, etc.) that pdflatex cannot handle.
    XeLaTeX is used in that case for full Unicode support.
    """
    try:
        latex_code.encode("ascii")
        return False   # pure ASCII — pdflatex is fine
    except UnicodeEncodeError:
        return True    # non-ASCII found — use xelatex


def _patch_for_xelatex(latex_code: str) -> str:
    """
    Patches a LaTeX document to work with XeLaTeX:
      - Replaces inputenc/fontenc (pdflatex-only) with fontspec + polyglossia
      - Adds polyglossia language setup for Hindi/Gujarati if detected
      - Adds a Unicode-capable fallback font (FreeSerif covers Devanagari + Gujarati)
    If the document already uses fontspec, it is left as-is.
    """
    if "fontspec" in latex_code:
        # Already set up for XeLaTeX — compile as-is
        return latex_code

    # Remove pdflatex-only packages that break under XeLaTeX
    latex_code = re.sub(r"\\usepackage\[.*?\]\{inputenc\}", "", latex_code)
    latex_code = re.sub(r"\\usepackage\[.*?\]\{fontenc\}",  "", latex_code)
    latex_code = re.sub(r"\\usepackage\{inputenc\}",         "", latex_code)
    latex_code = re.sub(r"\\usepackage\{fontenc\}",          "", latex_code)

    # Detect script to set polyglossia language
    gujarati_range = any("\u0A80" <= ch <= "\u0AFF" for ch in latex_code)
    hindi_range    = any("\u0900" <= ch <= "\u097F" for ch in latex_code)

    if gujarati_range:
        lang_setup = (
            "\\usepackage{polyglossia}\n"
            "\\setmainlanguage{english}\n"
            "\\setotherlanguage{gujarati}\n"
        )
    elif hindi_range:
        lang_setup = (
            "\\usepackage{polyglossia}\n"
            "\\setmainlanguage{english}\n"
            "\\setotherlanguage{hindi}\n"
        )
    else:
        lang_setup = ""

    # Build fontspec block — FreeSerif covers Latin + Devanagari + Gujarati
    fontspec_block = (
        "\\usepackage{fontspec}\n"
        + lang_setup
        + "\\setmainfont{FreeSerif}\n"
    )

    # Inject after \documentclass{...} line
    # Use a lambda for the replacement to avoid re.sub interpreting
    # backslashes in fontspec_block as regex escape sequences (\u, \s etc.)
    latex_code = re.sub(
        r"(\\documentclass(?:\[.*?\])?\{.*?\})",
        lambda m: m.group(1) + "\n" + fontspec_block,
        latex_code,
        count=1
    )

    return latex_code


def generate_pdf(latex_code: str, sections: list) -> bytes:
    """
    Compiles LaTeX source and returns the resulting PDF as bytes.

    Strategy:
      - Detects whether the source contains non-ASCII characters (Gujarati, Hindi, etc.)
      - If yes: uses XeLaTeX for full Unicode support, patches preamble automatically
      - If no:  uses pdflatex (faster, more compatible for Latin scripts)
      - Compiler is run twice so cross-references and page numbers resolve correctly.
      - All temp files are cleaned up automatically after compilation.

    Args:
        latex_code: full LaTeX string from Gemini (may or may not be a complete document)
        sections:   list of {"title": str, "content": str} — used as fallback if needed

    Returns:
        PDF file as bytes

    Raises:
        RuntimeError: if compilation fails (stderr + log tail included for debugging)
    """

    # ── Step 1: Decide what LaTeX source to compile ──
    if _is_complete_document(latex_code):
        source = latex_code
    elif sections:
        source = _wrap_sections_in_template(sections)
    else:
        source = _wrap_plain_text(latex_code)

    # ── Step 2: Choose compiler based on content ──
    if _needs_xelatex(source):
        compiler = _find_xelatex()
        source   = _patch_for_xelatex(source)
        print(f"[pdf_generator] Non-ASCII detected — using XeLaTeX at: {compiler}")
    else:
        compiler = _find_pdflatex()
        print(f"[pdf_generator] ASCII content — using pdflatex at: {compiler}")

    # ── Step 3: Write .tex to a temp dir and compile ──
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "output.tex")
        pdf_path = os.path.join(tmpdir, "output.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(source)

        # Run compiler twice — needed for correct page numbers / references
        for _ in range(2):
            result = subprocess.run(
                [
                    compiler,
                    "-interaction=nonstopmode",
                    "-output-directory", tmpdir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

        # ── Step 4: Check output exists ──
        if not os.path.exists(pdf_path):
            log_path = os.path.join(tmpdir, "output.log")
            log_text = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                    log_text = lf.read()[-3000:]

            raise RuntimeError(
                f"LaTeX compilation failed — PDF not produced.\n"
                f"Compiler: {compiler}\n"
                f"STDERR:\n{result.stderr[-1000:]}\n"
                f"LOG (tail):\n{log_text}"
            )

        # ── Step 5: Read and return PDF bytes ──
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