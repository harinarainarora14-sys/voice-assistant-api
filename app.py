from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from fuzzywuzzy import fuzz

# === Load responses.json ===
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

app = FastAPI()

# === Enable CORS for frontend ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "✅ Voice Assistant API is running"}

@app.post("/ask")
@app.get("/ask")
def ask(question: str = Query(...)):
    question_text = question.lower().strip()
    best_match = None
    best_score = 0

    # === Fuzzy matching to find best intent ===
    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question_text, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    # === Determine the answer ===
    if best_match and best_score > 60:
        answer = responses[best_match]["answer"]

        if answer == "TIME":
            answer_text = datetime.now().strftime("%I:%M %p")
        elif answer == "WIKIPEDIA":
            # Cloud-friendly fallback
            answer_text = "Sorry, I couldn't find anything on Wikipedia."
        else:
            answer_text = answer
    else:
        answer_text = f"Sorry, I don't understand '{question}'."

    # === Return conversation-style JSON ===
    return {
        "conversation": [
            {"you": question},
            {"assistant": answer_text}
        ]
    }
