from flask import Flask, request, render_template, session, Response
from google import genai
from prompt_template import build_prompt
from parse_response import parse_gemini_response
from pdf_generator import generate_pdf
from pdf_extractor import extract_pdf_text
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = "smarttex-dev-key"
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Allowed image extensions for Task 8
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    subject   = request.form.get("subject")
    grade     = request.form.get("grade")
    test_type = request.form.get("test_type")
    marks     = request.form.get("marks")
    school    = request.form.get("school")

    # Sprint 4 Task 3: Read per-section difficulty
    section_names        = request.form.getlist("section_name[]")
    section_difficulties = request.form.getlist("section_difficulty[]")
    sections_with_difficulty = list(zip(section_names, section_difficulties))

    # Sprint 4 Task 4: Read optional custom instructions
    custom_instructions = request.form.get("custom_instructions", "")

    # ── Sprint 3: Handle optional chapter PDF upload ──
    chapter_context = ""
    pdf_warning     = ""
    uploaded_file   = request.files.get("chapter_pdf")

    if uploaded_file and uploaded_file.filename != "":
        # Sprint 4 Task 9: extract_pdf_text now handles OCR internally for scanned PDFs
        chapter_context, pdf_warning = extract_pdf_text(uploaded_file)
        if chapter_context:
            print(f"[app] PDF uploaded: '{uploaded_file.filename}' — extracted {len(chapter_context)} chars")
        else:
            print(f"[app] PDF uploaded but 0 chars extracted. Warning: {pdf_warning}")
    else:
        print("[app] No PDF uploaded — using subject-based generation")

    # ── Sprint 4 Task 8: Handle optional image upload ──
    image_path    = ""
    image_warning = ""
    uploaded_image = request.files.get("question_image")

    if uploaded_image and uploaded_image.filename != "":
        ext = os.path.splitext(uploaded_image.filename)[1].lower()

        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            image_warning = (
                f"Unsupported image format '{ext}'. "
                f"Please upload a PNG, JPG, or GIF. Image was ignored."
            )
            print(f"[app] Image rejected — unsupported extension: {ext}")
        else:
            # Save to static/uploads/ so pdflatex can reference it by absolute path
            uploads_dir = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(uploads_dir, exist_ok=True)

            unique_name = f"img_{uuid.uuid4().hex}{ext}"
            image_path  = os.path.join(uploads_dir, unique_name)
            uploaded_image.save(image_path)
            print(f"[app] Image saved: '{uploaded_image.filename}' → '{unique_name}'")
    else:
        print("[app] No image uploaded")

    prompt = build_prompt(
        subject, grade, test_type, marks,
        sections_with_difficulty, school,
        chapter_context,      # Sprint 3
        custom_instructions,  # Sprint 4 Task 4
        image_path            # Sprint 4 Task 8
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt
    )

    parsed = parse_gemini_response(response.text)

    session["latex_code"] = parsed["latex_code"]
    session["sections"]   = parsed["sections"]

    return render_template(
        "index.html",
        parsed=parsed,
        pdf_warning=pdf_warning,
        image_warning=image_warning
    )


@app.route("/download")
def download():
    latex_code = session.get("latex_code", "")
    sections   = session.get("sections", [])

    if not latex_code and not sections:
        return "Nothing to download. Please generate first.", 400

    # Sprint 4 Task 7: pdflatex compilation — catch errors gracefully
    try:
        pdf_bytes = generate_pdf(latex_code, sections)
    except RuntimeError as e:
        print(f"[download] pdflatex error:\n{e}")
        return (
            "PDF compilation failed. The LaTeX output from Gemini may contain errors. "
            "Please try generating again, or copy the LaTeX code and compile it manually.\n\n"
            f"Technical detail:\n{str(e)[:500]}",
            500
        )

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=smart_tex_output.pdf"}
    )


if __name__ == "__main__":
    app.run(debug=True)