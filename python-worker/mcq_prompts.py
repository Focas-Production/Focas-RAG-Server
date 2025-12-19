"""
mcq_prompts.py - ENHANCED CA EXAM MCQ GENERATION
Production-grade: Generates extremely challenging MCQs for CA students
Includes VERY-HARD difficulty level with complex scenarios
"""

import random

MAX_QUESTIONS = 50
MAX_TOKENS = 3000  # Increased for complex MCQ generation

SYSTEM_PROMPT = """You are an elite ICAI exam question setter with 30+ years experience setting CA Final papers.
Generate EXTREMELY CHALLENGING, AUTHENTIC CA exam MCQs that test deep expertise.

CRITICAL REQUIREMENTS FOR PRODUCTION:
1. Based ONLY on provided content - NO external knowledge
2. Multiple concepts integrated (not single-topic)
3. Realistic Indian business scenarios with specific numbers
4. Requires CRITICAL THINKING and APPLICATION, not just recall
5. Include numerical calculations, policy implications, or complex judgment
6. Each wrong answer must be plausible (common misconception)
7. Suitable for CA students preparing for actual exams

QUALITY STANDARDS:
- Provide 4 DISTINCT, PLAUSIBLE options
- Correct answer is NOT obvious
- Requires 2-5 minutes of careful analysis
- Do NOT indicate which is correct
- Randomize all options equally
- Test understanding of edge cases and exceptions"""

# ===== DIFFICULTY LEVEL DESCRIPTIONS =====

DIFFICULTY_DESCRIPTIONS = {
    "easy": {
        "name": "EASY",
        "description": "Tests basic concept recall and simple application",
        "characteristics": [
            "Single concept",
            "Straightforward scenario",
            "0-1 calculation",
            "Direct textbook reference",
            "Answer is relatively obvious to those who studied"
        ]
    },
    "medium": {
        "name": "MEDIUM",
        "description": "Tests application of concepts with some analysis",
        "characteristics": [
            "2-3 concepts combined",
            "Real business scenario",
            "2-3 calculations or logical steps",
            "Requires understanding, not just recall",
            "Some judgment/interpretation needed"
        ]
    },
    "hard": {
        "name": "HARD",
        "description": "Tests deep understanding with complex scenarios",
        "characteristics": [
            "3-4 concepts integrated",
            "Complex Indian business scenario",
            "4-6 calculations or decision factors",
            "Requires expert judgment and analysis",
            "Tests exception cases and edge scenarios",
            "Combines theory with practical implications"
        ]
    },
    "very_hard": {
        "name": "VERY-HARD",
        "description": "Tests mastery level understanding - CA Final exam standard",
        "characteristics": [
            "4-5+ concepts deeply integrated",
            "Highly realistic, complex Indian business scenario with multiple variables",
            "6-10+ calculation steps or decision factors",
            "Requires EXPERT judgment, critical analysis, and synthesis",
            "Tests understanding of exceptions, boundary cases, policy nuances",
            "Combines theory, practice, policy, and ethical considerations",
            "Question that senior CAs debate in practice",
            "Separates good CA students from excellent ones",
            "Requires knowing what most candidates DON'T know"
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
        return """VERY-HARD LEVEL - CA FINAL EXAMINATION STANDARD:
- This question SEPARATES good CAs from EXCELLENT CAs
- 4-5+ interconnected concepts from the content
- Complex, realistic Indian business scenario (NOT simplified)
- 6-10+ calculation steps or decision factors required
- Requires EXPERT-level judgment and critical analysis
- Tests understanding of edge cases, exceptions, policy nuances
- Each wrong answer must be a common mistake made by 80% of candidates
- Question that practicing CAs would debate in technical forums
- Solution requires deep synthesis of multiple principles
- Include specific numerical examples from Indian context
- NO generic/theoretical answers - practical expertise needed"""
    
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
    """Generate POWERFUL subject-specific, topic-aware prompt with extreme quality standards"""
    
    difficulty_lower = difficulty.lower()
    subject = subject_context.get("name", "").lower().replace(" ", "_")
    
    # Get subject config
    config = SUBJECT_CONFIGURATIONS.get(subject, SUBJECT_CONFIGURATIONS["business_economics"])
    
    # Select question type appropriate for difficulty
    question_type = select_question_type(subject, difficulty_lower, chapter_name=chapter_name)
    
    # Get template
    template = config["question_templates"].get(question_type, "Default: [{scenario}]. Correct answer is?")
    
    # Get examples
    examples = config["examples"]
    
    # Get difficulty description
    diff_info = DIFFICULTY_DESCRIPTIONS.get(difficulty_lower, DIFFICULTY_DESCRIPTIONS["hard"])
    
    # Build POWERFUL prompt
    prompt = f"""GENERATE PRODUCTION-GRADE CA EXAM MCQ - {diff_info['name']} LEVEL
{'='*80}

CONTENT TO BASE QUESTION ON:
Chapter: {chapter_number} - {chapter_name}
Unit: {unit_number} - {unit_name}
Topic: {topic_name}
Difficulty Level: {diff_info['name']}

DIFFICULTY LEVEL CHARACTERISTICS:
{chr(10).join('• ' + char for char in diff_info['characteristics'])}

CONTENT PROVIDED:
{context}

{'='*80}
QUESTION GENERATION REQUIREMENTS:
{'='*80}

1. DIFFICULTY CALIBRATION FOR {diff_info['name']}:
{get_difficulty_instruction(difficulty_lower, subject)}

2. QUESTION QUALITY STANDARDS:
   ✓ Based ONLY on provided content - NO external knowledge
   ✓ Integrates {2 if difficulty_lower == 'easy' else 3 if difficulty_lower == 'medium' else 4 if difficulty_lower == 'hard' else 5}+ concepts from content
   ✓ Realistic Indian business scenario with SPECIFIC numbers/amounts
   ✓ Requires {'recall' if difficulty_lower == 'easy' else 'understanding + application' if difficulty_lower == 'medium' else 'deep analysis + synthesis' if difficulty_lower == 'hard' else 'expert judgment + critical thinking + synthesis'}
   ✓ Test takers need {'basic knowledge' if difficulty_lower == 'easy' else 'intermediate understanding' if difficulty_lower == 'medium' else 'advanced expertise' if difficulty_lower == 'hard' else '5+ years professional experience'}
   ✓ Each wrong answer is a PLAUSIBLE misconception
   ✓ Correct answer is NOT obvious (requires {'0-1' if difficulty_lower == 'easy' else '2-3' if difficulty_lower == 'medium' else '4-6' if difficulty_lower == 'hard' else '6-10+'}+ minutes analysis)

3. SCENARIO CONSTRUCTION ({diff_info['name']}):
   • Use these real Indian companies/contexts: {', '.join(random.sample(examples.get('companies', ['Company A', 'Company B', 'Company C']), min(3, len(examples.get('companies', [])))))}
   • Include specific amounts: {', '.join(random.sample(examples.get('price_ranges', ['Rs. 100', 'Rs. 1000']), min(3, len(examples.get('price_ranges', [])))))}
   • Market context: {', '.join(random.sample(examples.get('markets', ['Market A', 'Market B']), min(2, len(examples.get('markets', [])))))}
   • Realistic timeframe and business constraints
   {'• Include policy implications or regulatory considerations' if difficulty_lower in ['hard', 'very_hard'] else ''}

4. QUESTION TEMPLATE TO FOLLOW:
   {template}

5. OPTION DESIGN:
   • A: {['Obviously wrong' if difficulty_lower == 'easy' else 'Related but incorrect concept' if difficulty_lower == 'medium' else 'Common expert misconception' if difficulty_lower == 'hard' else 'Seems correct but misses critical nuance']}
   • B: {['Directly wrong' if difficulty_lower == 'easy' else 'Partially correct concept' if difficulty_lower == 'medium' else 'Correct on surface but wrong logic' if difficulty_lower == 'hard' else 'Correct calculation but wrong interpretation']}
   • C: {['Clearly incorrect' if difficulty_lower == 'easy' else 'Wrong interpretation of concept' if difficulty_lower == 'medium' else 'Correct concept but wrong application' if difficulty_lower == 'hard' else '70% correct - MOST candidates choose this']}
   • D: {['CORRECT ANSWER - requires analysis' if difficulty_lower == 'easy' else 'CORRECT ANSWER - requires application' if difficulty_lower == 'medium' else 'CORRECT ANSWER - requires synthesis' if difficulty_lower == 'hard' else 'CORRECT ANSWER - only experts see this']}

{'CRITICAL FOR VERY-HARD:' if difficulty_lower == 'very_hard' else ''}
{'- Question should appear on CA Final papers' if difficulty_lower == 'very_hard' else ''}
{'- Separates 95% of candidates from top 5%' if difficulty_lower == 'very_hard' else ''}
{'- Requires knowing what 90% of CAs DONT know' if difficulty_lower == 'very_hard' else ''}
{'- Include edge case or policy nuance' if difficulty_lower == 'very_hard' else ''}

{'='*80}
RESPONSE FORMAT - JSON ONLY (NO MARKDOWN):
{{
  "chapter_number": {chapter_number},
  "chapter_name": "{chapter_name}",
  "unit_number": {unit_number},
  "unit_name": "{unit_name}",
  "topic_name": "{topic_name}",
  "difficulty": "{difficulty}",
  "question_type": "{question_type}",
  "question": "SPECIFIC, DETAILED question with numbers, scenario, and decision framework [{diff_info['name']} LEVEL]",
  "options": ["OPTION A: [specific amount/scenario]", "OPTION B: [calculation with values]", "OPTION C: [plausible misconception]", "OPTION D: [CORRECT - requires synthesis]"],
  "correct_answer": "[A/B/C/D]",
  "explanation": "DETAILED step-by-step solution: 
     1. [Identify key concepts from content]
     2. [Apply relevant principles]
     3. [Perform calculations/analysis]
     4. [Explain why each wrong answer is incorrect - typical student mistakes]
     5. [Conclusion with policy/practical implications]",
  "difficulty_justification": "Why this is {diff_info['name']} level: [Explain the complexity factors]",
  "keywords_from_content": ["keyword1", "keyword2", "keyword3"]
}}

{'='*80}
NOW GENERATE - Create an EXCEPTIONAL {diff_info['name']} level MCQ!
{'='*80}"""

    return prompt

def get_system_prompt():
    """Get enhanced system prompt"""
    return SYSTEM_PROMPT

def randomize_correct_answer(mcq):
    """
    Randomize correct answer position and options.

    Behaviour:
    - Uses the correct answer coming from the LLM (mcq["correct_answer"])
    - Correct option can end up in A, B, C, or D (pure random)
    - Options are shuffled randomly
    - Updates mcq["correct_answer"] to the new letter (A/B/C/D)
    - If model didn't set correct_answer properly, assumes last option (D) is correct
      (consistent with your prompt where D is the correct one)
    """
    if "options" not in mcq or len(mcq["options"]) != 4:
        return mcq

    options = mcq["options"].copy()
    raw_correct = str(mcq.get("correct_answer", "")).strip().upper()

    correct_idx = None

    # 1️⃣ Case 1: model returns clean "A"/"B"/"C"/"D"
    if raw_correct in {"A", "B", "C", "D"}:
        correct_idx = ord(raw_correct) - ord("A")

    # 2️⃣ Case 2: "OPTION A", "Option B", etc.
    elif raw_correct.startswith("OPTION "):
        last_part = raw_correct.split()[-1]
        if last_part in {"A", "B", "C", "D"}:
            correct_idx = ord(last_part) - ord("A")

    # 3️⃣ Case 3: model might have returned the actual option text as correct_answer
    if correct_idx is None and raw_correct:
        for i, opt in enumerate(options):
            if raw_correct == str(opt).strip().upper():
                correct_idx = i
                break

    # 4️⃣ Fallback: assume last option (D) is correct as per your template
    if correct_idx is None or not (0 <= correct_idx < 4):
        correct_idx = 3  # index 3 = D

    # Attach a flag to each option indicating whether it's the correct one
    options_with_flag = []
    for i, opt_text in enumerate(options):
        is_correct = (i == correct_idx)
        options_with_flag.append((opt_text, is_correct))

    # Shuffle options WITH their flags
    random.shuffle(options_with_flag)

    # Rebuild options list and find new correct index
    new_options = []
    new_correct_idx = None
    for idx, (opt_text, is_correct) in enumerate(options_with_flag):
        new_options.append(opt_text)
        if is_correct:
            new_correct_idx = idx

    # Safety fallback (should not happen, but just in case)
    if new_correct_idx is None:
        new_correct_idx = 0

    # Map new correct index back to letter A/B/C/D
    new_correct_letter = chr(ord("A") + new_correct_idx)

    mcq["options"] = new_options
    mcq["correct_answer"] = new_correct_letter

    return mcq

    """Randomize correct answer position"""
    if "options" not in mcq or len(mcq["options"]) != 4:
        return mcq
    
    # Find correct answer first
    correct_answer = mcq.get("correct_answer", "D")
    options = mcq["options"].copy()
    
    # Shuffle options
    random.shuffle(options)
    
    # Find new position of correct answer
    # Assuming first option in original list is correct
    correct_option = options[0] if len(options) > 0 else ""
    
    # Create mapping for new position
    if len(options) == 4:
        for i, opt in enumerate(options):
            if opt == correct_option:
                correct_letter = chr(65 + i)
                break
        else:
            correct_letter = "A"
    else:
        correct_letter = "A"
    
    mcq["options"] = options
    mcq["correct_answer"] = correct_letter
    
    return mcq