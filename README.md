# 🧠 Smart-TeX
### AI-Powered Test & Worksheet Generator for Teachers

> **Built end-to-end using Google Gemini API + Flask + SQLite — from idea to deployed full-stack web app — by a final-year CE student at GEC Modasa.**

[![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![Gemini API](https://img.shields.io/badge/Gemini_API-gemini--3.1--flash--lite-orange?style=flat-square&logo=google)](https://ai.google.dev)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue?style=flat-square&logo=sqlite)](https://sqlite.org)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render-purple?style=flat-square&logo=render)](https://render.com)
[![LaTeX](https://img.shields.io/badge/PDF-pdflatex-green?style=flat-square)](https://tug.org/texlive)

---

## 📌 What is Smart-TeX?

Smart-TeX is a web application that eliminates the most tedious part of a teacher's job — writing and formatting test papers and worksheets from scratch.

A teacher fills a simple form: subject, grade, type (test or worksheet), total marks, sections and their difficulty levels. Smart-TeX sends those parameters to a pre-engineered Gemini API prompt at the backend, receives a fully structured LaTeX-based test paper, compiles it via `pdflatex`, and gives the teacher a ready-to-print PDF — in under 30 seconds.

Teachers can also upload a chapter PDF (even scanned ones — OCR is handled automatically), and Smart-TeX will generate questions specifically from that chapter's content.

---

## 💡 The Story Behind This Project

This project was built as a **User Defined Internship Project** at Government Engineering College, Modasa under the guidance of **Prof. Viral Patel** (Assistant Professor, CE Dept.).

### The core challenge I solved as a developer:

**Gemini API hallucinations in large systems.**

When you build a complex AI-powered app and describe everything to the model at once, the model loses context, hallucinates features, and produces inconsistent output. I solved this by applying **Agile sprint methodology to AI-assisted development itself:**

- The project was divided into **9 sprints** (January – May 2026)
- Each sprint had a **clearly scoped prompt context** — I only described what was being built in that sprint, not the whole system
- This kept AI-generated code focused, reviewable, and incrementally testable
- Every sprint built directly on the previous one — no context bleed, no repeated tasks

> **This is not a vibe-coded project. Every feature, every sprint, every technical decision was my idea — AI was the implementation tool, not the architect.**

---

## 🚀 Features

### Core Generation
- **Parameter form** — Subject, Grade, Type (Test/Worksheet), Total Marks, Sections, Difficulty per section, School Name
- **Master prompt at backend** — teachers never write prompts; parameters are injected automatically
- **Gemini API integration** — `gemini-3.1-flash-lite-preview` for structured LaTeX output
- **pdflatex compilation** — professional print-ready PDFs (not basic text-to-PDF)
- **XeLaTeX fallback** — auto-detects non-ASCII content (Gujarati/Hindi) and switches compiler
- **Loading spinner** — UI feedback during API call

### Smart PDF Handling
- **Chapter PDF upload** — generate questions from specific chapter content, not randomly
- **OCR support** — scanned PDFs are automatically handled via Tesseract before text extraction
- **Image support** — upload a diagram; it gets injected as a `\includegraphics{}` LaTeX figure

### Paper Quality Controls
- **Exact marks enforcement** — Gemini is explicitly instructed to sum to exactly the entered marks
- **Difficulty labels hidden** — section difficulty is for generation only, never appears in student paper
- **MCQ answer distribution** — correct answers distributed evenly across A/B/C/D, no pattern
- **Worksheet mode** — marks automatically hidden when type is Worksheet

### Form Enhancements
- **Student Name & Roll No. field** — injected into paper header
- **Per-section difficulty** — set Easy/Medium/Hard independently per section (not one global setting)
- **Custom prompt add-on** — teacher can append extra instructions to the master prompt

### Database (Full-Stack)
- **SQLite + SQLAlchemy** — auto-saves every generated paper to database
- **Past Papers page** — browse all saved papers, filter by Subject/Grade/Type, re-download any as PDF
- **Question Bank** — questions auto-extracted from every generated paper, stored with metadata
- **Full CRUD** — browse, filter, add, edit and delete questions
- **Cascade delete** — deleting a paper removes all its linked questions

### Stability & Error Handling
- **Gemini API failure handling** — friendly error banner, app never crashes
- **PDF upload validation** — extension + MIME type checked
- **Form validation** — Subject, Marks, School, Sections all validated server-side
- **DB write error handling** — try/except with rollback on all commits

### Deployment
- **Dockerised** — Dockerfile with TeX Live minimal + Tesseract + gunicorn
- **Deployed on Render** — free tier, auto-deploy from GitHub

---

## 🗂️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10 + Flask |
| AI | Google Gemini API (`gemini-3.1-flash-lite-preview`) |
| PDF Generation | pdflatex / XeLaTeX (TeX Live minimal) |
| PDF Extraction | PyMuPDF (fitz) + pytesseract (OCR) |
| Database | SQLite + SQLAlchemy / Flask-SQLAlchemy |
| Frontend | Jinja2 + HTML + CSS (no JS framework) |
| Deployment | Docker + Render |

---

## 🗃️ Project Structure

```
smart-tex/
├── app.py                  # Flask app — all routes
├── prompt_template.py      # Master prompt builder — build_prompt()
├── parse_response.py       # Gemini response parser + question extractor
├── pdf_generator.py        # pdflatex / xelatex compiler
├── pdf_extractor.py        # PyMuPDF + Tesseract OCR
├── requirements.txt
├── Dockerfile
├── render.yaml
├── templates/
│   ├── index.html          # Main form + output display
│   ├── past_papers.html    # Past Papers page
│   ├── question_bank.html  # Question Bank page
│   ├── add_question.html   # Add Question form
│   └── edit_question.html  # Edit Question form
└── static/
    ├── style.css
    └── uploads/            # Temporary image uploads
```

---

## 🏃 Sprint-by-Sprint Build Journey

The entire project was built across **9 Agile sprints** from January to May 2026. Each sprint had a defined scope, deliverable list, daily log and professor review.

| Sprint | Dates | What Was Built |
|---|---|---|
| 1 | Jan 1–17 | Gemini API working in Python, master prompt written, HTML form + Flask backend |
| 2 | Jan 18–31 | Full form→API→output pipeline, improved response parsing, fpdf2 PDF download |
| 3 | Feb 1–7 | Chapter PDF upload, PyMuPDF text extraction, prompt context injection, OCR fallback identified |
| 4 | Feb 8–21 | Student name field, worksheet marks logic, per-section difficulty, custom prompt, pdflatex replaces fpdf2, image support, Tesseract OCR |
| 5 | Feb 22–Mar 7 | SQLite + SQLAlchemy setup, papers table, auto-save, Past Papers page, re-download |
| 6 | Mar 8–21 | Questions table, auto-extraction from output, Question Bank page, full CRUD |
| 7 | Mar 22–Apr 4 | Past Papers filter, DB indexes, delete paper (cascade), form validation, error handling, stability test |
| 8 | Apr 5–18 | Fixed marks mismatch bug, removed difficulty labels, MCQ distribution, loading spinner, live testing with 4 teachers/professors, feedback collected |
| 9 | Apr 19–May 2 | Dockerfile + render.yaml, deployed to Render, project report submitted |

---

## 🧪 Real Teacher Testing Results

Sprint 8 included live testing sessions with **2 school teachers and 2 college professors** at GEC Modasa using a structured Google Form:

| Metric | Average Rating |
|---|---|
| UI / UX Experience | ⭐ 4.25 / 5 |
| Output Quality | ⭐ 4.0 / 5 |
| Errors / Crashes | 0 |

---

## 🔌 Running Locally

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/smart-tex.git
cd smart-tex

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install texlive-base texlive-latex-base \
  texlive-latex-recommended texlive-latex-extra \
  texlive-xetex tesseract-ocr

# Set your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Run the app
python app.py
```

Visit `http://localhost:5000`

---

## 🐳 Running with Docker

```bash
docker build -t smart-tex .
docker run -p 10000:10000 -e GEMINI_API_KEY=your_key_here smart-tex
```

---

## 📋 Key Files Explained

**`prompt_template.py` — `build_prompt()`**
The master prompt builder. Takes all form parameters and constructs the complete prompt sent to Gemini. This is where all quality controls live — marks enforcement, difficulty hiding, MCQ distribution rules, worksheet marks logic, image figure injection, chapter context injection.

**`parse_response.py` — `parse_gemini_response()` + `parse_questions()`**
Parses raw Gemini output into structured sections for display, extracts clean LaTeX code, and auto-extracts individual questions with metadata for the Question Bank.

**`pdf_generator.py` — `generate_pdf()`**
Detects whether the LaTeX content contains non-ASCII characters (Gujarati/Hindi), selects pdflatex or xelatex accordingly, patches the preamble for XeLaTeX if needed, compiles twice for correct page numbering, and returns PDF bytes.

**`pdf_extractor.py` — `extract_pdf_text()`**
Opens uploaded PDF with PyMuPDF. For each page, tries digital text extraction first. If a page returns no text (scanned), automatically runs Tesseract OCR on a rasterized version of that page. Returns `(text, warning)` tuple.

---

## 🔮 Future Enhancements

- Language selection — generate papers in Gujarati or Hindi
- Number of questions per section as a configurable field
- Answer key generation as a separate download
- Multi-user support with teacher profiles
- Export to Word (.docx) in addition to PDF

---

## 👩‍💻 About

**Soni Twishha Chetankumar**
Final Year, Computer Engineering
Government Engineering College, Modasa
Enrollment: 220160107129

Project Guide: **Prof. Viral Patel** (Assistant Professor, CE Dept., GEC Modasa)
Project Type: Internship / User Defined Project | Semester 8, 2026

---

## 📄 License

This project is for academic purposes.

---

*Built sprint by sprint. Every idea mine. Every line reviewed.*
