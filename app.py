import json
import sounddevice as sd
import queue
import threading
import pyttsx3
from fuzzywuzzy import fuzz
from vosk import Model, KaldiRecognizer
from urllib.parse import quote
import requests
import string
from datetime import datetime, timezone

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
# Initialize TTS engine
# ------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speaking speed

# ------------------------
# Audio globals
# ------------------------
audio_queue = queue.Queue()
stop_flag = False

# ------------------------
# Audio callback
# ------------------------
def audio_callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

# ------------------------
# Process question locally
# ------------------------
def ask_question(question: str):
    # Lowercase, strip spaces and trailing punctuation
    question = question.lower().strip()
    question = question.rstrip(string.punctuation)

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

    if best_match and best_score >= 85:
        return process_answer(best_match, question)

    # --- Step 3: Wikipedia fallback for long questions ---
    if len(question.split()) >= 3:
        query = question.replace("tell me about", "").strip()
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("extract", "No summary found.")
            else:
                return "I couldn't find anything on Wikipedia."
        except requests.exceptions.RequestException:
            return "Sorry, there was an error accessing Wikipedia."

    # --- Step 4: No match ---
    return f"Sorry, I don't understand '{question}'."

# ------------------------
# Process answer
# ------------------------
def process_answer(intent: str, question: str):
    answer = responses[intent].get("answer", "Sorry, I don't understand that.")

    # Time request → return 12-hour hh:mm AM/PM
    if answer.upper() == "TIME":
        now_utc = datetime.now(timezone.utc)
        time_str = now_utc.strftime("%I:%M %p")  # 12-hour format
        return time_str

    # Wikipedia request
    elif answer.upper() == "WIKIPEDIA":
        query = question.replace("tell me about", "").strip()
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query)
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("extract", "No summary found.")
            else:
                return "I couldn't find anything on Wikipedia."
        except requests.exceptions.RequestException:
            return "Sorry, there was an error accessing Wikipedia."

    # Default static response
    else:
        return answer

# ------------------------
# Speak answer
# ------------------------
def speak(answer: str):
    print("Assistant:", answer)
    engine.say(answer)
    engine.runAndWait()

# ------------------------
# Continuous listening
# ------------------------
def continuous_listen(model_path="model"):
    global stop_flag
    stop_flag = False
    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    print("🎙️ Continuous mode started. Say 'stop' to end...")

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        while not stop_flag:
            data = audio_queue.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    print("You:", text)
                    if "stop" in text.lower():
                        stop_flag = True
                        print("🛑 Continuous mode stopped by user.")
                        break
                    threading.Thread(target=lambda: speak(ask_question(text)), daemon=True).start()

# ------------------------
# Single voice mode
# ------------------------
def single_listen(model_path="model"):
    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    print("🎙️ Say something...")
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        data = audio_queue.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if text:
                print("You:", text)
                speak(ask_question(text))

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    print("Select mode: 1 = Single voice, 2 = Continuous voice, 3 = Text input")
    mode = input("Mode: ").strip()
    if mode == "1":
        single_listen()
    elif mode == "2":
        continuous_listen()
    elif mode == "3":
        while True:
            q = input("You: ").strip()
            if q.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            speak(ask_question(q))
    else:
        print("Invalid mode selected.")
