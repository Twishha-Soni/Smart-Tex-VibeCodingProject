import re


def parse_gemini_response(raw_text):
    """
    Parses the raw Gemini API response into a structured dict.

    Returns:
    {
        "latex_code": str,       # clean LaTeX code (stripped of markdown fences)
        "sections": list,        # list of {"title": str, "content": str}
        "raw": str               # original raw text (fallback)
    }
    """

    result = {
        "latex_code": "",
        "sections": [],
        "raw": raw_text
    }

    # Step 1: Strip markdown code fences if Gemini wraps output in ```latex ... ```
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:latex)?\s*([\s\S]*?)```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    result["latex_code"] = cleaned

    # Step 2: Extract sections from LaTeX
    # Look for \section{...} or \textbf{Section ...} patterns
    section_pattern = re.compile(
        r"\\section\*?\{([^}]+)\}([\s\S]*?)(?=\\section|\Z)",
        re.IGNORECASE
    )
    matches = section_pattern.findall(cleaned)

    if matches:
        for title, content in matches:
            result["sections"].append({
                "title": title.strip(),
                "content": content.strip()
            })
    else:
        # Fallback: try to detect bold section headers like \textbf{Section A: MCQ}
        fallback_pattern = re.compile(
            r"\\textbf\{([^}]*(?:section|part|question)[^}]*)\}([\s\S]*?)(?=\\textbf\{[^}]*(?:section|part|question)|\\end\{document\}|\Z)",
            re.IGNORECASE
        )
        fallback_matches = fallback_pattern.findall(cleaned)
        for title, content in fallback_matches:
            result["sections"].append({
                "title": title.strip(),
                "content": content.strip()
            })

    return result


# ── Sprint 6 Task 2: parse_questions() ────────────────────────────────────────

def parse_questions(parsed, subject, grade, sections_with_difficulty, chapter_name=""):
    """
    Extracts individual questions from parsed Gemini output and returns them
    as a list of dicts ready to be bulk-inserted into the questions table.

    Strategy:
      - Iterates through each section in parsed["sections"].
      - Infers question_type from the section title (e.g. "MCQ", "Short Answer").
      - Infers difficulty by matching the section title against sections_with_difficulty
        from the form — falls back to "Medium" if no match found.
      - Splits section content into individual questions by detecting numbered
        patterns: "1.", "1)", "Q1.", "Q1)" at the start of a line.
      - Strips LaTeX markup from each question before saving (keeps it readable).
      - Skips empty or very short strings (< 5 chars) that are not real questions.

    Args:
        parsed:                   dict returned by parse_gemini_response()
        subject:                  str — from form
        grade:                    str — from form
        sections_with_difficulty: list of (section_name, difficulty) tuples — from form
        chapter_name:             str — PDF filename (without extension) if uploaded,
                                  otherwise defaults to subject name

    Returns:
        list of dicts, each with keys:
            subject, grade, chapter_name, difficulty, question_type, content
        (paper_id is NOT included here — it is assigned in app.py after the paper is saved)
    """

    questions = []

    # Use subject as chapter_name fallback if no PDF was uploaded
    effective_chapter = chapter_name.strip() if chapter_name.strip() else subject

    # Build a lookup: normalised section title → difficulty
    # e.g. "mcq" → "Easy", "short answer" → "Medium"
    difficulty_lookup = {}
    for name, diff in sections_with_difficulty:
        difficulty_lookup[name.strip().lower()] = diff

    sections = parsed.get("sections", [])

    if not sections:
        # No sections parsed — try to extract questions from raw latex_code as one block
        # Treat the whole paper as a single "General" section with Medium difficulty
        sections = [{"title": "General", "content": parsed.get("latex_code", "")}]

    for section in sections:
        section_title   = section.get("title", "").strip()
        section_content = section.get("content", "").strip()

        if not section_content:
            continue

        # ── Infer question_type from section title ──
        question_type = _infer_question_type(section_title)

        # ── Infer difficulty by matching section title against form data ──
        difficulty = _infer_difficulty(section_title, difficulty_lookup)

        # ── Split content into individual questions ──
        raw_questions = _split_into_questions(section_content)

        for raw_q in raw_questions:
            clean_q = _strip_latex(raw_q).strip()
            if len(clean_q) < 5:
                # Skip noise — blank lines, lone brackets, etc.
                continue
            questions.append({
                "subject":       subject,
                "grade":         grade,
                "chapter_name":  effective_chapter,
                "difficulty":    difficulty,
                "question_type": question_type,
                "content":       clean_q
            })

    print(f"[parse_questions] Extracted {len(questions)} questions from {len(sections)} section(s)")
    return questions


# ── Helpers ───────────────────────────────────────────────────────────────────

# Keywords used to infer question type from section title
_TYPE_KEYWORDS = [
    ("mcq",           "MCQ"),
    ("multiple choice","MCQ"),
    ("short answer",  "Short Answer"),
    ("short",         "Short Answer"),
    ("long answer",   "Long Answer"),
    ("long",          "Long Answer"),
    ("fill",          "Fill in the Blanks"),
    ("true",          "True/False"),
    ("false",         "True/False"),
    ("match",         "Match the Following"),
    ("diagram",       "Diagram Based"),
    ("essay",         "Essay"),
    ("general",       "General"),
]

def _infer_question_type(section_title: str) -> str:
    """Returns a clean question type label inferred from the section title."""
    lower = section_title.lower()
    for keyword, label in _TYPE_KEYWORDS:
        if keyword in lower:
            return label
    # Default: use the section title itself as the type
    return section_title if section_title else "General"


def _infer_difficulty(section_title: str, difficulty_lookup: dict) -> str:
    """
    Matches section title against the difficulty_lookup built from form data.
    Falls back to "Medium" if no match is found.
    """
    lower = section_title.lower()
    # Try exact match first
    if lower in difficulty_lookup:
        return difficulty_lookup[lower]
    # Try partial match — section title contains one of the lookup keys
    for key, diff in difficulty_lookup.items():
        if key in lower or lower in key:
            return diff
    return "Medium"


def _split_into_questions(content: str) -> list:
    """
    Splits a section's LaTeX content into individual question strings.

    Detects question boundaries by looking for numbered patterns at the
    start of a line:
        1.   1)   Q1.   Q1)   (1)   [1]
    """
    # Pattern: optional whitespace, then a question number marker at line start
    split_pattern = re.compile(
        r"(?m)(?=^\s*(?:Q\s*)?\d+[\.\)]\s|^\s*\(\d+\)\s|^\s*\[\d+\]\s)"
    )
    parts = split_pattern.split(content)
    # Filter out empty strings
    return [p.strip() for p in parts if p.strip()]


# LaTeX commands to strip when saving question text to the DB
_LATEX_STRIP_PATTERNS = [
    re.compile(r"\\(?:textbf|textit|underline|emph|text)\{([^}]*)\}"),  # formatting → keep inner text
    re.compile(r"\\(?:item|hline|hfill|hrulefill|newline|\\)"),          # structural commands
    re.compile(r"\\[a-zA-Z]+\*?\{[^}]*\}"),                              # generic \cmd{...} → remove
    re.compile(r"\\[a-zA-Z]+"),                                           # bare commands like \par
    re.compile(r"\$\$[\s\S]*?\$\$"),                                      # display math blocks
    re.compile(r"\$[^$]*?\$"),                                            # inline math
    re.compile(r"[{}]"),                                                  # leftover braces
    re.compile(r"\[\d+\s*[Mm]arks?\]"),                                   # [2 Marks] annotations
    re.compile(r"\s{2,}"),                                                # collapse whitespace
]

def _strip_latex(text: str) -> str:
    """
    Removes LaTeX markup from a question string so the DB stores readable text.
    Formatting commands like \\textbf{word} are replaced by just 'word'.
    """
    # First pass: replace formatting commands with their inner text
    text = re.sub(r"\\(?:textbf|textit|underline|emph|text)\{([^}]*)\}", r"\1", text)
    # Second pass: remove remaining LaTeX
    for pattern in _LATEX_STRIP_PATTERNS[1:]:
        text = pattern.sub(" ", text)
    return text.strip()