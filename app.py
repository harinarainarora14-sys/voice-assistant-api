from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote
import string

# ------------------------
# Load responses
# ------------------------
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

# ------------------------
# Initialize FastAPI
# ------------------------
app = FastAPI()

# CORS middleware to allow frontend access globally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Home & ping routes
# ------------------------
@app.get("/")
def home():
    return {"message": "✅ Voice Assistant API is running"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

# ------------------------
# Gemini API helper
# ------------------------
GEMINI_API_KEY = "AIzaSyB4oYXN34edV8imQd7A_pYxuSSm9Hl5sso"
GEMINI_API_URL = "https://api.gemini.ai/v1/chat"  # Example Gemini endpoint

def ask_gemini(question: str):
    try:
        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
        payload = {"prompt": question, "model": "gemini-1"}
        resp = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("answer") or data.get("text") or "No answer from Gemini."
        else:
            return "Gemini API error."
    except Exception as e:
        return f"Gemini API exception: {str(e)}"

# ------------------------
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...)):
    question_clean = question.lower().strip().rstrip(string.punctuation + "!?")

    # --- Step 1: Exact match ---
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question)

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
        return process_answer(best_match, question)

    # --- Step 3: Wikipedia fallback ---
    if len(question_clean.split()) >= 3:
        wiki_keywords = [
            "tell me about", "who is", "what is", "search for",
            "give me information on", "explain", "tell me something about", "find info about"
        ]
        query = question
        for kw in wiki_keywords:
            if question.startswith(kw):
                query = question[len(kw):].strip()
                break

        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
        headers = {"User-Agent": "VoiceAssistant/1.0 (https://yourdomain.com, contact: your@email.com)"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    return {"answer": extract}
                else:
                    return {"answer": "I couldn't find anything on Wikipedia."}
            else:
                return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Sorry, there was an error accessing Wikipedia."}

    # --- Step 4: Fallback to Gemini ---
    gemini_answer = ask_gemini(question)
    return {"answer": gemini_answer}

# ------------------------
# Answer processing
# ------------------------
def process_answer(intent: str, question: str):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time request → Indian local time
    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now_india = datetime.now(india_tz)
        time_str = now_india.strftime("%I:%M %p")
        return {"answer": time_str, "type": "time_india"}

    # Wikipedia request
    elif answer.upper() == "WIKIPEDIA":
        wiki_keywords = [
            "tell me about", "who is", "what is", "search for",
            "give me information on", "explain", "tell me something about", "find info about"
        ]
        query = question
        for kw in wiki_keywords:
            if question.startswith(kw):
                query = question[len(kw):].strip()
                break

        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
        headers = {"User-Agent": "VoiceAssistant/1.0 (https://yourdomain.com, contact: your@email.com)"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    return {"answer": extract}
                else:
                    return {"answer": "I couldn't find anything on Wikipedia."}
            else:
                return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Sorry, there was an error accessing Wikipedia."}

    # Default static response
    else:
        return {"answer": answer}

