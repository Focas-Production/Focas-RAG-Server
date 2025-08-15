import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from query import get_answer
from evaluate import evaluate_answer

# Initialize Flask App
app = Flask(__name__)
CORS(app) # Enable cross-origin requests

@app.route("/query", methods=["POST"])
def handle_query():
    """Endpoint to get an answer from the RAG system."""
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' in request body"}), 400
    
    level = data.get("level", "Foundation")
    subject = data.get("subject", "accounting")
    question = data.get("question")
    
    print(f"API: Received query for {level}/{subject}: {question}")
    answer = get_answer(level, subject, question)
    
    # query.py returns a string, so we wrap it in a JSON object
    # In a real app, get_answer would return a dictionary with sources
    return jsonify({"answer": answer, "sources": []})

@app.route("/evaluate", methods=["POST"])
def handle_evaluation():
    """Endpoint to evaluate a user's answer against the correct one."""
    data = request.get_json()
    if not data or "user_answer" not in data or "reference_answer" not in data:
        return jsonify({"error": "Missing 'user_answer' or 'reference_answer'"}), 400

    user_answer = data.get("user_answer")
    reference_answer = data.get("reference_answer")
    
    print("API: Received request to evaluate an answer.")
    evaluation_result = evaluate_answer(user_answer, reference_answer)
    
    return jsonify({"evaluation": evaluation_result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)