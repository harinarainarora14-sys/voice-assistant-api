from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote

# Load responses
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

app = FastAPI()

# CORS middleware - allow your frontend (GitHub Pages or others)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with your frontend URL for security
    allow_credentials=False,  # Must be False when using "*"
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
    question = question.lower().strip()

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

    if best_match and best_score >= 80:  # stricter fuzzy threshold
        return process_answer(best_match, question)

    # --- Step 3: No match ---
    return {"answer": f"Sorry, I don't understand '{question}'."}


def process_answer(intent: str, question: str):
    """Handles the answer logic (time, wiki, or static)"""
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    if answer.upper() == "TIME":
        return {"answer": datetime.now().strftime("%I:%M %p")}  # hh:mm AM/PM

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

    else:
        return {"answer": answer}
