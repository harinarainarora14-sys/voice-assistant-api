from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # built-in
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote
import string
import re

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
# Wikipedia fetch helper
# ------------------------
def fetch_wikipedia_summary(query: str):
    # Clean query
    wiki_keywords = [
        "tell me about", "who is", "what is", "search for",
        "give me information on", "explain", "tell me something about", "find info about"
    ]
    query_lower = query.lower()
    for kw in wiki_keywords:
        if query_lower.startswith(kw):
            query = query[len(kw):].strip()
            break
    query_clean = re.sub(r"[^\w\s]", "", query)
    query_clean = re.sub(r"\s+", " ", query_clean).strip()
    if not query_clean:
        return ""

    # Step 1: Use opensearch to get title
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "search": query_clean,
        "limit": 1,
        "namespace": 0,
        "format": "json"
    }

    try:
        resp = requests.get(search_url, params=params, timeout=7)
        data = resp.json()
        titles = data[1]
        if not titles:
            return ""
        title = titles[0]

        # Step 2: Fetch summary
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title, safe='')
        resp2 = requests.get(summary_url, timeout=7)
        if resp2.status_code == 200:
            extract = resp2.json().get("extract", "")
            return extract
        else:
            return ""
    except requests.exceptions.RequestException:
        return ""

# ------------------------
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...)):
    question_orig = question
    question = question.lower().strip()
    question = question.rstrip(string.punctuation + "!?")

    # Exact match
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question == q.lower().strip():
                return process_answer(intent, question_orig)

    # Fuzzy match
    best_match = None
    best_score = 0
    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent
    if best_match and best_score >= 85:
        return process_answer(best_match, question_orig)

    # Wikipedia fallback
    if len(question.split()) >= 3:
        summary = fetch_wikipedia_summary(question_orig)
        if summary:
            return {"answer": summary}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    # No match
    return {"answer": f"Sorry, I don't understand '{question_orig}'."}

# ------------------------
# Answer processing
# ------------------------
def process_answer(intent: str, question: str):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time → Indian time
    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now_india = datetime.now(india_tz)
        time_str = now_india.strftime("%I:%M %p")
        return {"answer": time_str, "type": "time_india"}

    # Wikipedia
    elif answer.upper() == "WIKIPEDIA":
        summary = fetch_wikipedia_summary(question)
        if summary:
            return {"answer": summary}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    # Default static
    else:
        return {"answer": answer}
