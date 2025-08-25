from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote
import string
import re

# Load responses
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

app = FastAPI()

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
    question_clean = question.lower().strip()
    question_clean = question_clean.rstrip(string.punctuation + "!?")

    # Exact match
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question)

    # Fuzzy match
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

    # Wikipedia fallback
    if len(question_clean.split()) >= 3:
        summary = fetch_wikipedia_summary(question)
        if summary:
            return {"answer": summary}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    return {"answer": f"Sorry, I don't understand '{question}'."}

def process_answer(intent: str, question: str):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now_india = datetime.now(india_tz)
        time_str = now_india.strftime("%I:%M %p")
        return {"answer": time_str, "type": "time_india"}

    elif answer.upper() == "WIKIPEDIA":
        summary = fetch_wikipedia_summary(question)
        if summary:
            return {"answer": summary}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    else:
        return {"answer": answer}

def fetch_wikipedia_summary(question: str) -> str:
    wiki_keywords = [
        "tell me about", "who is", "what is", "search for",
        "give me information on", "explain", "tell me something about", "find info about"
    ]
    query = question
    for kw in wiki_keywords:
        if question.lower().startswith(kw):
            query = question[len(kw):].strip()
            break

    query_clean = re.sub(r"[^a-zA-Z0-9\s]", "", query)

    # Step 1: Search Wikipedia
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query_clean,
        "format": "json",
        "utf8": 1,
        "srlimit": 1
    }
    try:
        resp = requests.get(search_url, params=params, timeout=7)
        data = resp.json()
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return ""
        title = search_results[0]["title"]

        # Step 2: Fetch summary using REST API with proper URL encoding
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title, safe='')
        resp = requests.get(summary_url, timeout=7)
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            if extract:
                return extract
        return ""
    except requests.exceptions.RequestException:
        return ""
