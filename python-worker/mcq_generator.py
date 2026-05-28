"""
mcq_generator.py - PRODUCTION-GRADE CA EXAM MCQ GENERATION
Generates VERY-HARD and HARD level MCQs for CA students
Selects optimal chunks and uses advanced prompting
"""

import os
import re
import json
import time
import pymongo
import random
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcq_prompts import (
    get_prompt,
    get_case_scenario_prompt,
    MAX_QUESTIONS,
    normalize_options_order,
    normalize_subject_key,
)

MAX_GENERATION_RETRIES = 1   # 2 total attempts per topic; topic fallback handles the rest

# ── OpenAI error handling ────────────────────────────────────────────────────
_QUOTA_SIGNALS    = ("insufficient_quota", "exceeded your current quota", "billing_hard_limit_reached")
_RATE_LIM_SIGNALS = ("rate_limit_exceeded", "rate limit", "too many requests")


def _classify_llm_error(err_str: str) -> str:
    """Classify a 429/API error so we know whether to retry.

    Returns:
        'quota'      — billing exhausted; retry is pointless
        'rate_limit' — temporary throttle; retry after backoff
        'other'      — unknown; retry once
    """
    lower = err_str.lower()
    if any(s in lower for s in _QUOTA_SIGNALS):
        return "quota"
    if any(s in lower for s in _RATE_LIM_SIGNALS):
        return "rate_limit"
    return "other"


load_dotenv()
load_dotenv(".env.local", override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

if not OPENAI_API_KEY or not MONGO_URI:
    raise ValueError("Missing OPENAI_API_KEY or MONGO_URI in environment")

# ===== SUBJECT-SPECIFIC LLM CONFIGURATIONS =====
DEFAULT_MAX_TOKENS = int(os.getenv("MCQ_MAX_OUTPUT_TOKENS", "2000"))
DEFAULT_CONTEXT_TOKENS = int(os.getenv("MCQ_CONTEXT_TOKENS", "4000"))
DEFAULT_MAX_CHUNKS = int(os.getenv("MCQ_MAX_CHUNKS", "10"))

# Conceptual subjects (no heavy arithmetic) use a smaller token budget.
# Saves ~40% cost vs numerical subjects without hurting quality.
CONCEPTUAL_MAX_TOKENS = int(os.getenv("MCQ_CONCEPTUAL_MAX_OUTPUT_TOKENS", "1200"))
CONCEPTUAL_CONTEXT_TOKENS = int(os.getenv("MCQ_CONCEPTUAL_CONTEXT_TOKENS", "2500"))

_CONCEPTUAL_SUBJECTS = {
    "business_economics", "auditing", "law", "business_law",
    "auditing_ethics", "corporate_laws", "strategic_management", "advanced_auditing",
}

# Subjects that consistently need MORE tokens than DEFAULT_MAX_TOKENS:
# FM (leasing/NPV chains), AFM (derivatives), direct tax (treaty computations).
_HEAVY_NUMERICAL_MAX_TOKENS = int(os.getenv("MCQ_HEAVY_MAX_OUTPUT_TOKENS", "2500"))
_HEAVY_NUMERICAL_SUBJECTS = {
    "financial_management", "advanced_financial_management", "direct_tax_international",
}


def _max_tokens_for_subject(subject_key: str) -> int:
    if subject_key in _CONCEPTUAL_SUBJECTS:
        return CONCEPTUAL_MAX_TOKENS
    if subject_key in _HEAVY_NUMERICAL_SUBJECTS:
        return _HEAVY_NUMERICAL_MAX_TOKENS
    return DEFAULT_MAX_TOKENS


def _context_tokens_for_subject(subject_key: str) -> int:
    return CONCEPTUAL_CONTEXT_TOKENS if subject_key in _CONCEPTUAL_SUBJECTS else DEFAULT_CONTEXT_TOKENS


DEFAULT_COST_PER_1K_INPUT = float(os.getenv("MCQ_COST_PER_1K_INPUT", "0"))
DEFAULT_COST_PER_1K_OUTPUT = float(os.getenv("MCQ_COST_PER_1K_OUTPUT", "0"))

# Case-scenario generation needs a larger output budget (narrative + N questions)
CASE_SCENARIO_MAX_TOKENS = int(os.getenv("MCQ_CASE_SCENARIO_MAX_TOKENS", "4000"))

# Optional built-in pricing hints (override via env for accuracy)
# Real OpenAI pricing per 1K tokens (input, output)
# Override with MCQ_COST_PER_1K_INPUT / MCQ_COST_PER_1K_OUTPUT env vars if set to non-zero
_custom = (DEFAULT_COST_PER_1K_INPUT, DEFAULT_COST_PER_1K_OUTPUT)
MODEL_PRICING_PER_1K = {
    "gpt-4o":           _custom if DEFAULT_COST_PER_1K_INPUT else (0.00250, 0.01000),
    "gpt-4o-mini":      _custom if DEFAULT_COST_PER_1K_INPUT else (0.00015, 0.00060),
    "gpt-4.1":          _custom if DEFAULT_COST_PER_1K_INPUT else (0.00200, 0.00800),
    "gpt-4.1-mini":     _custom if DEFAULT_COST_PER_1K_INPUT else (0.00040, 0.00160),
}

# ── Model strategy ──────────────────────────────────────────────────────────
# gpt-4.1: used for all subjects.
#   - Significantly better multi-step arithmetic than gpt-4.1-mini
#   - Eliminates the "closest option" bug where the smaller model computed
#     approximate values and picked the nearest wrong option
#
# Temperature guide:
#   Numerical subjects: 0.1 — minimal randomness for deterministic calculations
#   Conceptual subjects: 0.4 — moderate creativity for scenario framing
# ────────────────────────────────────────────────────────────────────────────

SUBJECT_CONFIG = {
    # ── Generic fallback keys ──────────────────────────────────────────────────
    "business_economics": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "accounting": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "auditing": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "taxation": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "law": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "cost_accounting": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },

    # ── Foundation ─────────────────────────────────────────────────────────────
    "business_law": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "accounting_foundation": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },

    # ── Intermediate ───────────────────────────────────────────────────────────
    "advanced_accounts": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "auditing_ethics": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "corporate_laws": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "cost_management_accounting": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "financial_management": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "indirect_tax": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "income_tax": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "strategic_management": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },

    # ── Final ──────────────────────────────────────────────────────────────────
    "advanced_financial_management": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "advanced_auditing": {
        "temperature": 0.4,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "direct_tax_international": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
    "financial_reporting": {
        "temperature": 0.1,
        "model": "gpt-4.1",
        "max_tokens": DEFAULT_MAX_TOKENS,
    },
}

def get_llm_for_subject(subject):
    """Get subject-specific LLM configuration.

    Model selection (cheapest that maintains quality):
      Conceptual subjects → gpt-4.1-mini  (5× cheaper, no arithmetic)
      Numerical subjects  → gpt-4.1       (full accuracy for multi-step maths)

    Override via env:
      LLM_MODEL                  — forces ALL subjects to one model
      LLM_MODEL_CONCEPTUAL       — overrides conceptual default only
      LLM_MODEL_NUMERICAL        — overrides numerical default only
    """
    subject_key = normalize_subject_key(subject)
    config = SUBJECT_CONFIG.get(subject_key, SUBJECT_CONFIG["business_economics"])

    is_conceptual = subject_key in _CONCEPTUAL_SUBJECTS
    if is_conceptual:
        default_model = "gpt-4.1-mini"
        model = os.getenv("LLM_MODEL") or os.getenv("LLM_MODEL_CONCEPTUAL", default_model)
    else:
        default_model = "gpt-4.1"
        model = os.getenv("LLM_MODEL") or os.getenv("LLM_MODEL_NUMERICAL", default_model)

    max_tokens = _max_tokens_for_subject(subject_key)
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=model,
        temperature=config["temperature"],
        max_tokens=max_tokens,
        timeout=120
    )
    config = {**config, "model": model, "max_tokens": max_tokens}
    return llm, config

def extract_token_usage(response):
    """Extract token usage from LangChain response if available."""
    try:
        meta = getattr(response, "response_metadata", None) or {}
        usage = meta.get("token_usage") or meta.get("usage") or {}
        if usage:
            return {
                "input": usage.get("prompt_tokens") or usage.get("input_tokens"),
                "output": usage.get("completion_tokens") or usage.get("output_tokens"),
                "total": usage.get("total_tokens"),
            }
    except Exception:
        pass
    return None

def estimate_cost(model_name, token_usage):
    """Estimate cost using configured per-1K rates."""
    if not token_usage:
        return None
    input_tokens = token_usage.get("input") or 0
    output_tokens = token_usage.get("output") or 0
    rates = MODEL_PRICING_PER_1K.get(model_name, (0, 0))
    in_rate, out_rate = rates
    if in_rate == 0 and out_rate == 0:
        return None
    cost = (input_tokens / 1000.0) * in_rate + (output_tokens / 1000.0) * out_rate
    return cost

def get_all_topics(level, subject, chapter_name, unit_name=None):
    """
    Fetch all unique topics for a chapter/unit with their chunk counts.
    Uses MongoDB aggregation — does NOT load full chunk text into Python.
    """
    client = None
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        chunks_collection = db["icaichunks"]

        match_filter = {"level": level, "subject": subject, "chapter_name": chapter_name}
        if unit_name:
            match_filter["unit_name"] = unit_name

        def _run_aggregation(f):
            pipeline = [
                {"$match": f},
                {"$group": {
                    "_id": "$topic_name",
                    "chunk_count": {"$sum": 1},
                    "total_chunks": {"$first": "$total_chunks_in_topic"}
                }},
                {"$sort": {"chunk_count": -1}}
            ]
            return list(chunks_collection.aggregate(pipeline))

        results = _run_aggregation(match_filter)

        if not results:
            # Case-insensitive chapter_name fallback
            all_chapters = chunks_collection.distinct(
                "chapter_name", {"level": level, "subject": subject}
            )
            pattern = re.compile(re.escape(chapter_name), re.IGNORECASE)
            matched = [c for c in all_chapters if pattern.search(c)]
            if matched:
                print(f"   ⚠️ Exact match failed — using case-insensitive match: '{matched[0]}'")
                match_filter["chapter_name"] = matched[0]
                results = _run_aggregation(match_filter)

        if not results:
            print(f"❌ No chunks found for: level='{level}' subject='{subject}' chapter='{chapter_name}'")
            distinct_subjects = chunks_collection.distinct("subject", {"level": level})
            print(f"   Available subjects at level '{level}': {distinct_subjects}")
            distinct_chapters = chunks_collection.distinct("chapter_name", {"level": level, "subject": subject})
            print(f"   Available chapters for subject '{subject}': {distinct_chapters[:10]}")
            return []

        topics_list = [
            {"name": r["_id"], "chunk_count": r["chunk_count"], "total_chunks": r.get("total_chunks") or 0}
            for r in results
        ]

        print(f"✅ Found {len(topics_list)} unique topics")
        print(f"\n📊 TOPICS (sorted by importance):")
        for i, topic in enumerate(topics_list[:10], 1):
            print(f"   {i}. {topic['name']} ({topic['chunk_count']} chunks)")

        return topics_list

    except Exception as e:
        print(f"❌ Error fetching topics: {e}")
        return []
    finally:
        if client:
            client.close()

_TOPIC_SWEET_SPOT_MAX = int(os.getenv("MCQ_TOPIC_MAX_CHUNKS", "20"))


def select_best_topic_for_mcq(topics_list, exclude_topics=None, prefer_complex=True):
    """
    Select the best topic for MCQ generation.

    Cost-aware strategy:
    • Prefer "focused" topics with 3–20 chunks — they contain specific, well-scoped
      content that the LLM can build a coherent question around without looping.
    • Deprioritize huge topics (>20 chunks) — broad topics produce too many facts,
      causing the LLM to enter exploration loops and burn tokens on retries.
    • Fall back to large topics only when all focused ones are exhausted.
    """
    if exclude_topics is None:
        exclude_topics = []

    available = [t for t in topics_list if t["name"] not in exclude_topics]

    if not available:
        print("⚠️ All topics exhausted, cycling back to beginning")
        return topics_list[0] if topics_list else None

    # Sort: focused topics first (3–20 chunks), then large topics by chunk count
    def _score(t):
        c = t["chunk_count"]
        if 3 <= c <= _TOPIC_SWEET_SPOT_MAX:
            return (1, c)   # tier 1 — preferred, higher count wins within tier
        else:
            return (0, c)   # tier 0 — fallback (too small or too large)

    available.sort(key=_score, reverse=True)
    best_topic = available[0]

    tier = "focused" if 3 <= best_topic["chunk_count"] <= _TOPIC_SWEET_SPOT_MAX else "large/fallback"
    print(f"\n🎯 BEST TOPIC SELECTED: {best_topic['name']}")
    print(f"   Chunks: {best_topic['chunk_count']} ({tier})")

    return best_topic

def fetch_topic_chunks_optimized(level, subject, chapter_name, unit_name, topic_name,
                                  context_tokens=None):
    """
    Fetch chunks for a specific topic with a strict token budget.
    Ensures broad coverage while keeping cost under control.

    Args:
        topic_name: The topic_name to fetch
        context_tokens: Override the global DEFAULT_CONTEXT_TOKENS cap.
                        Pass _context_tokens_for_subject(subject_key) for per-subject budgets.

    Returns:
        Combined text of all chunks + metadata
    """
    if context_tokens is None:
        context_tokens = DEFAULT_CONTEXT_TOKENS
    client = None
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        chunks_collection = db["icaichunks"]

        query = {
            "level": level,
            "subject": subject,
            "chapter_name": chapter_name,
            "topic_name": topic_name
        }
        if unit_name:
            query["unit_name"] = unit_name

        # Project only needed fields — exclude embedding to reduce transfer size
        projection = {"text": 1, "chunk_order": 1, "chapter_number": 1,
                      "chapter_name": 1, "unit_number": 1, "unit_name": 1,
                      "topic_name": 1, "total_chunks_in_topic": 1, "_id": 0}

        chunks = list(chunks_collection.find(query, projection).sort("chunk_order", 1))

        if not chunks:
            # Case-insensitive chapter_name fallback
            all_chapters = chunks_collection.distinct(
                "chapter_name", {"level": level, "subject": subject}
            )
            pattern = re.compile(re.escape(chapter_name), re.IGNORECASE)
            matched = [c for c in all_chapters if pattern.search(c)]
            if matched:
                query["chapter_name"] = matched[0]
                chunks = list(chunks_collection.find(query, projection).sort("chunk_order", 1))

        if not chunks:
            print(f"❌ No chunks found for topic: {topic_name}")
            print(f"   Query: {query}")
            return "", None

        # Debug: confirm actual stored values
        first = chunks[0]
        print(f"   DB values — level='{level}' subject='{subject}' chapter='{first.get('chapter_name')}'")

        metadata = {
            "chapter_number": first.get("chapter_number"),
            "chapter_name": first.get("chapter_name"),
            "unit_number": first.get("unit_number"),
            "unit_name": first.get("unit_name"),
            "topic_name": first.get("topic_name"),
            "level": level,
            "subject": subject,
            "total_chunks": len(chunks)
        }

        def estimate_tokens(text):
            return max(1, int(len(text) / 4))

        chunk_texts = [chunk.get("text", "") for chunk in chunks]
        total_tokens = sum(estimate_tokens(t) for t in chunk_texts)

        if total_tokens <= context_tokens:
            selected_texts = chunk_texts
        else:
            avg_tokens = max(1, int(total_tokens / max(1, len(chunks))))
            target_count = max(4, min(DEFAULT_MAX_CHUNKS, int(context_tokens / avg_tokens)))
            target_count = min(len(chunks), target_count)
            step = max(1, int(len(chunks) / target_count))

            indices = list(range(0, len(chunks), step))
            if indices[-1] != len(chunks) - 1:
                indices.append(len(chunks) - 1)
            indices = indices[:target_count]

            selected_texts = [chunk_texts[i] for i in indices]

            while sum(estimate_tokens(t) for t in selected_texts) > context_tokens and len(selected_texts) > 4:
                selected_texts.pop()

        combined_text = "\n\n".join(selected_texts)

        print(f"✅ Fetched {len(chunks)} chunks for topic")
        print(f"   Selected: {len(selected_texts)} chunks (budget ~{context_tokens} tokens)")
        print(f"   Input tokens (est.): {estimate_tokens(combined_text)}")

        return combined_text, metadata

    except Exception as e:
        print(f"❌ Database Error: {e}")
        return "", None
    finally:
        if client:
            client.close()

_EXPLORATION_SIGNALS = (
    "not matching",
    "not match",
    "alternatively, perhaps",
    "alternatively, maybe",
    "let's check if",
    "let us check if",
    "still not matching",
    "does not match",
    "none of the options match",
    "options do not match",
    "options are not matching",
)


def parse_mcq_response(response_text):
    """Parse MCQ JSON response from LLM with robust error handling.

    Fast-fails (returns None) if the response contains exploration-loop signals
    — phrases like 'Alternatively, perhaps' or 'not matching' indicate the LLM
    got confused about its own options and is burning tokens trying alternatives.
    Returning None here triggers a retry with a fresh prompt.
    """
    lower = response_text.lower()
    for signal in _EXPLORATION_SIGNALS:
        if signal in lower:
            print(f"   ❌ LLM entered exploration loop ('{signal}') — discarding response")
            return None

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

_LABEL_RE = re.compile(r"^[A-D]\s*[\)\:\.\-]\s*", re.IGNORECASE)

# Detects a full A/B/C/D option block accidentally embedded in the question text
_EMBEDDED_OPTIONS_BLOCK_RE = re.compile(
    r"\n\s*[Aa]\s*[\)\:\.\-][^\n]*\n\s*[Bb]\s*[\)\:\.\-][^\n]*\n\s*[Cc]\s*[\)\:\.\-]",
    re.MULTILINE,
)


def strip_embedded_options(mcq: dict) -> dict:
    """Strip A/B/C/D option block accidentally embedded inside the question text."""
    q = mcq.get("question", "")
    if not q:
        return mcq
    m = _EMBEDDED_OPTIONS_BLOCK_RE.search(q)
    if m:
        print(f"   🔧 Stripping embedded options from question text (pos {m.start()})")
        mcq["question"] = q[: m.start()].rstrip()
    return mcq


def _normalize_option_body(text: str) -> str:
    """Normalize option body for duplicate detection: strip label, ₹/Rs., commas."""
    text = _LABEL_RE.sub("", str(text)).strip().lower()
    text = re.sub(r"[₹\s,]", "", text)
    text = re.sub(r"rs\.?", "", text)
    return text

# Extracts standalone Indian-format numbers: ₹1,23,456 / 1,23,456 / 1234.56
_NUMBER_RE = re.compile(
    r"(?:₹\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
)


def _normalise_number(raw: str) -> float:
    """Strip currency symbols, commas, whitespace → float for comparison."""
    cleaned = raw.replace("₹", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return float("nan")


def _extract_numbers(text: str):
    """Return sorted list of unique floats found in text."""
    nums = set()
    for m in _NUMBER_RE.finditer(text):
        v = _normalise_number(m.group(0))
        if not (v != v):  # skip NaN
            nums.add(v)
    return sorted(nums)


def detect_closest_option_bug(mcq: dict) -> tuple:
    """
    Detects the 'closest option' bug: LLM computes ₹X in the explanation but
    no option contains ₹X, and the correct option is a nearby wrong value.

    Strategy:
    1. Find the last number in the explanation's working section (before ✅).
       Using the last number (by position) avoids false positives from large
       intermediate values in multi-step calculations (e.g. total cost ₹60L
       appearing before a final depletion of ₹14L).
    2. Check if that value appears in ANY of the 4 options.
    3. Only flag if the explanation's final value is absent from all options
       AND the correct option contains a meaningfully different value.

    Returns (bug_detected: bool, detail: str).
    """
    explanation = mcq.get("explanation", "")
    correct_letter = str(mcq.get("correct_answer", "")).strip().upper()
    if correct_letter not in {"A", "B", "C", "D"}:
        return False, "invalid letter — skip"

    options = mcq.get("options", [])
    correct_opt_text = next(
        (o for o in options if str(o).strip().upper().startswith(correct_letter)),
        ""
    )
    if not correct_opt_text:
        return False, "no matching option — skip"

    # Use only the part of the explanation BEFORE the anchor
    anchor_idx = explanation.find("✅")
    work_text = explanation[:anchor_idx] if anchor_idx != -1 else explanation
    # Last 200 chars — closer to the actual computed answer
    work_snippet = work_text[-200:] if len(work_text) > 200 else work_text

    # Collect numbers in order of appearance (not sorted by value)
    expl_ordered = []
    for m in _NUMBER_RE.finditer(work_snippet):
        v = _normalise_number(m.group(0))
        if not (v != v) and v > 0:  # skip NaN and zero
            expl_ordered.append(v)

    opt_nums = _extract_numbers(correct_opt_text)

    if not expl_ordered or not opt_nums:
        return False, "no numbers to compare"

    # Last number by position is the most likely final computed answer
    main_expl_val = expl_ordered[-1]
    main_opt_val  = max(opt_nums)

    if main_opt_val == 0:
        return False, "zero value — skip"

    diff_pct = abs(main_expl_val - main_opt_val) / max(abs(main_opt_val), 1) * 100
    if diff_pct <= 0.5 or abs(main_expl_val - main_opt_val) <= 1:
        return False, "ok"

    # Only flag if the explanation's final value is absent from ALL options —
    # multi-step problems legitimately have intermediate values that don't
    # appear in any option (they're just calculation steps, not the answer).
    all_opt_text = " ".join(str(o) for o in options)
    all_opt_nums = _extract_numbers(all_opt_text)
    if any(
        abs(main_expl_val - n) / max(abs(n), 1) * 100 < 0.5
        for n in all_opt_nums
    ):
        return False, "explanation value found in options — ok"

    return (
        True,
        f"explanation computed {main_expl_val:,.2f} but this value is absent "
        f"from all 4 options; correct option ({correct_letter}) contains "
        f"{main_opt_val:,.2f} — possible 'closest option' bug"
    )

_EQ_VAL_RE = re.compile(
    r"=\s*(?:Rs\.?\s*|₹\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _numerical_autocorrect(mcq: dict):
    """
    Catch label-confusion bugs: explanation correctly computes ₹X but then
    refers to the wrong option letter as containing ₹X (e.g., LLM says
    'Option B is ₹6,00,000' when Option B is actually ₹12,00,000).

    Strategy:
    1. Strip the 'Option X is…' discussion section and the ✅ anchor.
    2. Find the last '= ₹X' computed value in the pure calculation text.
    3. If the correct option does NOT contain that value but another option
       does, return that letter for auto-correction.
    Returns the corrected letter, or None if no correction is needed.
    """
    explanation = mcq.get("explanation", "")
    correct_letter = str(mcq.get("correct_answer", "")).strip().upper()
    options = mcq.get("options", [])

    if not explanation or correct_letter not in {"A", "B", "C", "D"}:
        return None

    # Cut off at ✅ anchor
    anchor_idx = explanation.find("✅")
    work_text = explanation[:anchor_idx] if anchor_idx != -1 else explanation

    # Strip the option-discussion section ("Option A is…", "Option B is…")
    opt_discuss = re.search(
        r"\bOption\s+[A-D]\s+(?:is|shows|gives|represents|would|will)\b",
        work_text,
        re.IGNORECASE,
    )
    if opt_discuss:
        work_text = work_text[: opt_discuss.start()]

    # Find the last "= ₹X" or "= X" in the pure calculation text
    eq_matches = list(_EQ_VAL_RE.finditer(work_text))
    if not eq_matches:
        return None

    last_computed = _normalise_number(eq_matches[-1].group(1))
    if last_computed != last_computed or last_computed == 0:  # NaN / zero
        return None

    # If the correct option already contains this value, no fix needed
    correct_opt_text = next(
        (o for o in options if str(o).strip().upper().startswith(correct_letter)), ""
    )
    correct_nums = _extract_numbers(correct_opt_text)
    if any(abs(last_computed - n) / max(abs(n), 1) * 100 < 0.5 for n in correct_nums):
        return None

    # Find which other option matches the computed value
    for opt in options:
        opt_text = str(opt).strip()
        m = re.match(r"^([A-D])\s*[:\)\.\-]\s*", opt_text, re.IGNORECASE)
        if not m:
            continue
        letter = m.group(1).upper()
        if letter == correct_letter:
            continue
        opt_nums = _extract_numbers(opt_text)
        if any(abs(last_computed - n) / max(abs(n), 1) * 100 < 0.5 for n in opt_nums):
            return letter

    return None


# Patterns that signal which option the explanation declares correct.
# Ordered from most-specific to least-specific.
_EXPLANATION_ANSWER_PATTERNS = [
    re.compile(r"✅\s*[Cc]orrect\s+[Aa]nswer[:\s]+[Oo]ption\s*([A-D])", re.IGNORECASE),
    re.compile(r"[Cc]orrect\s+[Aa]nswer\s+is\s+(?:[Oo]ption\s*)?([A-D])\b", re.IGNORECASE),
    re.compile(r"[Aa]nswer\s+is\s+(?:[Oo]ption\s*)?([A-D])\b", re.IGNORECASE),
    re.compile(r"[Oo]ption\s+([A-D])\s+is\s+(?:the\s+)?correct", re.IGNORECASE),
    re.compile(r"[Tt]herefore[,.]?\s+(?:[Oo]ption\s*)?([A-D])\b", re.IGNORECASE),
    re.compile(r"[Hh]ence[,.]?\s+(?:[Oo]ption\s*)?([A-D])\b", re.IGNORECASE),
    re.compile(r"^([A-D])\s+is\s+(?:the\s+)?correct", re.IGNORECASE | re.MULTILINE),
]


def extract_stated_answer_from_explanation(explanation: str):
    """
    Try to detect which option letter the explanation declares as correct.
    Returns the letter (A/B/C/D) or None if not found.
    """
    for pattern in _EXPLANATION_ANSWER_PATTERNS:
        m = pattern.search(explanation)
        if m:
            return m.group(1).upper()
    return None


def try_autocorrect_answer(mcq: dict) -> dict:
    """
    Two-stage fix for wrong correct_answer:
    1. Letter mismatch: explanation explicitly states a different option letter.
    2. Label confusion: explanation computes ₹X but marks the wrong option
       (e.g., computes ₹6,00,000 but labels Option B as correct when
       ₹6,00,000 is actually Option A).
    Returns the (possibly corrected) mcq dict.
    """
    explanation = mcq.get("explanation", "")
    current = str(mcq.get("correct_answer", "")).strip().upper()

    # Stage 1 — letter stated in explanation
    stated = extract_stated_answer_from_explanation(explanation)
    if stated and stated != current and stated in {"A", "B", "C", "D"}:
        print(f"   ⚠️  Answer mismatch detected: correct_answer='{current}' but explanation states '{stated}'")
        print(f"   🔧 Auto-correcting correct_answer → '{stated}'")
        mcq["correct_answer"] = stated
        return mcq

    # Stage 2 — numerical label-confusion fix
    num_fix = _numerical_autocorrect(mcq)
    if num_fix:
        print(f"   ⚠️  Label confusion: computed value matches option {num_fix}, not {current}")
        print(f"   🔧 Auto-correcting correct_answer → '{num_fix}'")
        mcq["correct_answer"] = num_fix

    return mcq


def validate_mcq(mcq):
    """
    Validate MCQ structure and quality.
    Returns (is_valid: bool, reason: str).
    Checks: required fields, 4 options, valid correct_answer letter, no duplicate options,
    and explanation-answer consistency.
    """
    required = ["question", "options", "explanation", "difficulty", "correct_answer"]
    for field in required:
        if field not in mcq:
            return False, f"Missing field: {field}"

    # Explanation must be non-empty and long enough to be real working
    expl = str(mcq.get("explanation", "")).strip()
    if not expl:
        return False, "Empty explanation"
    if len(expl) < 80:
        return False, f"Explanation too short ({len(expl)} chars) — likely truncated"

    if not isinstance(mcq["options"], list) or len(mcq["options"]) != 4:
        return False, f"Expected 4 options, got {len(mcq.get('options', []))}"

    correct = str(mcq.get("correct_answer", "")).strip().upper()
    if correct not in {"A", "B", "C", "D"}:
        return False, f"Invalid correct_answer: '{correct}'"

    # Check for multiple sub-questions (LLM asked to find X and Y together)
    q_text = mcq.get("question", "")
    if q_text.count("?") > 1:
        return False, "Multiple question marks — question asks for more than one value"
    multi_part = re.search(
        r"\(\s*(?:i{1,3}|iv|v|[1-9])\s*\).*\(\s*(?:ii|iii|iv|v|[2-9])\s*\)",
        q_text, re.DOTALL | re.IGNORECASE,
    )
    if multi_part:
        return False, "Multiple sub-questions detected (e.g., '(i)...(ii)...')"

    # Extract option bodies and check uniqueness (normalize ₹/Rs./commas first)
    bodies = [_normalize_option_body(opt) for opt in mcq["options"]]
    if len(set(bodies)) < len(bodies):
        dupes = list({b for b in bodies if bodies.count(b) > 1})
        return False, f"Duplicate options: {dupes[:2]}"

    # Cross-check: does the explanation agree with correct_answer?
    stated = extract_stated_answer_from_explanation(mcq.get("explanation", ""))
    if stated and stated != correct:
        # Before rejecting, verify numerically. If the numerical computation
        # independently selects `correct` (e.g., explanation says 'Option B'
        # but computed ₹6,00,000 is Option A and correct_answer was fixed to A
        # by the label-confusion autocorrect), trust the numbers over the label.
        num_confirm = _numerical_autocorrect({**mcq, "correct_answer": stated})
        if num_confirm == correct:
            pass  # numerical computation overrides the confabulated letter
        else:
            return False, f"Explanation states '{stated}' is correct but correct_answer is '{correct}'"

    # Detect "closest option" bug: explanation computes X but correct option contains Y
    bug, detail = detect_closest_option_bug(mcq)
    if bug:
        print(f"   ⚠️  Closest-option bug detected: {detail}")
        return False, f"Closest-option bug: {detail}"

    return True, "valid"

def get_subject_context(subject):
    """Get subject-specific context.

    ``subject`` is the EXACT MongoDB subject name (e.g. "Cost and Management
    Accounting", "IDT", "Advanced auditing,Assurance and Professional ethics").
    The original name is preserved as the display name; an internal config_key
    is added for prompt-level lookups.
    """
    config_key = normalize_subject_key(subject)

    focus_map = {
        "business_economics": ["demand/supply", "market dynamics", "cost analysis", "policy implications"],
        "accounting":         ["standards", "calculations", "practical scenarios", "consolidation"],
        "auditing":           ["procedures", "evidence", "compliance", "risk assessment"],
        "law":                ["principles", "case studies", "compliance", "statutory requirements"],
        "taxation":           ["computations", "deductions", "planning", "policy"],
        "cost_accounting":    ["methods", "analysis", "decisions", "costing systems"],
    }

    return {
        "name": subject,                                    # original DB name — used in prompt display
        "config_key": config_key,                           # internal key — used for config lookups
        "focus": focus_map.get(config_key, ["general concepts"]),
    }

def generate_mcq(level, subject, chapter_name, difficulty="very_hard", unit_name=None,
                 question_number=1, topic_data=None, used_question_types=None):
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
    
    # ── Model setup ───────────────────────────────────────────────────────────
    llm, config = get_llm_for_subject(subject)
    print(f"\n🤖 LLM Configuration:")
    print(f"   Model      : {config['model']}")
    print(f"   Max tokens : {config['max_tokens']}")
    print(f"   Temperature: {config['temperature']}")
    
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
        topic_name=metadata.get("topic_name", ""),
        used_question_types=used_question_types or [],
    )
    
    # Call LLM with retry on validation failure
    print(f"\n⏳ Generating {difficulty.upper()} MCQ (this may take 30-60 seconds)...")
    mcq = None
    for attempt in range(MAX_GENERATION_RETRIES + 1):
        if attempt > 0:
            print(f"🔄 Retry {attempt}/{MAX_GENERATION_RETRIES} — regenerating...")

        try:
            response = llm.invoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)

            usage = extract_token_usage(response)
            model_name = config.get("model", "unknown")
            if usage:
                out_tok = usage.get("output") or 0
                print(f"📊 Token usage: input={usage.get('input')}, output={out_tok}, total={usage.get('total')}")
                cost = estimate_cost(model_name, usage)
                if cost is not None:
                    print(f"💰 Approx cost ({model_name}): ${cost:.4f}")
                # If output hit the hard cap, the JSON was cut off mid-stream.
                # Skip parsing entirely and retry — no point running the exploration
                # loop check on a truncated response (false positives happen here).
                if out_tok >= config.get("max_tokens", DEFAULT_MAX_TOKENS):
                    print(f"   ⚠️  Output truncated at {out_tok} tokens — retrying with fresh generation")
                    if attempt >= MAX_GENERATION_RETRIES:
                        print(f"❌ Response keeps truncating — consider increasing MCQ_HEAVY_MAX_OUTPUT_TOKENS")
                        return None
                    continue
        except Exception as e:
            err_type = _classify_llm_error(str(e))
            if err_type == "quota":
                print(f"❌ OpenAI quota exhausted — add credits at platform.openai.com/account/billing")
                print(f"   (Retrying will NOT help — aborting immediately)")
                return None
            if err_type == "rate_limit":
                wait = 15 * (attempt + 1)   # 15 s, 30 s, 45 s
                print(f"⏳ Rate limited — waiting {wait}s before retry {attempt + 1}/{MAX_GENERATION_RETRIES}...")
                time.sleep(wait)
            else:
                print(f"❌ LLM Error: {e}")
            if attempt >= MAX_GENERATION_RETRIES:
                return None
            continue

        print(f"📝 Parsing MCQ response (attempt {attempt + 1})...")
        parsed = parse_mcq_response(response_text)

        if not parsed:
            print(f"❌ Failed to parse JSON response")
            if attempt >= MAX_GENERATION_RETRIES:
                print(f"   Response (first 500 chars): {response_text[:500]}")
                return None
            continue

        # Attempt to auto-correct answer-explanation mismatch before validation
        parsed = strip_embedded_options(parsed)
        parsed = try_autocorrect_answer(parsed)

        is_valid, reason = validate_mcq(parsed)
        if is_valid:
            mcq = parsed
            break

        print(f"⚠️ Validation failed: {reason}")
        if attempt >= MAX_GENERATION_RETRIES:
            print(f"❌ MCQ generation failed after {MAX_GENERATION_RETRIES} retries: {reason}")
            return None

    if not mcq:
        return None

    # Normalize options order/format
    print("🔤 Normalizing answer options to A-D...")
    mcq = normalize_options_order(mcq)
    
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
    used_question_types = []

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

        # Try up to 3 different topics per question — if one topic consistently
        # triggers exploration loops, fall back to the next best topic.
        max_topic_fallbacks = min(3, len(topics_list))
        mcq = None

        for topic_attempt in range(max_topic_fallbacks):
            try:
                # Select BEST available topic (different from previously used ones)
                selected_topic = select_best_topic_for_mcq(
                    topics_list, exclude_topics=used_topics, prefer_complex=True
                )

                if not selected_topic:
                    print(f"⚠️ No more topics available")
                    break

                used_topics.append(selected_topic["name"])

                if topic_attempt > 0:
                    print(f"🔁 Topic fallback {topic_attempt}/{max_topic_fallbacks - 1} — trying '{selected_topic['name']}'")

                # Fetch OPTIMIZED chunks for this topic
                print(f"\n📚 Fetching comprehensive content for MCQ generation...")
                context, metadata = fetch_topic_chunks_optimized(
                    level, subject, chapter_name, unit_name,
                    selected_topic["name"],
                    context_tokens=_context_tokens_for_subject(normalize_subject_key(subject)),
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
                    topic_data=(context, metadata),
                    used_question_types=used_question_types,
                )

                if mcq:
                    break  # Success — stop trying more topics for this question

                print(f"⚠️ Topic '{selected_topic['name']}' failed all retries — trying next topic")

            except Exception as e:
                print(f"❌ Error generating MCQ {question_num}: {e}")
                import traceback
                traceback.print_exc()

        if mcq:
            mcqs.append(mcq)
            q_type = mcq.get("question_type")
            if q_type:
                used_question_types.append(q_type)
            print(f"\n✅ Successfully generated MCQ #{question_num}")
    
    # Summary
    print(f"\n{'#'*70}")
    print(f"# GENERATION COMPLETE")
    print(f"# ✅ Generated: {len(mcqs)}/{num_questions}")
    print(f"# ❌ Failed: {num_questions - len(mcqs)}")
    print(f"# 📊 Topics Used: {len(used_topics)}")
    print(f"{'#'*70}\n")
    
    return mcqs

# ===== CASE SCENARIO GENERATION =====

def get_llm_for_case_scenario(subject):
    """LLM for case scenario — uses same per-category model as MCQ, but higher token cap."""
    subject_key = normalize_subject_key(subject)
    config = SUBJECT_CONFIG.get(subject_key, SUBJECT_CONFIG["business_economics"])
    is_conceptual = subject_key in _CONCEPTUAL_SUBJECTS
    if is_conceptual:
        model = os.getenv("LLM_MODEL") or os.getenv("LLM_MODEL_CONCEPTUAL", "gpt-4.1-mini")
    else:
        model = os.getenv("LLM_MODEL") or os.getenv("LLM_MODEL_NUMERICAL", "gpt-4.1")
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=model,
        temperature=config["temperature"],
        max_tokens=CASE_SCENARIO_MAX_TOKENS,
        timeout=180
    )
    config = {**config, "model": model}
    return llm, config


def parse_case_scenario_response(response_text):
    """Parse the LLM's case scenario JSON (narrative + questions list)."""
    response_text = response_text.strip()

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(response_text[start:end])
            except Exception:
                return None
    return None


def validate_case_scenario(data):
    """Validate that the parsed case scenario has all required fields."""
    required_top = ["case_scenario_title", "case_scenario_narrative", "questions"]
    for field in required_top:
        if field not in data:
            return False, f"Missing top-level field: {field}"

    if not isinstance(data["questions"], list) or len(data["questions"]) < 1:
        return False, "questions must be a non-empty list"

    for i, q in enumerate(data["questions"]):
        missing = [k for k in ("question", "options", "correct_answer", "explanation") if k not in q]
        if missing:
            return False, f"Question {i + 1} missing: {missing}"
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            return False, f"Question {i + 1} must have exactly 4 options"

    return True, "valid"


def generate_case_scenario_mcqs(level, subject, chapter_name,
                                difficulty="very-hard", num_questions=4, unit_name=None):
    """
    Generate an ICAI-standard case scenario with multiple related MCQs.

    The LLM produces ONE shared narrative + num_questions MCQs in a single call.

    Returns:
        dict  – { case_scenario_title, case_scenario_narrative, questions, metadata }
        None  – on failure
    """
    print(f"\n{'#'*70}")
    print(f"# ICAI CASE SCENARIO MCQ GENERATION")
    print(f"# Level: {level} | Subject: {subject.upper()}")
    print(f"# Chapter: {chapter_name}")
    if unit_name:
        print(f"# Unit: {unit_name}")
    print(f"# Difficulty: {difficulty.upper()} | Questions: {num_questions}")
    print(f"{'#'*70}\n")

    # ── 1. Fetch topics ──────────────────────────────────────────────────────
    print("📚 Step 1: Scanning topics in chapter...")
    topics_list = get_all_topics(level, subject, chapter_name, unit_name)
    if not topics_list:
        print("❌ No topics found")
        return None

    # ── 2. Select best topic ─────────────────────────────────────────────────
    selected_topic = select_best_topic_for_mcq(topics_list, prefer_complex=True)
    if not selected_topic:
        print("❌ Could not select a topic")
        return None

    # ── 3. Fetch chunks ──────────────────────────────────────────────────────
    print(f"\n📚 Step 2: Fetching content — topic: {selected_topic['name']}")
    context, metadata = fetch_topic_chunks_optimized(
        level, subject, chapter_name, unit_name, selected_topic["name"],
        context_tokens=_context_tokens_for_subject(normalize_subject_key(subject)),
    )
    if not context or metadata is None:
        print("❌ Could not fetch topic content")
        return None

    # ── 4. Build prompt ──────────────────────────────────────────────────────
    subject_context = get_subject_context(subject)
    norm_difficulty = difficulty.lower().replace("-", "_")

    print(f"\n📝 Step 3: Building ICAI case scenario prompt...")
    prompt = get_case_scenario_prompt(
        norm_difficulty,
        context,
        metadata.get("chapter_number", 1),
        metadata.get("chapter_name", chapter_name),
        metadata.get("unit_number", 1),
        metadata.get("unit_name", unit_name or ""),
        subject_context,
        num_questions=num_questions,
        topic_name=metadata.get("topic_name", selected_topic["name"])
    )

    # ── 5. Call LLM ──────────────────────────────────────────────────────────
    llm, config = get_llm_for_case_scenario(subject)
    print(f"\n🤖 LLM: {config['model']} | temp={config['temperature']} | max_tokens={CASE_SCENARIO_MAX_TOKENS}")
    print(f"\n⏳ Step 4: Generating case scenario (may take 60–120 s)...")

    try:
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)

        usage = extract_token_usage(response)
        if usage:
            print(f"📊 Token usage: input={usage.get('input')}, output={usage.get('output')}, total={usage.get('total')}")
    except Exception as e:
        err_type = _classify_llm_error(str(e))
        if err_type == "quota":
            print(f"❌ OpenAI quota exhausted — add credits at platform.openai.com/account/billing")
        elif err_type == "rate_limit":
            print(f"⏳ Rate limited — case scenario generation aborted (no retry for single-call)")
        else:
            print(f"❌ LLM Error: {e}")
        return None

    # ── 6. Parse & validate ───────────────────────────────────────────────────
    print(f"\n📝 Step 5: Parsing response...")
    case_data = parse_case_scenario_response(response_text)

    if not case_data:
        print("❌ Failed to parse case scenario response")
        print(f"   Response (first 500 chars): {response_text[:500]}")
        return None

    is_valid, reason = validate_case_scenario(case_data)
    if not is_valid:
        print(f"❌ Validation failed: {reason}")
        return None

    # ── 7. Normalize options and auto-correct answers in each question ───────────
    print("🔤 Step 6: Normalizing answer options and cross-validating answers...")
    normalized_questions = []
    for i, q in enumerate(case_data["questions"]):
        q["question_number"] = i + 1
        q = strip_embedded_options(q)
        q = try_autocorrect_answer(q)          # fix explanation vs letter mismatch
        q = normalize_options_order(q)
        for key, value in metadata.items():
            if key not in q:
                q[key] = value
        normalized_questions.append(q)

    case_data["questions"] = normalized_questions
    case_data["metadata"] = {
        "level": level,
        "subject": subject,
        "chapter_name": chapter_name,
        "unit_name": unit_name,
        "topic_name": selected_topic["name"],
        "difficulty": difficulty,
        "total_questions": len(normalized_questions)
    }

    print(f"\n✅ Case Scenario Generated Successfully!")
    print(f"   Title     : {case_data.get('case_scenario_title', 'N/A')}")
    print(f"   Questions : {len(normalized_questions)}")

    return case_data


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
