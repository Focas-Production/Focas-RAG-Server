"""
mcq_prompts.py - ENHANCED CA EXAM MCQ GENERATION
Production-grade: Generates extremely challenging MCQs for CA students
Includes VERY-HARD difficulty level with complex scenarios
"""

import random
import re

MAX_QUESTIONS = 50
SYSTEM_PROMPT = """You are an ICAI exam question setter.
Generate authentic, high-quality CA MCQs.
Use ONLY provided content. No external facts.
Use realistic Indian business context with rupee amounts.
Integrate multiple concepts, require analysis, and include plausible distractors.
Return JSON only."""

# ===== DIFFICULTY LEVEL DESCRIPTIONS =====

DIFFICULTY_DESCRIPTIONS = {
    "easy": {
        "name": "EASY",
        "description": "Tests basic concept recall and simple application",
        "characteristics": [
            "Single concept",
            "Simple scenario",
            "0-1 calculation"
        ]
    },
    "medium": {
        "name": "MEDIUM",
        "description": "Tests application of concepts with some analysis",
        "characteristics": [
            "2-3 concepts combined",
            "Realistic scenario",
            "2-3 calculation steps"
        ]
    },
    "hard": {
        "name": "HARD",
        "description": "Tests deep understanding with complex scenarios",
        "characteristics": [
            "3-4 concepts integrated",
            "Complex scenario",
            "4-6 calculation steps"
        ]
    },
    "very_hard": {
        "name": "VERY-HARD",
        "description": "Tests mastery level understanding - CA Final exam standard",
        "characteristics": [
            "4-5+ concepts integrated",
            "Highly complex scenario",
            "6-10+ decision factors"
        ]
    }
}

# ===== SUBJECT CONFIGURATIONS - ENHANCED =====

SUBJECT_CONFIGURATIONS = {
    "business_economics": {
        "name": "Business Economics",
        "question_types": {
            "easy": [
                "demand_supply_definition",
                "elasticity_concept",
                "market_equilibrium_basic",
                "consumer_behavior",
                "cost_concept",
                "price_effect",
                "production_decision_basic"
            ],
            "medium": [
                "elasticity_calculation",
                "market_analysis_scenario",
                "consumer_surplus_calculation",
                "equilibrium_shift",
                "welfare_analysis",
                "market_structure_identification",
                "pricing_strategy"
            ],
            "hard": [
                "complex_equilibrium",
                "elasticity_revenue_relationship",
                "welfare_loss_calculation",
                "multi_factor_production",
                "market_dynamics_analysis",
                "policy_impact_assessment",
                "consumer_producer_surplus_trade"
            ],
            "very_hard": [
                "multi_market_equilibrium_with_policy",
                "complex_cost_structure_analysis",
                "welfare_optimization_under_constraints",
                "market_failure_policy_trade_offs",
                "production_efficiency_frontier",
                "comparative_advantage_with_externalities",
                "pricing_under_oligopoly_with_regulations"
            ]
        },
        "question_templates": {
            "demand_supply_definition": "As per content, [{concept}] means?",
            "elasticity_concept": "Demand for [{product}] has [{type}] elasticity because?",
            "market_equilibrium_basic": "At equilibrium price Rs. [{price}], quantity is [{quantity}]. Why?",
            "consumer_behavior": "[{consumer_scenario}]. Consumer will [{action}] because?",
            "cost_concept": "[{company}] has fixed cost Rs. [{amount}]. Variable cost is?",
            "price_effect": "When price [{increases/decreases}] by [{percent}]%, [{effect}] happens because?",
            "production_decision_basic": "[{cost_scenario}]. Company should [{decision}] because?",
            "elasticity_calculation": "Price [{change}]%, Quantity [{change}]%. Elasticity is? Calculate.",
            "market_analysis_scenario": "[{market_data}]. At price Rs. [{price}], shortage is?",
            "consumer_surplus_calculation": "Consumer willing Rs. [{max}], market price Rs. [{actual}]. Surplus is?",
            "equilibrium_shift": "[{shift_scenario}]. New equilibrium [{effect}]?",
            "welfare_analysis": "[{price_control}]. Consumer surplus [{change}]%, Producer surplus [{change}]%. Net welfare?",
            "market_structure_identification": "[{market_characteristics}]. Market structure is [{type}]?",
            "pricing_strategy": "[{demand_data}]. Optimal price considering [{factors}] is?",
            "complex_equilibrium": "[{complex_scenario}]. New equilibrium price and quantity considering [{multiple_factors}]?",
            "elasticity_revenue_relationship": "[{elasticity_data}]. When price changes [{percent}]%, revenue [{direction}] by [{amount}]?",
            "welfare_loss_calculation": "[{deadweight_loss_scenario}] with externalities. Total welfare loss?",
            "multi_factor_production": "[{production_constraints}]. Optimal [{decision}] considering all factors, including [{hidden_factor}]?",
            "market_dynamics_analysis": "[{multiple_forces}] occurring simultaneously. Market outcome will [{outcome}]?",
            "policy_impact_assessment": "[{policy}] implemented. Combined impact on [{stakeholders}] over [{timeframe}]?",
            "consumer_producer_surplus_trade": "[{trade_scenario}] with policy implications. Net effect on [{metric}]?",
            "multi_market_equilibrium_with_policy": "[{scenario_with_multiple_markets_and_policy}]. Considering [{concept1}], [{concept2}], and [{concept3}] simultaneously, equilibrium [{outcome}]?",
            "complex_cost_structure_analysis": "[{firm_with_complex_costs}] where AFC is Rs. [{afc}], VC is Rs. [{vc}], optimal output Rs. [{output}]. If [{condition}], new optimal output?",
            "welfare_optimization_under_constraints": "[{constrained_scenario}]. Maximize [{objective}] subject to [{constraints}]. Optimal solution considers [{nuance}]?",
            "market_failure_policy_trade_offs": "[{market_failure_scenario}]. Policy [{policy}] creates [{trade_off}]. Net effect on efficiency and equity?",
            "production_efficiency_frontier": "[{two_product_scenario}] in economy. Production possibility frontier shows [{implication}]? If [{shock}], PPC shifts?",
            "comparative_advantage_with_externalities": "[{trade_scenario}] between regions. Comparative advantage in [{product}] but negative externality of Rs. [{amount}]. Should trade occur?"
        },
        "examples": {
            "products": ["Premium Rice", "Mobile phones", "Electric Automobiles", "Insurance Products", "E-commerce Services", "Pharmaceuticals", "Steel", "Cement"],
            "markets": ["Agricultural", "Technology", "Financial", "Manufacturing", "E-commerce", "Energy", "Healthcare"],
            "price_ranges": ["Rs. 100", "Rs. 500", "Rs. 5,000", "Rs. 50,000", "Rs. 1,00,000"],
            "companies": ["TCS Ltd", "Reliance Industries", "HDFC Bank", "Hero MotoCorp", "Infosys", "Bajaj Auto", "ICICI Bank"]
        }
    },

    "accounting": {
        "name": "Financial Accounting",
        "question_types": {
            "easy": [
                "journal_entry_basic",
                "account_classification",
                "debit_credit_rule",
                "asset_definition",
                "revenue_recognition_basic"
            ],
            "medium": [
                "multi_entry_transaction",
                "valuation_application",
                "accrual_timing",
                "standard_application",
                "financial_impact_calculation"
            ],
            "hard": [
                "consolidation_complex",
                "multi_standard_scenario",
                "impairment_calculation",
                "deferred_tax_complex",
                "business_combination"
            ],
            "very_hard": [
                "multi_level_consolidation_with_goodwill",
                "complex_fair_value_measurement",
                "ind_as_combination_impact",
                "segment_reporting_with_ifrs_transition",
                "deferred_tax_with_uncertain_positions"
            ]
        }
    },

    "auditing": {
        "name": "Auditing and Assurance",
        "question_types": {
            "easy": [
                "audit_evidence_type",
                "internal_control_basic",
                "sa_standard_basic",
                "audit_risk_definition",
                "materiality_concept"
            ],
            "medium": [
                "procedure_selection",
                "evidence_evaluation",
                "risk_assessment_application",
                "control_testing",
                "materiality_application"
            ],
            "hard": [
                "complex_risk_scenario",
                "evidence_credibility",
                "fraud_risk_indicators",
                "group_audit",
                "audit_conclusion"
            ],
            "very_hard": [
                "complex_group_with_fraud_indicators",
                "going_concern_with_subsequent_events",
                "related_party_transaction_detection",
                "cyber_risk_and_audit_procedures",
                "crypto_transaction_substantive_procedures"
            ]
        }
    },

    "taxation": {
        "name": "Income Taxation",
        "question_types": {
            "easy": [
                "income_head_classification",
                "exemption_basic",
                "deduction_basic",
                "gross_income_concept",
                "assessment_status"
            ],
            "medium": [
                "multi_head_income",
                "deduction_calculation",
                "exemption_application",
                "loss_adjustment",
                "tax_planning_basic"
            ],
            "hard": [
                "complex_income_computation",
                "loss_carry_forward",
                "deduction_limits",
                "exemption_conditions",
                "residential_status_implication"
            ],
            "very_hard": [
                "multi_jurisdiction_with_dta",
                "transfer_pricing_documentation",
                "beneficial_ownership_determination",
                "tax_avoidance_gaar_application",
                "cryptocurrency_taxation_implications"
            ]
        }
    }
}

# ===== DYNAMIC PROMPT GENERATION =====

def get_difficulty_instruction(difficulty, subject):
    """Get difficulty-specific detailed instructions"""
    difficulty_lower = difficulty.lower()
    
    if difficulty_lower == "very_hard":
        return """VERY-HARD LEVEL - CA FINAL STANDARD:
- 4-5+ interconnected concepts from the content
- Complex Indian business scenario with multiple variables
- 6-10+ decision factors or calculations
- Requires expert judgment and edge-case reasoning
- Distractors are common expert-level misconceptions"""
    
    instructions = {
        "easy": "Tests BASIC concept understanding. Single concept. Simple scenario. 1-2 calculations if any.",
        "medium": "Tests APPLICATION with analysis. 2-3 calculations. Real scenario. Some judgment needed.",
        "hard": "Tests DEEP understanding. 4-6 calculations/factors. Complex scenario. Expert judgment needed."
    }
    return instructions.get(difficulty_lower, instructions["easy"])

def select_question_type(subject, difficulty, previous_types=None, chapter_name=None):
    """Intelligently select question type to ensure variety and appropriate difficulty"""
    if previous_types is None:
        previous_types = []
    
    config = SUBJECT_CONFIGURATIONS.get(subject, SUBJECT_CONFIGURATIONS["business_economics"])
    available_types = config["question_types"].get(difficulty.lower(), [])
    
    if not available_types:
        available_types = config["question_types"].get("hard", [])
    
    # Remove previously used types
    available_types = [t for t in available_types if t not in previous_types]
    
    # If all used, reset
    if not available_types:
        available_types = config["question_types"].get(difficulty.lower(), [])
    
    # Select randomly from available
    selected = random.choice(available_types) if available_types else "definition"
    return selected

def get_prompt(difficulty, context, chapter_number, chapter_name, unit_number, unit_name, subject_context, question_count=1, topic_name=""):
    """Generate compact, high-precision prompt for MCQ generation"""
    
    difficulty_lower = difficulty.lower()
    subject = subject_context.get("name", "").lower().replace(" ", "_")
    
    # Get subject config
    config = SUBJECT_CONFIGURATIONS.get(subject, SUBJECT_CONFIGURATIONS["business_economics"])
    
    # Select question type appropriate for difficulty
    question_type = select_question_type(subject, difficulty_lower, chapter_name=chapter_name)
    
    # Get template
    template = config["question_templates"].get(question_type, "Default: [{scenario}]. Correct answer is?")
    
    # Get difficulty description
    diff_info = DIFFICULTY_DESCRIPTIONS.get(difficulty_lower, DIFFICULTY_DESCRIPTIONS["hard"])
    
    prompt = f"""GENERATE CA EXAM MCQ - {diff_info['name']} LEVEL

CONTENT:
Chapter: {chapter_number} - {chapter_name}
Unit: {unit_number} - {unit_name}
Topic: {topic_name}

DIFFICULTY TARGET:
{get_difficulty_instruction(difficulty_lower, subject)}
Key traits: {', '.join(diff_info['characteristics'])}

SOURCE CONTENT (use only this):
{context}

REQUIREMENTS:
- Integrate multiple concepts from the content.
- Use a realistic Indian business scenario with specific rupee amounts.
- Include 4 plausible options labeled A-D.
- Correct answer not obvious; requires analysis.
- No external knowledge.
- Explanation: concise but complete (100-160 words).

QUESTION TEMPLATE:
{template}

RESPONSE JSON ONLY:
{{
  "difficulty": "{difficulty}",
  "question_type": "{question_type}",
  "question": "Detailed question with numbers and scenario",
  "options": ["A: ...", "B: ...", "C: ...", "D: ..."],
  "correct_answer": "A",
  "explanation": "Step-by-step reasoning and why others are wrong."
}}"""

    return prompt

def get_system_prompt():
    """Get enhanced system prompt"""
    return SYSTEM_PROMPT

def normalize_options_order(mcq):
    """
    Normalize options to A/B/C/D order and remove the "OPTION " prefix.
    Also ensures correct_answer is a clean letter.
    """
    if "options" not in mcq or len(mcq["options"]) != 4:
        return mcq

    label_pattern = re.compile(
        r"^\s*(?:OPTION\s+)?([A-D])\s*[\)\:\.\-]\s*(.+)$",
        re.IGNORECASE
    )

    options = mcq["options"]
    labeled = {}
    unlabeled = []

    for opt in options:
        text = str(opt).strip()
        match = label_pattern.match(text)
        if match:
            label = match.group(1).upper()
            body = match.group(2).strip()
            labeled[label] = body
        else:
            unlabeled.append(text)

    ordered = []
    for label in ["A", "B", "C", "D"]:
        if label in labeled:
            body = labeled[label]
        else:
            body = unlabeled.pop(0) if unlabeled else ""
        ordered.append(f"{label}: {body}".strip())

    mcq["options"] = ordered

    raw_correct = str(mcq.get("correct_answer", "")).strip().upper()
    if raw_correct.startswith("OPTION "):
        raw_correct = raw_correct.replace("OPTION ", "", 1).strip()

    if raw_correct in {"A", "B", "C", "D"}:
        mcq["correct_answer"] = raw_correct
        return mcq

    match = re.match(r"^\s*([A-D])\s*[\)\:\.\-]?", raw_correct)
    if match:
        mcq["correct_answer"] = match.group(1)
        return mcq

    cleaned_correct = raw_correct
    for i, opt in enumerate(ordered):
        opt_body = re.sub(r"^[A-D]\s*[\)\:\.\-]\s*", "", opt, flags=re.IGNORECASE).strip().upper()
        if cleaned_correct == opt_body:
            mcq["correct_answer"] = chr(ord("A") + i)
            return mcq

    mcq["correct_answer"] = "A"
    return mcq
