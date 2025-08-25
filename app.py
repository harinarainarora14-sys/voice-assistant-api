from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Built-in in Python 3.9+
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
    question_clean = question.lower().strip()
    question_clean = question_clean.rstrip(string.punctuation + "!?")

    # Step 1: Exact match
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question_clean)

    # Step 2: Fuzzy match
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

    # Step 3: Wikipedia fallback
    if len(question_clean.split()) >= 3:
        summary = fetch_wikipedia_summary(question_clean)
        if summary:
            return {"answer": summary}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    # Step 4: No match
    return {"answer": f"Sorry, I don't understand '{question_clean}'."}


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
        summary = fetch_wikipedia_summary(question)
        if summary:
            return {"answer": summary}
        else:
            return {"answer": "I couldn't find anything on Wikipedia."}

    # Default static response
    else:
        return {"answer": answer}


# ------------------------
# Wikipedia helper
# ------------------------
def fetch_wikipedia_summary(query: str):
    # Remove common prefixes
    wiki_keywords = [
        "tell me about", "who is", "what is", "search for",
        "give me information on", "explain", "tell me something about", "find info about"
    ]
    query_lower = query.lower()
    for kw in wiki_keywords:
        if query_lower.startswith(kw):
            query = query[len(kw):].strip()
            break

    # Remove punctuation and extra spaces
    query_clean = re.sub(r"[^\w\s]", "", query)
    query_clean = re.sub(r"\s+", " ", query_clean).strip()
    if not query_clean:
        return ""

    # Wikipedia search API
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

        # Fetch summary
        title = search_results[0]["title"]
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title, safe='')
        resp2 = requests.get(summary_url, timeout=7)
        if resp2.status_code == 200:
            data2 = resp2.json()
            extract = data2.get("extract", "")
            return extract
        else:
            return ""
    except requests.exceptions.RequestException:
        return ""
