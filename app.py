from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from fuzzywuzzy import fuzz
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo
import string

# ------------------------
# Load responses.json
# ------------------------
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

# ------------------------
# Gemini API Key
# ------------------------
GEMINI_KEY = "AIzaSyB4oYXN34edV8imQd7A_pYxuSSm9Hl5sso"
GEMINI_URL = "https://api.generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateText"

# ------------------------
# Initialize FastAPI
# ------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Home & ping
# ------------------------
@app.get("/")
def home():
    return {"message": "✅ Voice Assistant API is running"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

# ------------------------
# Ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...), use_gemini: bool = Query(False)):
    question_clean = question.lower().strip().rstrip(string.punctuation + "!?")

    # --- Step 1: Exact match ---
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question_clean, use_gemini)

    # --- Step 2: Fuzzy match ---
    best_match = None
    best_score = 0
    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question_clean, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    if best_match and best_score >= 85:
        return process_answer(best_match, question_clean, use_gemini)

    # --- Step 3: Gemini fallback ---
    if use_gemini or len(question.split()) >= 3:
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                json={"prompt": {"text": question}, "temperature": 0.5, "maxOutputTokens": 300}
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", "")
                if text:
                    return {"answer": text}
            return {"answer": "Gemini API did not return a valid response."}
        except Exception as e:
            return {"answer": f"Gemini API error: {e}"}

    # --- Step 4: No match ---
    return {"answer": f"Sorry, I don't understand '{question}'."}


# ------------------------
# Process static responses
# ------------------------
def process_answer(intent: str, question: str, use_gemini=False):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time
    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(india_tz)
        return {"answer": now.strftime("%I:%M %p"), "type": "time_india"}

    # Gemini override
    if use_gemini:
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                json={"prompt": {"text": question}, "temperature": 0.5, "maxOutputTokens": 300}
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", "")
                if text:
                    return {"answer": text}
        except Exception as e:
            return {"answer": f"Gemini API error: {e}"}

    # Default static response
    return {"answer": answer}
