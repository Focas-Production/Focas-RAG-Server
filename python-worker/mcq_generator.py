"""
mcq_generator.py - PRODUCTION-GRADE CA EXAM MCQ GENERATION
Generates VERY-HARD and HARD level MCQs for CA students
Selects optimal chunks and uses advanced prompting
"""

import os
import json
import pymongo
import random
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcq_prompts import (
    get_prompt, 
    get_system_prompt, 
    MAX_TOKENS, 
    MAX_QUESTIONS,
    randomize_correct_answer
)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

if not OPENAI_API_KEY or not MONGO_URI:
    raise ValueError("Missing OPENAI_API_KEY or MONGO_URI in environment")

# ===== SUBJECT-SPECIFIC LLM CONFIGURATIONS =====
SUBJECT_CONFIG = {
    "business_economics": {
        "temperature": 0.7,  # Lower for harder questions - more focused
        "model": "gpt-4-turbo",
        "max_tokens": 2500,
    },
    "accounting": {
        "temperature": 0.65,
        "model": "gpt-4-turbo",
        "max_tokens": 2500,
    },
    "auditing": {
        "temperature": 0.68,
        "model": "gpt-4-turbo",
        "max_tokens": 2500,
    },
    "taxation": {
        "temperature": 0.7,
        "model": "gpt-4-turbo",
        "max_tokens": 2500,
    },
    "law": {
        "temperature": 0.68,
        "model": "gpt-4-turbo",
        "max_tokens": 2500,
    },
    "cost_accounting": {
        "temperature": 0.7,
        "model": "gpt-4-turbo",
        "max_tokens": 2500,
    }
}

def get_llm_for_subject(subject):
    """Get subject-specific LLM configuration"""
    config = SUBJECT_CONFIG.get(subject.lower(), SUBJECT_CONFIG["business_economics"])
    
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        timeout=120  # Increased timeout for complex generation
    )
    
    return llm, config

def get_all_topics(level, subject, chapter_name, unit_name=None):
    """
    Fetch all unique topics for a chapter/unit with their chunk counts.
    Sorts by importance (chunk count).
    """
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        chunks_collection = db["icaichunks"]
        
        # Build query
        query = {
            "level": level,
            "subject": subject,
            "chapter_name": chapter_name
        }
        
        if unit_name:
            query["unit_name"] = unit_name
        
        # Get all chunks for this chapter/unit
        chunks = list(chunks_collection.find(query))
        client.close()
        
        if not chunks:
            print(f"❌ No chunks found")
            return []
        
        # Group by topic_name only
        topics_dict = {}
        for chunk in chunks:
            topic_name = chunk.get("topic_name", "Unknown")
            
            if topic_name not in topics_dict:
                topics_dict[topic_name] = {
                    "name": topic_name,
                    "chunk_count": 0,
                    "total_chunks": chunk.get("total_chunks_in_topic", 0)
                }
            
            topics_dict[topic_name]["chunk_count"] += 1
        
        # Convert to list and sort by chunk count (more chunks = more important)
        topics_list = list(topics_dict.values())
        topics_list.sort(key=lambda x: x["chunk_count"], reverse=True)
        
        print(f"✅ Found {len(topics_list)} unique topics")
        print(f"\n📊 TOPICS (sorted by importance):")
        for i, topic in enumerate(topics_list[:10], 1):
            print(f"   {i}. {topic['name']} ({topic['chunk_count']} chunks)")
        
        return topics_list
        
    except Exception as e:
        print(f"❌ Error fetching topics: {e}")
        return []

def select_best_topic_for_mcq(topics_list, exclude_topics=None, prefer_complex=True):
    """
    Select the BEST topic for MCQ generation.
    For very-hard MCQs, prefers topics with more chunks (more content to work with).
    
    Args:
        topics_list: List of available topics
        exclude_topics: List of topic names to exclude
        prefer_complex: If True, select topics with most chunks
    
    Returns:
        Selected topic or None
    """
    if exclude_topics is None:
        exclude_topics = []
    
    # Filter out already used topics
    available_topics = [t for t in topics_list if t["name"] not in exclude_topics]
    
    if not available_topics:
        print("⚠️ All topics exhausted, cycling back to beginning")
        return topics_list[0] if topics_list else None
    
    # Select topic with most chunks (importance-based, best for complex MCQs)
    best_topic = available_topics[0]
    
    print(f"\n🎯 BEST TOPIC SELECTED: {best_topic['name']}")
    print(f"   Importance Score: {best_topic['chunk_count']} chunks")
    print(f"   Total Content: {best_topic['total_chunks']} chunks in topic")
    
    return best_topic

def fetch_topic_chunks_optimized(level, subject, chapter_name, unit_name, topic_name):
    """
    Fetch ALL chunks for a specific topic for comprehensive MCQ generation.
    This ensures maximum content is available for complex questions.
    
    Args:
        topic_name: The topic_name to fetch
    
    Returns:
        Combined text of all chunks + metadata
    """
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        chunks_collection = db["icaichunks"]
        
        # Query for specific topic by NAME only (not topic_number)
        query = {
            "level": level,
            "subject": subject,
            "chapter_name": chapter_name,
            "topic_name": topic_name
        }
        
        # Add unit_name if provided
        if unit_name:
            query["unit_name"] = unit_name
        
        # Fetch ALL chunks sorted by chunk_order
        chunks = list(chunks_collection.find(query).sort("chunk_order", 1))
        client.close()
        
        if not chunks:
            print(f"❌ No chunks found for topic: {topic_name}")
            print(f"   Query: {query}")
            return "", None
        
        # Extract metadata from first chunk
        metadata = {
            "chapter_number": chunks[0].get("chapter_number"),
            "chapter_name": chunks[0].get("chapter_name"),
            "unit_number": chunks[0].get("unit_number"),
            "unit_name": chunks[0].get("unit_name"),
            "topic_name": chunks[0].get("topic_name"),
            "level": level,
            "subject": subject,
            "total_chunks": len(chunks)
        }
        
        # Combine all chunk texts in order
        combined_text = "\n\n".join([chunk.get("text", "") for chunk in chunks])
        
        # Check size
        text_length = len(combined_text)
        token_estimate = text_length / 4
        
        print(f"✅ Fetched {len(chunks)} chunks for topic")
        print(f"   Text size: {text_length} characters (~{int(token_estimate)} tokens)")
        print(f"   Safe for LLM: {'✅ YES' if token_estimate < 25000 else '⚠️ LARGE but OK'}")
        
        return combined_text, metadata
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return "", None

def parse_mcq_response(response_text):
    """Parse MCQ JSON response from LLM with robust error handling."""
    response_text = response_text.strip()
    
    # Try to extract JSON from markdown code blocks
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try to find JSON object
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        
        if start != -1 and end > start:
            try:
                return json.loads(response_text[start:end])
            except:
                return None
    
    return None

def validate_mcq(mcq):
    """Validate MCQ has all required fields."""
    required = ["question", "options", "explanation", "difficulty"]
    
    for field in required:
        if field not in mcq:
            return False
    
    if not isinstance(mcq["options"], list) or len(mcq["options"]) != 4:
        return False
    
    return True

def get_subject_context(subject):
    """Get subject-specific context"""
    subject_contexts = {
        "business_economics": {
            "name": "Business Economics",
            "focus": ["demand/supply", "market dynamics", "cost analysis", "policy implications"],
        },
        "accounting": {
            "name": "Financial Accounting",
            "focus": ["standards", "calculations", "practical scenarios", "consolidation"],
        },
        "auditing": {
            "name": "Auditing",
            "focus": ["procedures", "evidence", "compliance", "risk assessment"],
        },
        "law": {
            "name": "Business Law",
            "focus": ["principles", "case studies", "compliance", "statutory requirements"],
        },
        "taxation": {
            "name": "Income Tax",
            "focus": ["computations", "deductions", "planning", "policy"],
        },
        "cost_accounting": {
            "name": "Cost Accounting",
            "focus": ["methods", "analysis", "decisions", "costing systems"],
        }
    }
    
    return subject_contexts.get(subject.lower(), {
        "name": subject,
        "focus": ["general concepts"],
    })

def generate_mcq(level, subject, chapter_name, difficulty="very_hard", unit_name=None, 
                 question_number=1, topic_data=None):
    """
    Generate ONE HIGH-QUALITY MCQ based on a SPECIFIC TOPIC's chunks.
    Optimized for VERY-HARD level questions.
    
    Args:
        difficulty: 'easy', 'medium', 'hard', or 'very_hard'
        topic_data: Tuple of (context, metadata) for a specific topic
    """
    print(f"\n{'='*70}")
    print(f"🎯 Generating MCQ #{question_number} - {difficulty.upper()} LEVEL")
    print(f"   Level: {level}")
    print(f"   Subject: {subject}")
    print(f"   Chapter: {chapter_name}")
    if unit_name:
        print(f"   Unit: {unit_name}")
    print(f"{'='*70}")
    
    # Validate difficulty
    valid_difficulties = ["easy", "medium", "hard", "very_hard"]
    if difficulty.lower() not in valid_difficulties:
        difficulty = "very_hard"
    
    # Get subject-specific LLM
    llm, config = get_llm_for_subject(subject)
    print(f"\n🤖 LLM Configuration:")
    print(f"   Temperature: {config['temperature']} (lower = more focused for hard Qs)")
    print(f"   Model: {config['model']}")
    print(f"   Max tokens: {config['max_tokens']}")
    
    # Get context and metadata
    if topic_data is None:
        print("❌ No topic data provided")
        return None
    
    context, metadata = topic_data
    
    if not context:
        print("❌ Cannot generate MCQ without context")
        return None
    
    # Get subject context
    subject_context = get_subject_context(subject)
    
    print(f"\n📖 Content Details:")
    print(f"   Topic: {metadata['topic_name']}")
    print(f"   Chunks: {metadata['total_chunks']}")
    
    # Generate prompt
    print(f"\n📝 Preparing advanced prompt...")
    
    prompt = get_prompt(
        difficulty,
        context,
        metadata.get("chapter_number", 1),
        metadata.get("chapter_name", "Unknown"),
        metadata.get("unit_number", 1),
        metadata.get("unit_name", "Unknown"),
        subject_context,
        question_count=question_number,
        topic_name=metadata.get("topic_name", "")
    )
    
    system_prompt = get_system_prompt()
    
    # Call LLM
    print(f"\n⏳ Generating {difficulty.upper()} MCQ (this may take 30-60 seconds)...")
    try:
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None
    
    # Parse response
    print(f"📝 Parsing MCQ response...")
    mcq = parse_mcq_response(response_text)
    
    if not mcq:
        print("❌ Failed to parse MCQ response")
        print(f"   Response (first 500 chars): {response_text[:500]}")
        return None
    
    # Validate
    if not validate_mcq(mcq):
        print("❌ MCQ validation failed - missing required fields")
        return None
    
    # Randomize correct answer
    print(f"🔀 Randomizing answer options...")
    mcq = randomize_correct_answer(mcq)
    
    # Add metadata
    mcq["question_number"] = question_number
    if metadata:
        for key, value in metadata.items():
            if key not in mcq:
                mcq[key] = value
    
    print(f"✅ MCQ Generated Successfully!")
    print(f"   Type: {mcq.get('question_type', 'standard')}")
    print(f"   Difficulty: {mcq.get('difficulty', 'N/A')}")
    print(f"   Q: {mcq['question'][:80]}...")
    
    return mcq

def generate_multiple_mcqs(level, subject, chapter_name, num_questions=1, 
                          difficulty="very_hard", unit_name=None):
    """
    Generate multiple HIGH-QUALITY MCQs.
    Each MCQ uses the best available topic from the chapter.
    Optimized for VERY-HARD and HARD level questions.
    """
    try:
        num_questions = int(num_questions)
    except (ValueError, TypeError):
        num_questions = 1
    
    if num_questions > MAX_QUESTIONS:
        print(f"⚠️ Limiting {num_questions} to MAX_QUESTIONS ({MAX_QUESTIONS})")
        num_questions = MAX_QUESTIONS
    
    if num_questions < 1:
        num_questions = 1
    
    print(f"\n{'#'*70}")
    print(f"# CA EXAM MCQ GENERATION - PRODUCTION GRADE")
    print(f"# Level: {level} | Subject: {subject.upper()}")
    print(f"# Chapter: {chapter_name}")
    if unit_name:
        print(f"# Unit: {unit_name}")
    print(f"# Difficulty: {difficulty.upper()}")
    print(f"# Questions to Generate: {num_questions}")
    print(f"{'#'*70}\n")
    
    mcqs = []
    used_topics = []
    
    # Step 1: Get all topics for this chapter/unit
    print("📚 Step 1: Scanning for all topics in chapter...")
    topics_list = get_all_topics(level, subject, chapter_name, unit_name)
    
    if not topics_list:
        print("❌ No topics found in chapter")
        return []
    
    # Step 2: Generate MCQ for each topic (using best topics first)
    for i in range(num_questions):
        question_num = i + 1
        
        print(f"\n{'='*70}")
        print(f"📝 MCQ {question_num}/{num_questions}")
        print(f"{'='*70}")
        
        try:
            # Select BEST available topic
            selected_topic = select_best_topic_for_mcq(topics_list, exclude_topics=used_topics, prefer_complex=True)
            
            if not selected_topic:
                print(f"⚠️ No more topics available")
                break
            
            used_topics.append(selected_topic["name"])
            
            # Fetch OPTIMIZED chunks for this topic
            print(f"\n📚 Fetching comprehensive content for MCQ generation...")
            context, metadata = fetch_topic_chunks_optimized(
                level, subject, chapter_name, unit_name,
                selected_topic["name"]
            )
            
            if not context or metadata is None:
                print(f"⚠️ Skipping topic - no content retrieved")
                continue
            
            # Generate MCQ for this topic
            mcq = generate_mcq(
                level, subject, chapter_name,
                difficulty=difficulty,
                unit_name=unit_name,
                question_number=question_num,
                topic_data=(context, metadata)
            )
            
            if mcq:
                mcqs.append(mcq)
                print(f"\n✅ Successfully generated MCQ #{question_num}")
        
        except Exception as e:
            print(f"❌ Error generating MCQ {question_num}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print(f"\n{'#'*70}")
    print(f"# GENERATION COMPLETE")
    print(f"# ✅ Generated: {len(mcqs)}/{num_questions}")
    print(f"# ❌ Failed: {num_questions - len(mcqs)}")
    print(f"# 📊 Topics Used: {len(used_topics)}")
    print(f"{'#'*70}\n")
    
    return mcqs

# ===== CLI INTERFACE =====

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("\n📖 CA EXAM MCQ GENERATION - PRODUCTION GRADE")
        print("="*70)
        print("\nUsage: python mcq_generator.py <level> <subject> <chapter> <num_questions> [difficulty] [unit]\n")
        print("DIFFICULTY LEVELS: easy, medium, hard, very_hard (default: very_hard)\n")
        print("Examples:")
        print("  python mcq_generator.py Foundation business_economics 'Theory of production and cost' 2 very_hard")
        print("  python mcq_generator.py Foundation accounting 'Chapter Name' 1 hard")
        print("\nThese will generate EXTREMELY CHALLENGING MCQs suitable for CA exams.")
        print("="*70 + "\n")
        sys.exit(1)
    
    level = sys.argv[1]
    subject = sys.argv[2]
    chapter_name = sys.argv[3]
    num_questions = sys.argv[4]
    difficulty = sys.argv[5] if len(sys.argv) > 5 else "very_hard"
    unit_name = sys.argv[6] if len(sys.argv) > 6 else None
    
    print(f"💭 Generating {num_questions} {difficulty.upper()} MCQs...\n")
    mcqs = generate_multiple_mcqs(
        level, subject, chapter_name,
        num_questions=num_questions,
        difficulty=difficulty,
        unit_name=unit_name
    )
    
    # Display results
    print("\n" + "="*70)
    print("📊 GENERATED MCQs")
    print("="*70 + "\n")
    
    for mcq in mcqs:
        print(f"Q{mcq['question_number']}: {mcq['question'][:80]}...")
        print(f"   Difficulty: {mcq.get('difficulty', 'N/A')}")
        print(f"   Topic: {mcq.get('topic_name', 'N/A')}")
        print(f"   Options: {len(mcq.get('options', []))} choices")
        print(f"   Answer: {mcq.get('correct_answer', '?')}")
        print()