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