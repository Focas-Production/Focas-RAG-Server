"""
TEST SUBJECT PROMPT FOR MCQ GENERATION
Checks if:
1. Subject normalization works
2. Subject config loads correctly
3. Prompt generates MCQ
4. JSON parsing succeeds
"""

import os
import json
import random
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from mcq_prompts import (
    SYSTEM_PROMPT,
    SUBJECT_CONFIGURATIONS,
    normalize_subject_key
)

# --------------------------------------------------
# LOAD ENV VARIABLES
# --------------------------------------------------

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# --------------------------------------------------
# TEST INPUT
# --------------------------------------------------

subject = "Business Economics"
difficulty = "hard"

content_chunks = """
Demand refers to the quantity of a commodity that consumers are willing
and able to purchase at different prices during a given period of time.

Elasticity of demand measures the responsiveness of quantity demanded
to a change in price.
"""

# --------------------------------------------------
# SUBJECT CONFIGURATION
# --------------------------------------------------

subject_key = normalize_subject_key(subject)

config = SUBJECT_CONFIGURATIONS.get(subject_key)

if not config:
    raise ValueError(f"Subject config not found for: {subject}")

question_type = random.choice(config["question_types"][difficulty])

print("\n===== TEST DETAILS =====")
print("Subject:", subject)
print("Subject Key:", subject_key)
print("Difficulty:", difficulty)
print("Question Type:", question_type)

# --------------------------------------------------
# PROMPT
# --------------------------------------------------

prompt = f"""
Generate 1 {difficulty} CA exam MCQ.

Subject: {config["name"]}

Question Type:
{question_type}

Content:
{content_chunks}

IMPORTANT:
Return ONLY valid JSON.
Do NOT include markdown.
Do NOT include extra explanation.

JSON FORMAT:

{{
 "question": "",
 "options": {{
    "A": "",
    "B": "",
    "C": "",
    "D": ""
 }},
 "correct_answer": "A",
 "explanation": ""
}}
"""

# --------------------------------------------------
# INITIALIZE LLM
# --------------------------------------------------

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=api_key
)

# --------------------------------------------------
# CALL LLM
# --------------------------------------------------

response = llm.invoke([
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": prompt}
])

print("\n===== RAW RESPONSE =====\n")
print(response.content)

# --------------------------------------------------
# JSON PARSE TEST
# --------------------------------------------------

print("\n===== JSON VALIDATION =====")

try:
    data = json.loads(response.content)

    print("✅ JSON PARSED SUCCESSFULLY\n")

    print("Question:")
    print(data["question"])

    print("\nOptions:")
    for key, value in data["options"].items():
        print(f"{key}. {value}")

    print("\nCorrect Answer:", data["correct_answer"])

    print("\nExplanation:")
    print(data["explanation"])

except Exception as e:

    print("❌ JSON PARSE FAILED")
    print("Error:", e)