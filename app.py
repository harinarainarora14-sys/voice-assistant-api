import json
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer
import sys
import os
from fuzzywuzzy import fuzz
import datetime
import queue
import threading
import time
import pyttsx3

class VoiceAssistant:
    def __init__(self):
        # Initialize TTS engine
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)

        # Response queue
        self.response_queue = queue.Queue()
        self.response_thread = threading.Thread(target=self._response_worker, daemon=True)
        self.response_thread.start()

        # Load JSON responses
        try:
            with open('responses.json', 'r') as f:
                self.responses = json.load(f)
        except FileNotFoundError:
            print("responses.json not found!")
            sys.exit(1)

        # Initialize Vosk model
        self.model_path = "vosk-model-small-en-us"
        self._ensure_vosk_model()
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

        # Flags
        self.running = True
        self.last_text = ""

    # Download Vosk model if missing
    def _ensure_vosk_model(self):
        if not os.path.exists(self.model_path):
            print("Downloading Vosk model (~50MB)...")
            # Skipping actual download for brevity, you can keep your existing code

    # Thread worker for TTS
    def _response_worker(self):
        while True:
            text = self.response_queue.get()
            if text is None:
                break
            print(f"Assistant: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
            self.response_queue.task_done()

    # Queue response
    def speak(self, text):
        self.response_queue.put(text)

    # Fuzzy match to JSON
    def find_best_match(self, user_question):
        best_match = None
        highest_score = 0
        for intent, data in self.responses.items():
            questions = data.get('question', [])
            for question in questions:
                score = fuzz.ratio(user_question.lower(), question.lower())
                if score > highest_score and score > 50:  # flexible threshold
                    highest_score = score
                    best_match = intent
        return best_match

    # Process audio from mic
    def process_audio_chunk(self, indata, frames, time_info, status):
        if status and status.input_overflow:
            print("[DEBUG] Input overflow")
            return
        if self.recognizer.AcceptWaveform(indata.tobytes()):
            result = json.loads(self.recognizer.Result())
            if result.get('text'):
                print("[DEBUG] Recognized:", result['text'])
                self.handle_input(result['text'])

    # Handle recognized text
    def handle_input(self, text):
        text = text.strip().lower()
        if len(text) < 2 or text == self.last_text:
            return
        self.last_text = text
        print(f"You: {text}")

        # Exit commands
        if text in ['stop', 'exit', 'quit', 'goodbye', 'bye']:
            answer = self.responses.get('goodbye', {}).get('answer', "Goodbye!")
            self.speak(answer)
            time.sleep(0.5)
            self.running = False
            return

        # Time command
        if "time" in text:
            now = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {now}")
            return

        # Wikipedia queries fallback
        wiki_keywords = self.responses.get('wikipedia', {}).get('question', [])
        for kw in wiki_keywords:
            if kw in text:
                self.speak("Sorry, I couldn't find anything on Wikipedia.")
                return

        # Fallback for "tell me something about ..."
        if "tell me something about" in text:
            self.speak("Sorry, I couldn't find anything on Wikipedia.")
            return

        # Other predefined responses
        best_match = self.find_best_match(text)
        if best_match:
            answer = self.responses[best_match]['answer']
            if answer == "TIME":
                now = datetime.datetime.now().strftime("%I:%M %p")
                self.speak(f"The current time is {now}")
            else:
                self.speak(answer)
        else:
            self.speak("I'm sorry, I don't have a response for that question.")

    # Run assistant
    def run(self):
        greeting = "Hello! I'm your voice assistant. How can I help you?"
        print(f"Assistant: {greeting}")
        self.engine.say(greeting)
        self.engine.runAndWait()

        try:
            with sd.InputStream(samplerate=16000,
                                channels=1,
                                dtype=np.int16,
                                blocksize=16000,
                                callback=self.process_audio_chunk):
                print("Listening... (Say 'stop' or 'exit' to end)")
                while self.running:
                    sd.sleep(1000)
        except KeyboardInterrupt:
            print("\nStopping the voice assistant...")
            goodbye = "Goodbye!"
            print(f"Assistant: {goodbye}")
            self.engine.say(goodbye)
            self.engine.runAndWait()


if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run()
