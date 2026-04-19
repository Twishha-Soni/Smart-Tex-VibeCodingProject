from flask import Flask, request, render_template, session, Response
from flask_sqlalchemy import SQLAlchemy
from google import genai
from prompt_template import build_prompt
from parse_response import parse_gemini_response
from pdf_generator import generate_pdf
from pdf_extractor import extract_pdf_text
from dotenv import load_dotenv
import os
import uuid
import json
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = "smarttex-dev-key"

# ── Sprint 5 Task 1: SQLite + SQLAlchemy configuration ──
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smarttex.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Allowed image extensions for Sprint 4 Task 8
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


# ── Sprint 5 Task 2: Paper model — maps to the papers table in SQLite ──
class Paper(db.Model):
    __tablename__ = "papers"

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject        = db.Column(db.Text, nullable=False)
    grade          = db.Column(db.Text, nullable=False)
    test_type      = db.Column(db.Text, nullable=False)
    marks          = db.Column(db.Integer, nullable=True)
    date_generated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    latex_code     = db.Column(db.Text, nullable=False)
    sections       = db.Column(db.Text, nullable=True)   # stored as JSON string

    def __repr__(self):
        return f"<Paper id={self.id} subject='{self.subject}' grade='{self.grade}'>"


# ── Sprint 5 Task 1: Initialise database tables on startup ──
with app.app_context():
    db.create_all()


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

    # ── Sprint 5 Task 3: Auto-save generated paper to database ──
    if parsed["latex_code"]:
        try:
            paper = Paper(
                subject        = subject,
                grade          = grade,
                test_type      = test_type,
                marks          = int(marks) if marks else None,
                date_generated = datetime.utcnow(),
                latex_code     = parsed["latex_code"],
                sections       = json.dumps(parsed["sections"])
            )
            db.session.add(paper)
            db.session.commit()
            print(f"[app] Paper saved to DB — id={paper.id} subject='{subject}' grade='{grade}'")
        except Exception as e:
            db.session.rollback()
            print(f"[app] DB save failed: {e}")
    else:
        print("[app] Gemini returned empty LaTeX — paper not saved to DB")

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


# ── Sprint 5 Task 5: Past Papers route ──
@app.route("/papers")
def papers():
    all_papers = Paper.query.order_by(Paper.date_generated.desc()).all()
    print(f"[papers] Fetched {len(all_papers)} papers from DB")
    return render_template("past_papers.html", papers=all_papers)


# ── Sprint 5 Task 7: Re-download route — regenerate PDF from stored DB record ──
@app.route("/download/<int:paper_id>")
def download_by_id(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    # Deserialise sections JSON string back to list
    try:
        sections = json.loads(paper.sections) if paper.sections else []
    except (json.JSONDecodeError, TypeError):
        sections = []

    print(f"[download_by_id] Re-downloading paper id={paper_id} subject='{paper.subject}'")

    try:
        pdf_bytes = generate_pdf(paper.latex_code, sections)
    except RuntimeError as e:
        print(f"[download_by_id] pdflatex error:\n{e}")
        return (
            f"PDF compilation failed for paper #{paper_id}. "
            "The stored LaTeX may contain errors.\n\n"
            f"Technical detail:\n{str(e)[:500]}",
            500
        )

    filename = f"smart_tex_{paper.subject}_{paper.grade}.pdf".replace(" ", "_")

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


if __name__ == "__main__":
    app.run(debug=True)