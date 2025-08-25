import json
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer
import queue
import threading
import requests
import pyttsx3
from urllib.parse import quote

# ------------------------
# Load responses (for local fallback)
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
# Globals for continuous listening
# ------------------------
audio_queue = queue.Queue()
stop_flag = False

# ------------------------
# Audio callback for microphone
# ------------------------
def audio_callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

# ------------------------
# Ask API function
# ------------------------
API_URL = "http://127.0.0.1:8000/ask"  # Replace with your deployed API

def ask_api(question):
    try:
        resp = requests.get(API_URL, params={"question": question}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "Sorry, I don't understand that.")
            print("Assistant:", answer)
            engine.say(answer)
            engine.runAndWait()
        else:
            engine.say("Sorry, the server didn't respond properly.")
            engine.runAndWait()
    except requests.exceptions.RequestException:
        engine.say("Sorry, I could not connect to the server.")
        engine.runAndWait()

# ------------------------
# Continuous listening loop
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
                    # Ask API asynchronously
                    threading.Thread(target=ask_api, args=(text,), daemon=True).start()

# ------------------------
# Single question voice mode
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
                ask_api(text)

# ------------------------
# Main entry point
# ------------------------
if __name__ == "__main__":
    print("Select mode: 1 = Single voice, 2 = Continuous voice")
    mode = input("Mode: ").strip()
    if mode == "1":
        single_listen()
    elif mode == "2":
        continuous_listen()
    else:
        print("Invalid mode selected.")

