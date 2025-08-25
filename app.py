from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Built-in Python 3.9+
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote
import string
import re
import time

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

# CORS middleware
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
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...)):
    # Lowercase, strip spaces and trailing punctuation
    question_clean = question.lower().strip()
    question_clean = question_clean.rstrip(string.punctuation + "!?")

    # --- Step 1: Exact match ---
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question_clean)

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
        return process_answer(best_match, question_clean)

    # --- Step 3: Wikipedia fallback for longer queries ---
    if len(question_clean.split()) >= 3:
        wiki_answer = fetch_wikipedia_summary(question_clean)
        if wiki_answer:
            return {"answer": wiki_answer}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    # --- Step 4: No match ---
    return {"answer": f"Sorry, I don't understand '{question}'."}

# ------------------------
# Answer processing
# ------------------------
def process_answer(intent: str, question: str):
    """Handles the answer logic (time, wiki, or static)"""
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time request → Indian local time
    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now_india = datetime.now(india_tz)
        time_str = now_india.strftime("%I:%M %p")  # 12-hour format
        return {"answer": time_str, "type": "time_india"}

    # Wikipedia request
    elif answer.upper() == "WIKIPEDIA":
        wiki_answer = fetch_wikipedia_summary(question)
        if wiki_answer:
            return {"answer": wiki_answer}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    # Default static response
    else:
        return {"answer": answer}

# ------------------------
# Wikipedia fetch with retries & cleaned query
# ------------------------
def fetch_wikipedia_summary(question: str) -> str:
    wiki_keywords = [
        "tell me about", "who is", "what is", "search for",
        "give me information on", "explain", "tell me something about", "find info about"
    ]
    query = question
    for kw in wiki_keywords:
        if question.startswith(kw):
            query = question[len(kw):].strip()
            break

    # Clean query: remove special characters
    query = re.sub(r"[^a-zA-Z0-9\s]", "", query)

    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
    retries = 3
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    return extract
            elif resp.status_code == 404:
                return ""  # Page not found
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1)  # wait 1 second before retry
            else:
                return ""
    return ""
