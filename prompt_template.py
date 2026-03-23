def build_prompt(subject, grade, test_type, marks, difficulty, sections, school, chapter_context=""):
    """
    Builds the Gemini prompt for test/worksheet generation.

    Args:
        subject, grade, test_type, marks, difficulty, sections, school: form fields
        chapter_context: extracted text from uploaded PDF (optional, defaults to "")

    Returns:
        Complete prompt string to send to Gemini API
    """

    # ── Case 1: Chapter PDF was uploaded ──
    if chapter_context.strip():
        context_block = f"""
The teacher has uploaded a chapter PDF. Generate questions STRICTLY based on the content below.
Do NOT generate random questions — every question must relate to the chapter content provided.

--- CHAPTER CONTENT START ---
{chapter_context}
--- CHAPTER CONTENT END ---
"""
    # ── Case 2: No PDF — generate based on subject/grade ──
    else:
        context_block = """
No chapter PDF was uploaded. Generate questions based on standard curriculum for the given subject and grade.
"""

    return f"""
You are an expert teacher and question paper designer.

Generate a {test_type} for the subject: {subject}
Grade: {grade}
Total Marks: {marks}
Difficulty Level: {difficulty}
Sections to include: {sections}
School name: {school}
{context_block}
Follow these rules strictly:
- Generate the paper using LaTeX code
- Format the output cleanly so it can be printed directly
- Divide the paper into the requested sections clearly
- Each question must have marks clearly mentioned
- Questions must match the difficulty level
- Do NOT include answers, only questions

Generate the complete {test_type} now.
"""