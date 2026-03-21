from flask import Flask, request, render_template
from google import genai
from prompt_template import build_prompt
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    subject = request.form.get("subject")
    grade = request.form.get("grade")
    test_type = request.form.get("test_type")
    marks = request.form.get("marks")
    difficulty = request.form.get("difficulty")
    sections = request.form.get("sections")
    school = request.form.get("school")

    prompt = build_prompt(subject,grade, test_type, marks, difficulty, sections, school)

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt
    )

    output = response.text

    return render_template("index.html", output=output)

if __name__ == "__main__":
    app.run(debug=True)