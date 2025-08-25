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
# Wikipedia helper
# ------------------------
def fetch_wikipedia_summary(query: str):
    """Fetch Wikipedia summary, handle disambiguation if needed."""
    query = "_".join([w.capitalize() for w in query.split()])
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        print(f"[DEBUG] Wikipedia API response: {data}")  # Debug

        # Page not found
        if data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
            return "I couldn't find anything on Wikipedia."

        # Disambiguation page
        if data.get("type") == "disambiguation":
            # Try first link from content_urls.desktop.page
            first_link = data.get("content_urls", {}).get("desktop", {}).get("page")
            if first_link:
                title = first_link.split("/")[-1]
                return fetch_wikipedia_summary(title)
            else:
                return "This topic is ambiguous. Try being more specific."

        # Normal extract
        extract = data.get("extract", "")
        if extract:
            return extract
        else:
            return "I couldn't find anything on Wikipedia."

    except requests.exceptions.RequestException:
        return "Sorry, there was an error accessing Wikipedia."

# ------------------------
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...)):
    question = question.lower().strip()
    question = question.rstrip(string.punctuation + "!?")

    # Step 1: Exact match
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question == q.lower().strip():
                return process_answer(intent, question)

    # Step 2: Fuzzy match
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

    # Step 3: Wikipedia fallback
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
        summary = fetch_wikipedia_summary(query)
        return {"answer": summary}

    # Step 4: No match
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
        summary = fetch_wikipedia_summary(query)
        return {"answer": summary}

    else:
        return {"answer": answer}
