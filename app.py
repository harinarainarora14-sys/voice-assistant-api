from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from fuzzywuzzy import fuzz
import requests
from urllib.parse import quote
import openai
import tempfile
import os

# 🔑 OpenAI API Key (make sure it's set in environment before running)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load responses
try:
    with open("responses.json", "r") as f:
        responses = json.load(f)
except Exception as e:
    print("⚠️ Error loading responses.json:", e)
    responses = {}

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace "*" with frontend URL for security
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "✅ Voice Assistant API is running"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

# ✅ Text-based endpoint (unchanged, used by Chrome/Edge/etc.)
@app.get("/ask")
def ask(question: str = Query(...)):
    return process_question(question)


# ✅ Safari-only endpoint: takes audio, transcribes, then reuses same logic
@app.post("/ask-audio")
async def ask_audio(file: UploadFile = File(...)):
    try:
        # Save uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(await file.read())
            tmp.flush()
            tmp_path = tmp.name

        # Transcribe with Whisper
        with open(tmp_path, "rb") as audio_file:
            transcript = openai.Audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        question = transcript["text"]
        print(f"[Safari DEBUG] Transcript: {question}")

        # Reuse normal logic
        result = process_question(question)
        result["transcript"] = question
        return result

    except Exception as e:
        print("❌ Safari audio error:", e)
        return {"answer": "Error processing Safari audio", "error": str(e)}


# ✅ Shared logic for both text & Safari audio
def process_question(question: str):
    question = question.lower().strip()
    best_match = None
    best_score = 0

    for intent, data in responses.items():
        for q in data.get("question", []):
            score = fuzz.ratio(question, q.lower())
            if score > best_score:
                best_score = score
                best_match = intent

    print(f"[DEBUG] Best match: {best_match}, Score: {best_score}")

    if best_match and best_score > 60:
        answer = responses[best_match].get("answer", "Sorry, I don't understand that.")

        if answer.upper() == "TIME":
            return {"answer": datetime.now().strftime("%H:%M:%S")}

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

    return {"answer": f"Sorry, I don't understand '{question}'."}
