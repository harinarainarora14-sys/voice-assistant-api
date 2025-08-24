import json
import datetime
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fuzzywuzzy import fuzz

# Load responses.json
with open("responses.json", "r") as f:
    RESPONSES = json.load(f)

app = FastAPI(
    title="Voice Assistant API",
    description="Simple AI assistant API (text only)",
    version="1.0"
)

# Enable CORS so frontend (GitHub Pages) can call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 🔒 Change to ["https://yourusername.github.io"] after testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def find_best_match(user_text: str):
    best_match, highest_score = None, 0
    for intent, data in RESPONSES.items():
        for q in data["question"]:
            score = fuzz.ratio(user_text.lower(), q.lower())
            if score > highest_score and score > 50:
                highest_score, best_match = score, intent
    return best_match


def fetch_wikipedia_summary(query: str):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("extract", "No summary found.")
    except:
        pass
    return "Sorry, I couldn't fetch info from Wikipedia."


@app.get("/")
async def root():
    return {"message": "Voice Assistant API is running"}


@app.post("/ask")
async def ask(question: str):
    text = question.strip().lower()

    # Exit intent
    if text in ["bye", "goodbye", "exit", "quit"]:
        return {"answer": RESPONSES["goodbye"]["answer"]}

    # Time intent
    if "time" in text:
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {"answer": f"The current time is {now}"}

    # Wikipedia intent
    for kw in RESPONSES["wikipedia"]["question"]:
        if kw in text:
            query = text.replace(kw, "").strip()
            if query:
                return {"answer": fetch_wikipedia_summary(query)}
            return {"answer": "Please tell me what to search on Wikipedia."}

    # Fuzzy match other responses
    match = find_best_match(text)
    if match:
        answer = RESPONSES[match]["answer"]
        if answer == "TIME":
            now = datetime.datetime.now().strftime("%I:%M %p")
            return {"answer": f"The current time is {now}"}
        return {"answer": answer}

    return {"answer": "I'm sorry, I don't know how to respond to that."}
