from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Built-in, no extra dependency
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
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...)):
    # Lowercase, strip spaces and trailing punctuation
    question = question.lower().strip()
    question = question.rstrip(string.punctuation + "!?")

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

    # --- Step 3: Wikipedia fallback for long questions ---
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

        # Format query for Wikipedia API: capitalize words, replace spaces with underscores
        query = "_".join([w.capitalize() for w in query.split()])
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
                    return {"answer": "I couldn't find anything on Wikipedia."}
                extract = data.get("extract", "")
                if extract:
                    return {"answer": extract}
                else:
                    return {"answer": "I couldn't find anything on Wikipedia."}
            else:
                return {"answer": "I couldn't find anything on Wikipedia."}
        except requests.exceptions.RequestException:
            return {"answer": "Sorry, there was an error accessing Wikipedia."}

    # --- Step 4: No match ---
    return {"answer": f"Sorry, I don't understand '{question}'."}


# ------------------------
# Answer processing
# ------------------------
def process_answer(intent: str, question: str):
    """Handles the answer logic (time, wiki, or static)"""
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time request → Indian local time 12-hour format
    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now_india = datetime.now(india_tz)
        time_str = now_india.strftime("%I:%M %p")  # 12-hour format
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

        # Format query for Wikipedia API: capitalize words, replace spaces with underscores
        query = "_".join([w.capitalize() for w in query.split()])
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
                    return {"answer": "I couldn't find anything on Wikipedia."}
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

