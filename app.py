from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json, requests, string
from datetime import datetime
from zoneinfo import ZoneInfo

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Home route
# ------------------------
@app.get("/")
def home():
    return {"message": "✅ Voice Assistant API running"}

# ------------------------
# Main ask endpoint
# ------------------------
@app.get("/ask")
def ask(question: str = Query(...), use_gemini: bool = False):
    question_clean = question.lower().strip().rstrip(string.punctuation + "!?")

    # Gemini API forced
    if use_gemini:
        gemini_answer = call_gemini_api(question)
        return {"answer": gemini_answer}

    # Step 1: Exact match
    for intent, data in responses.items():
        for q in data.get("question", []):
            if question_clean == q.lower().strip():
                return process_answer(intent, question)

    # Step 2: Fuzzy match
    from fuzzywuzzy import fuzz
    best_match, best_score = None, 0
    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question_clean, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent
    if best_match and best_score >= 85:
        return process_answer(best_match, question)

    # Step 3: Wikipedia fallback
    if len(question.split()) >= 3:
        wiki_keywords = ["tell me about", "who is", "what is", "search for",
                         "give me information on", "explain", "tell me something about", "find info about"]
        query = question
        for kw in wiki_keywords:
            if question.startswith(kw):
                query = question[len(kw):].strip()
                break
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(query)
        headers = {"User-Agent": "VoiceAssistant/1.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                extract = resp.json().get("extract", "")
                if extract:
                    return {"answer": extract}
        except requests.exceptions.RequestException:
            pass

    return {"answer": f"Sorry, I don't understand '{question}'."}

# ------------------------
# Answer processing
# ------------------------
def process_answer(intent: str, question: str):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")
    if answer.upper() == "TIME":
        india_tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(india_tz)
        return {"answer": now.strftime("%I:%M %p"), "type": "time_india"}
    elif answer.upper() == "WIKIPEDIA":
        return {"answer": f"Please search '{question}' on Wikipedia."}
    else:
        return {"answer": answer}

# ------------------------
# Gemini API call
# ------------------------
def call_gemini_api(question: str):
    API_KEY = "AIzaSyB4oYXN34edV8imQd7A_pYxuSSm9Hl5sso"
    url = "https://api.generativeai.google.com/v1beta2/models/text-bison-001:generate"
    payload = {
        "prompt": {"text": question},
        "temperature": 0.7,
        "maxOutputTokens": 300
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("candidates", [{}])[0].get("output", "No answer from Gemini")
        else:
            return "Gemini API Error"
    except:
        return "Error connecting to Gemini API"
