import os
import pymongo
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from query import get_answer
from evaluate import evaluate_answer
from mcq_generator import generate_mcq, generate_multiple_mcqs, generate_case_scenario_mcqs

load_dotenv()
load_dotenv(".env.local", override=True)

MONGO_URI = os.getenv("MONGO_URI")

# Initialize Flask App
app = Flask(__name__)
CORS(app)  # Enable cross-origin requests


# ── Shared MongoDB helper ─────────────────────────────────────────────────────

def _get_chunks_collection():
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_default_database()
    return client, db["icaichunks"]


def _trim_aggregate(pipeline_match, group_field):
    """
    Run a $group aggregation that trims whitespace from string fields
    to avoid duplicates caused by trailing/leading spaces in the data.
    """
    client, col = _get_chunks_collection()
    try:
        pipeline = [
            {"$match": pipeline_match},
            {"$group": {
                "_id": {"$trim": {"input": {"$ifNull": [f"${group_field}", ""]}}}
            }},
            {"$match": {"_id": {"$ne": ""}}},
            {"$sort": {"_id": 1}},
        ]
        return [doc["_id"] for doc in col.aggregate(pipeline)]
    finally:
        client.close()

@app.route("/data/levels", methods=["GET"])
def get_levels():
    """Distinct CA exam levels stored in the database."""
    try:
        levels = _trim_aggregate({}, "level")
        return jsonify(levels)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/data/subjects", methods=["GET"])
def get_subjects():
    """Distinct subjects for a given level."""
    level = request.args.get("level", "").strip()
    if not level:
        return jsonify({"error": "level is required"}), 400
    try:
        subjects = _trim_aggregate({"level": level}, "subject")
        return jsonify(subjects)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/data/chapters", methods=["GET"])
def get_chapters():
    """Distinct chapter names for a given level + subject (whitespace-deduplicated)."""
    level = request.args.get("level", "").strip()
    subject = request.args.get("subject", "").strip()
    if not level or not subject:
        return jsonify({"error": "level and subject are required"}), 400
    try:
        client, col = _get_chunks_collection()
        try:
            pipeline = [
                {"$match": {"level": level, "subject": subject}},
                {"$group": {
                    "_id": {"$trim": {"input": {"$ifNull": ["$chapter_name", ""]}}},
                    "chapter_number": {"$first": "$chapter_number"}
                }},
                {"$match": {"_id": {"$ne": ""}}},
                {"$sort": {"chapter_number": 1, "_id": 1}},
            ]
            chapters = [doc["_id"] for doc in col.aggregate(pipeline)]
        finally:
            client.close()
        return jsonify(chapters)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/data/units", methods=["GET"])
def get_units():
    """Units for a given level + subject + chapter_name."""
    level = request.args.get("level", "").strip()
    subject = request.args.get("subject", "").strip()
    chapter_name = request.args.get("chapter_name", "").strip()
    if not level or not subject or not chapter_name:
        return jsonify({"error": "level, subject, and chapter_name are required"}), 400
    try:
        client, col = _get_chunks_collection()
        try:
            pipeline = [
                {"$match": {"level": level, "subject": subject, "chapter_name": chapter_name}},
                {"$group": {
                    "_id": "$unit_number",
                    "unit_name": {"$first": {"$trim": {"input": {"$ifNull": ["$unit_name", ""]}}}}
                }},
                {"$match": {"_id": {"$ne": None}, "unit_name": {"$ne": ""}}},
                {"$sort": {"_id": 1}},
                {"$project": {"_id": 0, "unit_number": "$_id", "unit_name": 1}},
            ]
            units = list(col.aggregate(pipeline))
        finally:
            client.close()
        return jsonify(units)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/data/capabilities", methods=["GET"])
def get_capabilities():
    """Returns supported MCQ question types, difficulties, and limits."""
    return jsonify({
        "question_types": [
            {"value": "standard",      "label": "General MCQ"},
            {"value": "case_scenario", "label": "Case Study Based MCQ"},
        ],
        "difficulties": [
            {"value": "easy",      "label": "Easy"},
            {"value": "medium",    "label": "Medium"},
            {"value": "hard",      "label": "Hard"},
            {"value": "very-hard", "label": "Very Hard"},
        ],
        "unit_selection_available": True,
        "max_questions": {"standard": 10, "case_scenario": 6},
    })


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
    Generate real CA exam MCQ(s) based on chapter/unit and difficulty.

    Request JSON (standard MCQ):
    {
        "level": "Foundation",
        "subject": "accounting",
        "chapter_name": "Theoretical Framework",
        "unit_name": "Meaning and scope of accounting",  // optional
        "difficulty": "easy",                            // easy | medium | hard | very-hard
        "num_questions": 1
    }

    Request JSON (case-scenario MCQ):
    {
        "level": "Final",
        "subject": "taxation",
        "chapter_name": "Basic Concepts",
        "unit_name": "Residence and scope of total income",  // optional
        "difficulty": "very-hard",
        "num_questions": 4,
        "case_scenario": "true"
    }

    Standard MCQ Response:
    {
        "success": true,
        "type": "standard",
        "count": 1,
        "mcqs": [ { ... } ]
    }

    Case-Scenario MCQ Response:
    {
        "success": true,
        "type": "case_scenario",
        "case_scenario_title": "CASE SCENARIO 1",
        "case_scenario_narrative": "Full narrative...",
        "count": 4,
        "mcqs": [ { "question_number": 1, ... }, ... ],
        "metadata": { ... }
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

        # Extract common parameters
        level = str(data.get("level", "")).strip()
        subject = str(data.get("subject", "")).strip()
        chapter_name = str(data.get("chapter_name", "")).strip()
        unit_name = str(data.get("unit_name", "")).strip() if data.get("unit_name") else None
        difficulty = str(data.get("difficulty", "easy")).strip().lower()
        num_questions = data.get("num_questions") or data.get("numQuestions", 1)

        # Case-scenario flag: accepts boolean true, string "true",
        # or question_type == "case_scenario"
        raw_cs = data.get("case_scenario", False)
        raw_qt = str(data.get("question_type", "standard")).strip().lower()
        is_case_scenario = (
            raw_cs is True
            or str(raw_cs).strip().lower() == "true"
            or raw_qt == "case_scenario"
        )

        # Validate difficulty
        valid_difficulties = ["easy", "medium", "hard", "very-hard", "very_hard"]
        if difficulty not in valid_difficulties:
            return jsonify({
                "success": False,
                "error": "Invalid difficulty. Use: easy, medium, hard, very-hard"
            }), 400

        # Normalise very_hard → very-hard
        if difficulty == "very_hard":
            difficulty = "very-hard"

        try:
            num_questions = int(num_questions)
        except (ValueError, TypeError):
            num_questions = 1

        if num_questions < 1:
            num_questions = 1

        print(f"\n{'='*70}")
        print(f"📌 MCQ Generation Request — {'CASE SCENARIO' if is_case_scenario else 'STANDARD'}")
        print(f"   Level     : {level}")
        print(f"   Subject   : {subject}")
        print(f"   Chapter   : {chapter_name}")
        if unit_name:
            print(f"   Unit      : {unit_name}")
        print(f"   Difficulty: {difficulty}")
        print(f"   Questions : {num_questions}")
        print(f"{'='*70}")

        # ── CASE SCENARIO PATH ────────────────────────────────────────────────
        if is_case_scenario:
            result = generate_case_scenario_mcqs(
                level=level,
                subject=subject,
                chapter_name=chapter_name,
                difficulty=difficulty,
                num_questions=num_questions,
                unit_name=unit_name
            )

            if not result:
                return jsonify({
                    "success": False,
                    "error": "Failed to generate case scenario MCQs",
                    "type": "case_scenario",
                    "count": 0,
                    "mcqs": []
                }), 500

            narrative = result.get("case_scenario_narrative", "")
            questions = result.get("questions", [])
            for q in questions:
                q["case_scenario_narrative"] = narrative

            return jsonify({
                "success": True,
                "type": "case_scenario",
                "case_scenario_title": result.get("case_scenario_title", "CASE SCENARIO 1"),
                "case_scenario_narrative": narrative,
                "count": len(questions),
                "message": f"Generated case scenario with {len(questions)} {difficulty} MCQ(s)",
                "mcqs": questions,
                "metadata": result.get("metadata", {})
            }), 200

        # ── STANDARD MCQ PATH ─────────────────────────────────────────────────
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
                "type": "standard",
                "count": 0,
                "mcqs": []
            }), 500

        return jsonify({
            "success": True,
            "type": "standard",
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