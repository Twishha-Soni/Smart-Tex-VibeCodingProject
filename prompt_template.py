def build_prompt(subject, grade, test_type, marks, difficulty, sections, school):
    return f"""
You are an expert teacher and question paper designer.

Generate a {test_type} for the subject: {subject}
Grade: {grade}
Total Marks: {marks}
Difficulty Level: {difficulty}
Sections to include: {sections}
School name : {school}

Follow these rules strictly:
- Generate the paper using latex code 
- Format the output cleanly so it can be printed directly
- Divide the paper into the requested sections clearly
- Each question must have marks clearly mentioned
- Questions must match the difficulty level
- Do NOT include answers, only questions

Generate the complete {test_type} now.
"""