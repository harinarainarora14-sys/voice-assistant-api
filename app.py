from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from datetime import datetime
from fuzzywuzzy import fuzz

# Load responses.json
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

app = FastAPI()

# Enable CORS
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

@app.get("/ask")
def ask(question: str = Query(...)):
    question_lower = question.lower().strip()
    best_match = None
    best_score = 0

    # Fuzzy match
    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question_lower, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    if best_match and best_score > 60:
        answer = responses[best_match]["answer"]

        # Return current time
        if answer == "TIME":
            return {"answer": datetime.now().strftime("%H:%M:%S")}

        # Wikipedia query
        elif answer == "WIKIPEDIA":
            query = question_lower.replace("wikipedia", "").strip()
            if not query:
                return {"answer": "Please tell me what to search on Wikipedia."}
            try:
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    return {"answer": data.get("extract", "No summary found.")}
                else:
                    return {"answer": "I couldn't find anything on Wikipedia."}
            except Exception:
                return {"answer": "Sorry, there was an error accessing Wikipedia."}

        # Predefined answer
        else:
            return {"answer": answer}

    # No match fallback
    return {"answer": f"Sorry, I don't understand '{question}'."}
