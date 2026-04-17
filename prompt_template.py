def build_prompt(subject, grade, test_type, marks, sections_with_difficulty, school,
                 chapter_context="", custom_instructions="", image_path=""):
    """
    Builds the Gemini prompt for test/worksheet generation.

    Args:
        subject, grade, test_type, marks, school: form fields
        sections_with_difficulty: list of (section_name, difficulty) tuples
                                  e.g. [("MCQ", "Easy"), ("Long Answer", "Hard")]
        chapter_context:      extracted text from uploaded PDF (optional)
        custom_instructions:  teacher's free-text add-on appended to the prompt (optional)
        image_path:           absolute path to uploaded image file (optional, Sprint 4 Task 8)

    Returns:
        Complete prompt string to send to Gemini API
    """

    # ── Marks logic: Test shows marks, Worksheet does not ──
    if test_type == "Worksheet":
        marks_rule = "- Do NOT mention marks for any question or section — this is a worksheet, not a scored test"
        marks_info = "N/A (Worksheet)"
    else:
        marks_rule = "- Each question must have marks clearly mentioned in square brackets e.g. [2 Marks]"
        marks_info = marks

    # ── Per-section difficulty block ──
    if sections_with_difficulty:
        sections_block = "Sections to include (with individual difficulty levels):\n"
        for name, diff in sections_with_difficulty:
            sections_block += f"  - {name}: {diff} difficulty\n"
    else:
        sections_block = "Sections to include: General sections\n"

    # ── Chapter context block ──
    if chapter_context.strip():
        context_block = f"""
The teacher has uploaded a chapter PDF. Generate questions STRICTLY based on the content below.
Do NOT generate random questions — every question must relate to the chapter content provided.

--- CHAPTER CONTENT START ---
{chapter_context}
--- CHAPTER CONTENT END ---
"""
    else:
        context_block = """
No chapter PDF was uploaded. Generate questions based on standard curriculum for the given subject and grade.
"""

    # ── Custom instructions block ──
    if custom_instructions.strip():
        custom_block = f"""
ADDITIONAL INSTRUCTIONS FROM THE TEACHER (follow these carefully):
{custom_instructions.strip()}
"""
    else:
        custom_block = ""

    # ── Sprint 4 Task 8: Image figure block ──
    # Tell Gemini to place the image as a LaTeX figure in the output.
    # The absolute path is embedded directly so pdflatex can find it at compile time.
    if image_path.strip():
        image_block = f"""
IMAGE FIGURE INSTRUCTION:
The teacher has uploaded a diagram/image for use in this paper.
You MUST include the following LaTeX figure exactly as shown, placed in a relevant question
(e.g. "Refer to the figure below and answer the following questions:"):

\\begin{{figure}}[h]
  \\centering
  \\includegraphics[width=0.5\\textwidth]{{{image_path}}}
  \\caption{{Refer to this diagram to answer the question.}}
\\end{{figure}}

Make sure \\usepackage{{graphicx}} is included in the preamble.
"""
    else:
        image_block = ""

    return f"""
You are an expert teacher and question paper designer.

Generate a {test_type} for the subject: {subject}
Grade: {grade}
Total Marks: {marks_info}
School name: {school}
{sections_block}
{context_block}
{image_block}
Follow these rules strictly:
- Generate the paper using LaTeX code
- Format the output cleanly so it can be printed directly
- Divide the paper into the requested sections clearly
- Each section must match its specified difficulty level exactly
- {marks_rule}
- Do NOT include answers, only questions

IMPORTANT — Paper Header Format:
The LaTeX output MUST begin with a proper school exam paper header inside \\begin{{document}}, formatted like this:
  - School name centered and bold at the top
  - Subject, Grade, and Total Marks on the next line
  - A horizontal rule (\\hrulefill or \\hline)
  - Then a row with blank fields for the student to fill:
      Name: \\underline{{\\hspace{{6cm}}}}  \\hfill  Roll No.: \\underline{{\\hspace{{2cm}}}}  \\hfill  Date: \\underline{{\\hspace{{2.5cm}}}}
  - Another horizontal rule
  - Then the sections and questions begin
{custom_block}
Generate the complete {test_type} now.
"""