from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# Allow frontend requests (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict later to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load responses
with open("responses.json") as f:
    responses = json.load(f)

def get_response(question: str):
    q = question.lower()
    return responses.get(q, "Sorry, I don't understand that.")

@app.get("/")
def root():
    return {"message": "Voice Assistant API is running 🚀"}

@app.get("/ask")
def ask(question: str):
    answer = get_response(question)
    return {"answer": answer}
