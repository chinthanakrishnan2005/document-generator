from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import json
import os
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# ✅ Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Secure API key
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

@app.get("/")
async def root():
    return {"message": "PRD Generator API is running"}

class InputData(BaseModel):
    input: str


# ✍️ Writer Agent (More Human Style)
def writer_agent(user_input):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": """You are an experienced Product Manager.
Write a detailed and human-like PRD.

IMPORTANT:
- Do NOT keep it too short
- Add depth and explanation in each section
- Each section should have at least 4–6 meaningful points
- Avoid generic statements
- Write like a real human, not robotic

Format in plain text (no * or markdown)

Include:
Title:
Overview:
Problem Statement:
User Stories:
Edge Cases:
Technical Requirements:
Success Metrics:
"""
                },
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"Writer Error: {e}")
        return "Error generating document."


# 🔍 Critic Agent
def critic_agent(document):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": """You are a strict reviewer.

Check if all sections exist:
- Title
- Overview
- Problem Statement
- User Stories
- Edge Cases
- Technical Requirements
- Success Metrics

Return ONLY JSON:
{
  "status": "approved" or "rejected",
  "missing_sections": [],
  "feedback": "short suggestions"
}
"""
                },
                {"role": "user", "content": document}
            ]
        )

        content = response.choices[0].message.content.strip()

        try:
            return json.loads(content)
        except:
            return {
                "status": "rejected",
                "missing_sections": [],
                "feedback": content
            }

    except Exception as e:
        logging.error(f"Critic Error: {e}")
        return {
            "status": "rejected",
            "missing_sections": [],
            "feedback": "Critic failed"
        }


# 🔁 Main API
@app.post("/generate-doc")
def generate_doc(data: InputData):
    user_input = data.input
    max_iterations = 3
    final_document = ""
    review = {"status": "rejected"}

    for i in range(max_iterations):
        logging.info(f"Iteration {i+1}")

        draft = writer_agent(user_input)
        review = critic_agent(draft)

        final_document = draft

        if review["status"] == "approved":
            break
        else:
            user_input += "\nImprove this:\n" + review["feedback"]

    return {
        "final_document": final_document,
        "status": review["status"],
        "iterations": i + 1
    }