from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from datetime import datetime
from fuzzywuzzy import fuzz

# Load responses.json
with open("responses.json", "r") as f:
    responses = json.load(f)

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
    return {"message": "Voice Assistant API running"}

@app.get("/ask")
def ask(question: str = Query(...)):
    question = question.lower().strip()
    best_match = None
    best_score = 0

    for intent, data in responses.items():
        for q in data["question"]:
            score = fuzz.ratio(question, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    if best_match and best_score > 60:
        answer = responses[best_match]["answer"]

        if answer == "TIME":
            return {"answer": datetime.now().strftime("%H:%M:%S")}

        elif answer == "WIKIPEDIA":
            try:
                query = question.replace("tell me about", "").strip()
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    return {"answer": data.get("extract", "No summary found.")}
                else:
                    return {"answer": "I couldn't find anything on Wikipedia."}
            except:
                return {"answer": "Sorry, error accessing Wikipedia."}
        else:
            return {"answer": answer}

    return {"answer": f"Sorry, I don't understand '{question}'."}
