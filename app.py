from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Built-in, no extra dependency
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Helper: Wikipedia fetch with retry & debug
# ------------------------
def fetch_wikipedia_summary(query: str):
    wiki_keywords = [
        "tell me about", "who is", "what is", "search for",
        "give me information on", "explain", "tell me something about", "find info about"
    ]
    q = query.lower().strip()
    for kw in wiki_keywords:
        if q.startswith(kw):
            q = q[len(kw):].strip()
            break
    q = re.sub(r"[^\w\s]", "", q).strip()
    if not q:
        print("[DEBUG] Wikipedia query empty after cleaning")
        return ""

    # Try multiple times
    for attempt in range(2):
        try:
            print(f"[DEBUG] Wikipedia query attempt {attempt+1}: '{q}'")
            # Step 1: opensearch to get exact title
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {"action": "opensearch", "search": q, "limit": 1, "namespace": 0, "format": "json"}
            resp = requests.get(search_url, params=params, timeout=7)
            data = resp.json()
            titles = data[1]
            if not titles:
                print("[DEBUG] No titles found on Wikipedia")
                return ""
            title = titles[0]
            print(f"[DEBUG] Wikipedia resolved title: '{title}'")

            # Step 2: fetch summary
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
            resp2 = requests.get(summary_url, timeout=7)
            if resp2.status_code == 200:
                extract = resp2.json().get("extract", "")
                if extract:
                    print("[DEBUG] Wikipedia summary found")
                    return extract
                else:
                    print("[DEBUG] Wikipedia summary empty")
            else:
                print(f"[DEBUG] Wikipedia summary request failed, status: {resp2.status_code}")
            # fallback: wait and retry
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Wikipedia request exception: {e}")
            time.sleep(1)
    return ""

# ------------------------
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...)):
    question_orig = question
    question_clean = question.lower().strip().rstrip(string.punctuation + "!?")

    # Exact match
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question_orig)

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
        return process_answer(best_match, question_orig)

    # Wikipedia fallback
    if len(question_clean.split()) >= 3:
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
