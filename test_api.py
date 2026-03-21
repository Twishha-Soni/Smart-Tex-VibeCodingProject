from google import genai
from dotenv import load_dotenv
from prompt_template import build_prompt
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

prompt = build_prompt(
    subject="EVS",
    grade=3,
    test_type="Test",
    marks=20,
    difficulty="Medium",
    sections="MCQ, short Answer, Long Answer"
    school="Podar International School, Modasa"
)

response = client.models.generate_content(
    model="gemini-3.1-flash-lite-preview",
    contents=prompt
)

print(response.text)