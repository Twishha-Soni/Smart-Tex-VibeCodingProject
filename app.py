from flask import Flask, request, render_template, session, Response, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from google import genai
from prompt_template import build_prompt
from parse_response import parse_gemini_response, parse_questions
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

# ── Sprint 7 Task 8: Allowed PDF MIME types ──
ALLOWED_PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


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

    # ── Sprint 7 Task 3: Indexes on frequently filtered columns ──
    __table_args__ = (
        db.Index("ix_papers_subject",   "subject"),
        db.Index("ix_papers_grade",     "grade"),
        db.Index("ix_papers_test_type", "test_type"),
    )

    # ── Sprint 6 Task 1: Relationship — one paper has many questions ──
    # cascade="all, delete-orphan" ensures linked questions are deleted when paper is deleted
    questions = db.relationship("Question", backref="paper", lazy=True,
                                cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Paper id={self.id} subject='{self.subject}' grade='{self.grade}'>"


# ── Sprint 6 Task 1: Question model — maps to the questions table in SQLite ──
class Question(db.Model):
    __tablename__ = "questions"

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject       = db.Column(db.Text, nullable=False)
    grade         = db.Column(db.Text, nullable=False)
    chapter_name  = db.Column(db.Text, nullable=True)
    difficulty    = db.Column(db.Text, nullable=True)
    question_type = db.Column(db.Text, nullable=True)
    content       = db.Column(db.Text, nullable=False)
    paper_id      = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=True)

    # ── Sprint 7 Task 3: Indexes on frequently filtered columns ──
    __table_args__ = (
        db.Index("ix_questions_subject",    "subject"),
        db.Index("ix_questions_grade",      "grade"),
        db.Index("ix_questions_difficulty", "difficulty"),
    )

    def __repr__(self):
        return f"<Question id={self.id} subject='{self.subject}' type='{self.question_type}'>"


# ── Sprint 5 Task 1 + Sprint 6 Task 1: Initialise all database tables on startup ──
with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    subject   = request.form.get("subject", "").strip()
    grade     = request.form.get("grade", "").strip()
    test_type = request.form.get("test_type", "").strip()
    marks     = request.form.get("marks", "").strip()
    school    = request.form.get("school", "").strip()

    section_names        = request.form.getlist("section_name[]")
    section_difficulties = request.form.getlist("section_difficulty[]")

    # ── Sprint 7 Task 6: Flask-side form validation ──
    validation_error = None

    if not subject:
        validation_error = "Subject is required."
    elif not school:
        validation_error = "School Name is required."
    elif not marks:
        validation_error = "Total Marks is required."
    else:
        try:
            marks_int = int(marks)
            if marks_int <= 0:
                validation_error = "Total Marks must be a positive number."
        except ValueError:
            validation_error = "Total Marks must be a valid number."

    # Filter out any section rows where the name is blank
    valid_sections = [
        (name.strip(), diff)
        for name, diff in zip(section_names, section_difficulties)
        if name.strip()
    ]

    if not validation_error and not valid_sections:
        validation_error = "At least one section must be added."

    if validation_error:
        print(f"[generate] Validation failed: {validation_error}")
        return render_template("index.html", validation_error=validation_error)

    sections_with_difficulty = valid_sections

    custom_instructions = request.form.get("custom_instructions", "")

    # ── Sprint 7 Task 8: PDF upload validation — extension + MIME type ──
    chapter_context = ""
    chapter_name    = ""
    pdf_warning     = ""
    uploaded_file   = request.files.get("chapter_pdf")

    if uploaded_file and uploaded_file.filename != "":
        ext      = os.path.splitext(uploaded_file.filename)[1].lower()
        mimetype = uploaded_file.mimetype or ""

        if ext != ".pdf" or mimetype not in ALLOWED_PDF_MIME_TYPES:
            pdf_warning = (
                f"Invalid file '{uploaded_file.filename}' — only PDF files are accepted. "
                f"The file was ignored and questions will be generated based on subject and grade."
            )
            print(f"[app] PDF rejected — ext='{ext}' mimetype='{mimetype}'")
        else:
            chapter_context, pdf_warning = extract_pdf_text(uploaded_file)
            chapter_name = os.path.splitext(uploaded_file.filename)[0]
            if chapter_context:
                print(f"[app] PDF uploaded: '{uploaded_file.filename}' — extracted {len(chapter_context)} chars")
            else:
                print(f"[app] PDF uploaded but 0 chars extracted. Warning: {pdf_warning}")
    else:
        print("[app] No PDF uploaded — using subject-based generation")

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
        chapter_context,
        custom_instructions,
        image_path
    )

    # ── Sprint 7 Task 7: Wrap Gemini API call in try/except ──
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        gemini_output = response.text
        print(f"[generate] Gemini response received — {len(gemini_output)} chars")
    except Exception as e:
        print(f"[generate] Gemini API call failed: {e}")
        return render_template(
            "index.html",
            api_error="Paper generation failed. Please check your connection and try again."
        )

    parsed = parse_gemini_response(gemini_output)

    session["latex_code"] = parsed["latex_code"]
    session["sections"]   = parsed["sections"]

    # ── Sprint 7 Task 9: Paper save and question save are separate try/except blocks ──
    # This ensures a question save failure never rolls back the already-committed paper.
    paper_id_for_questions = None

    if parsed["latex_code"]:

        # ── Commit 1: Save the paper record ──
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
            paper_id_for_questions = paper.id
            print(f"[app] Paper saved to DB — id={paper.id} subject='{subject}' grade='{grade}'")
        except Exception as e:
            db.session.rollback()
            print(f"[app] Paper DB save failed: {e}")

        # ── Commit 2: Save extracted questions (only if paper was saved successfully) ──
        if paper_id_for_questions:
            try:
                extracted = parse_questions(
                    parsed, subject, grade, sections_with_difficulty, chapter_name
                )

                if extracted:
                    question_rows = [
                        Question(
                            subject       = q["subject"],
                            grade         = q["grade"],
                            chapter_name  = q["chapter_name"],
                            difficulty    = q["difficulty"],
                            question_type = q["question_type"],
                            content       = q["content"],
                            paper_id      = paper_id_for_questions
                        )
                        for q in extracted
                    ]
                    db.session.bulk_save_objects(question_rows)
                    db.session.commit()
                    print(f"[app] {len(question_rows)} question(s) saved to DB for paper id={paper_id_for_questions}")
                else:
                    print(f"[app] No questions extracted for paper id={paper_id_for_questions}")
            except Exception as e:
                db.session.rollback()
                print(f"[app] Questions DB save failed (paper id={paper_id_for_questions}): {e}")
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


# ── Sprint 5 Task 5 + Sprint 7 Task 2: Past Papers route with filters ──
@app.route("/papers")
def papers():
    f_subject   = request.args.get("subject",   "").strip()
    f_grade     = request.args.get("grade",     "").strip()
    f_test_type = request.args.get("test_type", "").strip()

    query = Paper.query.order_by(Paper.date_generated.desc())

    if f_subject:
        query = query.filter(Paper.subject.ilike(f"%{f_subject}%"))
    if f_grade:
        query = query.filter(Paper.grade.ilike(f"%{f_grade}%"))
    if f_test_type:
        query = query.filter(Paper.test_type == f_test_type)

    all_papers = query.all()
    print(f"[papers] Fetched {len(all_papers)} papers (filters: subject='{f_subject}' "
          f"grade='{f_grade}' type='{f_test_type}')")

    all_subjects = sorted({p.subject for p in Paper.query.all() if p.subject})
    all_grades   = sorted({p.grade   for p in Paper.query.all() if p.grade})

    filters = {
        "subject":   f_subject,
        "grade":     f_grade,
        "test_type": f_test_type,
    }

    return render_template(
        "past_papers.html",
        papers       = all_papers,
        filters      = filters,
        all_subjects = all_subjects,
        all_grades   = all_grades,
    )


# ── Sprint 7 Task 4: Delete Paper — POST only, cascade deletes linked questions ──
@app.route("/papers/delete/<int:paper_id>", methods=["POST"])
def delete_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    try:
        db.session.delete(paper)
        db.session.commit()
        print(f"[delete_paper] Deleted paper id={paper_id} and its linked questions")
    except Exception as e:
        db.session.rollback()
        print(f"[delete_paper] DB delete failed: {e}")

    return redirect(url_for("papers"))


# ── Sprint 5 Task 7: Re-download route ──
@app.route("/download/<int:paper_id>")
def download_by_id(paper_id):
    paper = Paper.query.get_or_404(paper_id)

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


# ── Sprint 6 Task 4: Question Bank route — browse and filter questions ──
@app.route("/questions")
def questions():
    f_subject       = request.args.get("subject", "").strip()
    f_grade         = request.args.get("grade", "").strip()
    f_chapter       = request.args.get("chapter_name", "").strip()
    f_difficulty    = request.args.get("difficulty", "").strip()
    f_question_type = request.args.get("question_type", "").strip()

    query = Question.query.order_by(Question.id.desc())

    if f_subject:
        query = query.filter(Question.subject.ilike(f"%{f_subject}%"))
    if f_grade:
        query = query.filter(Question.grade.ilike(f"%{f_grade}%"))
    if f_chapter:
        query = query.filter(Question.chapter_name.ilike(f"%{f_chapter}%"))
    if f_difficulty:
        query = query.filter(Question.difficulty == f_difficulty)
    if f_question_type:
        query = query.filter(Question.question_type.ilike(f"%{f_question_type}%"))

    all_questions = query.all()
    print(f"[questions] Fetched {len(all_questions)} questions (filters: subject='{f_subject}' "
          f"grade='{f_grade}' chapter='{f_chapter}' difficulty='{f_difficulty}' type='{f_question_type}')")

    all_subjects       = sorted({q.subject       for q in Question.query.all() if q.subject})
    all_grades         = sorted({q.grade         for q in Question.query.all() if q.grade})
    all_chapters       = sorted({q.chapter_name  for q in Question.query.all() if q.chapter_name})
    all_difficulties   = ["Easy", "Medium", "Hard"]
    all_question_types = sorted({q.question_type for q in Question.query.all() if q.question_type})

    filters = {
        "subject":       f_subject,
        "grade":         f_grade,
        "chapter_name":  f_chapter,
        "difficulty":    f_difficulty,
        "question_type": f_question_type,
    }

    return render_template(
        "question_bank.html",
        questions          = all_questions,
        filters            = filters,
        all_subjects       = all_subjects,
        all_grades         = all_grades,
        all_chapters       = all_chapters,
        all_difficulties   = all_difficulties,
        all_question_types = all_question_types,
    )


# ── Sprint 6 Task 6: Add Question — GET shows form, POST saves to DB ──
@app.route("/questions/add", methods=["GET", "POST"])
def add_question():
    if request.method == "POST":
        subject       = request.form.get("subject", "").strip()
        grade         = request.form.get("grade", "").strip()
        chapter_name  = request.form.get("chapter_name", "").strip()
        difficulty    = request.form.get("difficulty", "").strip()
        question_type = request.form.get("question_type", "").strip()
        content       = request.form.get("content", "").strip()

        if not subject or not grade or not content:
            error = "Subject, Grade and Question Content are required."
            return render_template("add_question.html", error=error,
                                   form_data=request.form)

        try:
            question = Question(
                subject       = subject,
                grade         = grade,
                chapter_name  = chapter_name or None,
                difficulty    = difficulty or None,
                question_type = question_type or None,
                content       = content,
                paper_id      = None
            )
            db.session.add(question)
            db.session.commit()
            print(f"[add_question] Manually added question id={question.id} subject='{subject}'")
        except Exception as e:
            db.session.rollback()
            print(f"[add_question] DB save failed: {e}")
            error = "Failed to save question. Please try again."
            return render_template("add_question.html", error=error,
                                   form_data=request.form)

        return redirect(url_for("questions"))

    return render_template("add_question.html", error=None, form_data={})


# ── Sprint 6 Task 7: Edit Question — GET pre-fills form, POST updates DB ──
@app.route("/questions/edit/<int:question_id>", methods=["GET", "POST"])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)

    if request.method == "POST":
        subject       = request.form.get("subject", "").strip()
        grade         = request.form.get("grade", "").strip()
        chapter_name  = request.form.get("chapter_name", "").strip()
        difficulty    = request.form.get("difficulty", "").strip()
        question_type = request.form.get("question_type", "").strip()
        content       = request.form.get("content", "").strip()

        if not subject or not grade or not content:
            error = "Subject, Grade and Question Content are required."
            return render_template("edit_question.html", question=question,
                                   error=error, form_data=request.form)

        try:
            question.subject       = subject
            question.grade         = grade
            question.chapter_name  = chapter_name or None
            question.difficulty    = difficulty or None
            question.question_type = question_type or None
            question.content       = content
            db.session.commit()
            print(f"[edit_question] Updated question id={question_id}")
        except Exception as e:
            db.session.rollback()
            print(f"[edit_question] DB update failed: {e}")
            error = "Failed to update question. Please try again."
            return render_template("edit_question.html", question=question,
                                   error=error, form_data=request.form)

        return redirect(url_for("questions"))

    return render_template("edit_question.html", question=question,
                           error=None, form_data={})


# ── Sprint 6 Task 8: Delete Question — POST only, redirects to Question Bank ──
@app.route("/questions/delete/<int:question_id>", methods=["POST"])
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)

    try:
        db.session.delete(question)
        db.session.commit()
        print(f"[delete_question] Deleted question id={question_id}")
    except Exception as e:
        db.session.rollback()
        print(f"[delete_question] DB delete failed: {e}")

    return redirect(url_for("questions"))


if __name__ == "__main__":
    app.run(debug=True)