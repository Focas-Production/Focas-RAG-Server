import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from query import get_answer
from evaluate import evaluate_answer
from mcq_generator import generate_mcq, generate_multiple_mcqs

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

@app.route("/mcq/generate", methods=["POST"])
def generate_ca_mcq():
    """
    Generate real CA exam MCQ based on chapter/unit and difficulty.
    
    Request JSON:
    {
        "level": "Foundation",
        "subject": "accounting",
        "chapter_name": "Theoretical Framework",
        "unit_name": "Meaning and scope of accounting",  # Optional
        "difficulty": "easy",  # easy, medium, hard, very-hard
        "num_questions": 1
    }
    
    Response:
    {
        "success": true,
        "count": 1,
        "mcqs": [
            {
                "question_number": 1,
                "chapter_number": 1,
                "chapter_name": "Theoretical Framework",
                "unit_number": 1,
                "unit_name": "Meaning and scope of accounting",
                "difficulty": "easy",
                "question": "Question text...",
                "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
                "correct_answer": "A",
                "explanation": "Explanation..."
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "Request body is empty"}), 400
        
        # Validate required fields
        required = ["level", "subject", "chapter_name"]
        for field in required:
            if field not in data or not data[field]:
                return jsonify({"success": False, "error": f"Missing required: {field}"}), 400
        
        # Extract parameters
        level = str(data.get("level", "")).strip()
        subject = str(data.get("subject", "")).strip()
        chapter_name = str(data.get("chapter_name", "")).strip()
        unit_name = str(data.get("unit_name", "")).strip() if data.get("unit_name") else None
        difficulty = str(data.get("difficulty", "easy")).strip().lower()
        num_questions = data.get("num_questions", 1)
        
        # Validate difficulty
        valid_difficulties = ["easy", "medium", "hard", "very-hard", "very_hard"]
        if difficulty not in valid_difficulties:
            return jsonify({
                "success": False,
                "error": f"Invalid difficulty. Use: easy, medium, hard, very-hard"
            }), 400
        
        # Normalize very-hard
        if difficulty == "very_hard":
            difficulty = "very-hard"
        
        # Limit to requested number (no artificial limit)
        try:
            num_questions = int(num_questions)
        except (ValueError, TypeError):
            num_questions = 1
        
        if num_questions < 1:
            num_questions = 1
        
        print(f"\n{'='*70}")
        print(f"📌 MCQ Generation Request")
        print(f"   Level: {level}")
        print(f"   Subject: {subject}")
        print(f"   Chapter: {chapter_name}")
        if unit_name:
            print(f"   Unit: {unit_name}")
        print(f"   Difficulty: {difficulty}")
        print(f"{'='*70}")
        
        # Generate MCQ
        mcqs = generate_multiple_mcqs(
            level=level,
            subject=subject,
            chapter_name=chapter_name,
            num_questions=num_questions,
            difficulty=difficulty,
            unit_name=unit_name
        )
        
        if not mcqs:
            return jsonify({
                "success": False,
                "error": "Failed to generate MCQ",
                "count": 0,
                "mcqs": []
            }), 500
        
        # Success response
        return jsonify({
            "success": True,
            "count": len(mcqs),
            "message": f"Generated {len(mcqs)} {difficulty} MCQ(s)",
            "mcqs": mcqs
        }), 200
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)