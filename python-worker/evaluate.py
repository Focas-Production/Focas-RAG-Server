import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Embedding function
def get_embedding(text):
    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return embedding.data[0].embedding

def evaluate_answer(user_answer, reference_answer):
    # Step 1: Compute similarity
    user_emb = np.array(get_embedding(user_answer))
    ref_emb = np.array(get_embedding(reference_answer))
    similarity = np.dot(user_emb, ref_emb) / (np.linalg.norm(user_emb) * np.linalg.norm(ref_emb))
    similarity_score = round(similarity * 100, 2)

    # Step 2: Let GPT decide type & evaluation
    evaluation_prompt = f"""
    You are an expert CA exam evaluator.

    ### Evaluation Rules:
    1. Identify the question type (True/False, MCQ, Theoretical, Practical).
    2. Apply strict marking:
    - **True/False**:
        - Exact match → Correct (100)
        - Opposite → Wrong (0)
        - Explanation aligns but label wrong → Wrong (20)
    - **MCQ/Theoretical/Practical**:
        - Fully correct (exact meaning & steps match reference) → Correct (100)
        - Partial (some points wrong or missing) → Partial (40-80, proportional to correctness)
        - Wrong or irrelevant → Wrong (0)
    3. For Theoretical/Practical, consider the number of points correct vs wrong when deciding score.
    4. Always list mistakes explicitly, even small errors (spelling, missing terms, reversed meaning, etc.).

    ### Response Format:
    Correct Answer: <model-generated correct answer>
    Evaluation: <Correct / Partial / Wrong>
    Score: <0-100>
    Feedback: 
    - Mistake 1: ...
    - Mistake 2: ...
    - (List all mistakes clearly)

    ---
    Reference Answer (from PDF):
    {reference_answer}

    User Answer:
    {user_answer}

    Embedding Similarity Score: {similarity_score}
    """


    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a strict but fair CA exam evaluator."},
                  {"role": "user", "content": evaluation_prompt}]
    ).choices[0].message.content

    return response

