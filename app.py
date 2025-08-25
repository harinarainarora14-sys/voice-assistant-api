from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime, timezone
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote
import string

# Load responses
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False,  
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "✅ Voice Assistant API is running"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/ask")
def ask(question: str = Query(...)):
    # Lowercase, strip spaces and trailing punctuation
    question = question.lower().strip()
    question = question.rstrip(string.punctuation)

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

    print(f"[DEBUG] Best match: {best_match}, Score: {best_score}")

    if best_match and best_score >= 85:
        return process_answer(best_match, question)

    # --- Step 3: No match → Wikipedia fallback for long questions ---
    if len(question.split()) >= 3:
        query = question.replace("tell me about", "").strip()
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {"answer": data.get("extract", "No summary found.")}
            else:
                return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Sorry, there was an error accessing Wikipedia."}

    # --- Step 4: No valid fallback ---
    return {"answer": f"Sorry, I don't understand '{question}'."}


def process_answer(intent: str, question: str):
    """Handles the answer logic (time, wiki, or static)"""
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time request → return 12-hour hh:mm AM/PM
    if answer.upper() == "TIME":
        now_utc = datetime.now(timezone.utc)
        time_str = now_utc.strftime("%I:%M %p")  # 12-hour format
        return {"answer": time_str, "type": "time_utc"}

    # Wikipedia request
    elif answer.upper() == "WIKIPEDIA":
        query = question.replace("tell me about", "").strip()
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {"answer": data.get("extract", "No summary found.")}
            else:
                return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Sorry, there was an error accessing Wikipedia."}

    # Default static response
    else:
        return {"answer": answer}

