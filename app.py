from flask import Flask, request, render_template, session, Response
from google import genai
from prompt_template import build_prompt
from parse_response import parse_gemini_response
from pdf_generator import generate_pdf
from pdf_extractor import extract_pdf_text
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = "smarttex-dev-key"
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    subject    = request.form.get("subject")
    grade      = request.form.get("grade")
    test_type  = request.form.get("test_type")
    marks      = request.form.get("marks")
    difficulty = request.form.get("difficulty")
    sections   = request.form.get("sections")
    school     = request.form.get("school")

    # Sprint 3: Handle optional PDF upload
    chapter_context = ""
    pdf_warning     = ""
    uploaded_file   = request.files.get("chapter_pdf")

    if uploaded_file and uploaded_file.filename != "":
        chapter_context, pdf_warning = extract_pdf_text(uploaded_file)
        if chapter_context:
            print(f"[app] PDF uploaded: '{uploaded_file.filename}' — extracted {len(chapter_context)} chars")
        else:
            print(f"[app] PDF uploaded but 0 chars extracted — scanned PDF. Warning: {pdf_warning}")
    else:
        print("[app] No PDF uploaded — using subject-based generation")

    prompt = build_prompt(subject, grade, test_type, marks, difficulty, sections, school, chapter_context)

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt
    )

    parsed = parse_gemini_response(response.text)

    session["latex_code"] = parsed["latex_code"]
    session["sections"]   = parsed["sections"]

    return render_template("index.html", parsed=parsed, pdf_warning=pdf_warning)


@app.route("/download")
def download():
    latex_code = session.get("latex_code", "")
    sections   = session.get("sections", [])

    if not latex_code and not sections:
        return "Nothing to download. Please generate first.", 400

    pdf_bytes = generate_pdf(latex_code, sections)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=smart_tex_output.pdf"}
    )


if __name__ == "__main__":
    app.run(debug=True)