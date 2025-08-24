from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import wikipedia
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
    allow_origins=["*"],   # allow all origins
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
    question = question.lower().strip()
    best_match = None
    best_score = 0

    # === Find best match using fuzzy matching ===
    for intent, data in responses.items():
        for q in data["question"]:
            score = fuzz.ratio(question, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    # === If match found ===
    if best_match and best_score > 60:   # threshold lowered for better matching
        answer = responses[best_match]["answer"]

        if answer == "TIME":
            return {"answer": datetime.now().strftime("%H:%M:%S")}
        elif answer == "WIKIPEDIA":
            try:
                return {"answer": wikipedia.summary(question, sentences=1)}
            except:
                return {"answer": "Sorry, I couldn't find that on Wikipedia."}
        else:
            return {"answer": answer}

    # === If no match ===
    return {"answer": f"Sorry, I don't understand '{question}'."}
