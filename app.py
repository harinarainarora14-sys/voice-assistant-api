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
# Gemini API key
# ------------------------
GEMINI_API_KEY = "AIzaSyB4oYXN34edV8imQd7A_pYxuSSm9Hl5sso"
GEMINI_URL = "https://api.gemini.com/v1/ask"  # replace with actual Gemini API URL if different

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
    question = question.lower().strip()
    question = question.rstrip(string.punctuation + "!?")

    # Use Gemini API if requested
    if use_gemini:
        try:
            headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
            payload = {"question": question}
            resp = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer") or "Gemini API returned no answer."
                return {"answer": answer}
            else:
                return {"answer": f"Gemini API error: {resp.status_code}"}
        except Exception as e:
            return {"answer": f"Gemini API request failed: {e}"}

    # --- Step 1: Exact match ---
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question == q.lower().strip():
                return process_answer(intent, question)

    # --- Step 2: Fuzzy match ---
    best_match = None
    best_score = 0
    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    if best_match and best_score >= 85:
        return process_answer(best_match, question)

    # --- Step 3: Wikipedia fallback ---
    if len(question.split()) >= 3:
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
        headers = {"User-Agent": "VoiceAssistant/1.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    return {"answer": extract}
            return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Error accessing Wikipedia."}

    return {"answer": f"Sorry, I don't understand '{question}'."}

# ------------------------
# Answer processing
# ------------------------
def process_answer(intent: str, question: str):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now_india = datetime.now(india_tz)
        time_str = now_india.strftime("%I:%M %p")
        return {"answer": time_str, "type": "time_india"}

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
        headers = {"User-Agent": "VoiceAssistant/1.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    return {"answer": extract}
            return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Error accessing Wikipedia."}

    else:
        return {"answer": answer}
