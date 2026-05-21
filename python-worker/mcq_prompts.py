"""
mcq_prompts.py - ENHANCED CA EXAM MCQ GENERATION
Production-grade: Generates extremely challenging MCQs for CA students
Includes VERY-HARD difficulty level with complex scenarios
"""

import random
import re

MAX_QUESTIONS = 50

# ===== SUBJECT DB NAME → INTERNAL CONFIG KEY MAPPING =====
# Keys are EXACT MongoDB subject names; values are internal config keys.

SUBJECT_DB_TO_CONFIG_KEY = {
    # Foundation
    "Business Economics":                               "business_economics",
    "Business law":                                     "business_law",
    "accounting":                                       "accounting_foundation",
    # Intermediate
    "Advanced accounts":                                "advanced_accounts",
    "Auditing and Ethics":                              "auditing_ethics",
    "Corporate and other laws":                         "corporate_laws",
    "Cost and Management Accounting":                   "cost_management_accounting",
    "FM":                                               "financial_management",
    "IDT":                                              "indirect_tax",
    "IT":                                               "income_tax",
    "SM":                                               "strategic_management",
    # Final
    "Advanced Financial Management":                    "advanced_financial_management",
    "Advanced auditing,Assurance and Professional ethics": "advanced_auditing",
    "Direct Tax Laws & International Taxation":         "direct_tax_international",
    "Financial Reporting":                              "financial_reporting",
}


def normalize_subject_key(subject: str) -> str:
    """Return the internal config key for any MongoDB subject name."""
    if subject in SUBJECT_DB_TO_CONFIG_KEY:
        return SUBJECT_DB_TO_CONFIG_KEY[subject]
    # Case-insensitive fallback
    lower = subject.lower()
    for db_name, key in SUBJECT_DB_TO_CONFIG_KEY.items():
        if db_name.lower() == lower:
            return key
    # Last-resort: snake-case the name (preserves legacy behaviour)
    return lower.replace(" ", "_")


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
    },

    "law": {
        "name": "Business Law",
        "question_types": {
            "easy": [
                "act_definition",
                "statutory_provision_basic",
                "compliance_requirement_basic",
                "legal_term_identification",
                "party_rights_basic"
            ],
            "medium": [
                "provision_application",
                "compliance_deadline_calculation",
                "legal_consequence_scenario",
                "contract_validity_analysis",
                "statutory_filing_requirement"
            ],
            "hard": [
                "multi_act_scenario",
                "breach_consequence_analysis",
                "corporate_governance_compliance",
                "legal_remedy_determination",
                "cross_provision_application"
            ],
            "very_hard": [
                "complex_multi_act_compliance",
                "corporate_restructuring_legal_impact",
                "fraud_legal_liability_analysis",
                "cross_border_legal_jurisdiction",
                "statutory_exception_edge_case"
            ]
        }
    },

    "cost_accounting": {
        "name": "Cost Accounting",
        "question_types": {
            "easy": [
                "cost_classification_basic",
                "cost_concept_definition",
                "overhead_absorption_basic",
                "cost_sheet_element",
                "costing_method_identification"
            ],
            "medium": [
                "cost_sheet_calculation",
                "variance_analysis_basic",
                "overhead_recovery_rate",
                "marginal_costing_application",
                "process_costing_basic"
            ],
            "hard": [
                "complex_variance_analysis",
                "make_or_buy_decision",
                "activity_based_costing_scenario",
                "joint_product_cost_allocation",
                "standard_costing_reconciliation"
            ],
            "very_hard": [
                "integrated_cost_profit_volume_analysis",
                "multi_product_optimisation_constraints",
                "transfer_pricing_cost_centre",
                "complex_process_loss_abnormal_gain",
                "budgetary_control_with_variances"
            ]
        }
    },

    # ── FOUNDATION ────────────────────────────────────────────────────────────

    "business_law": {
        "name": "Business Law",
        "question_types": {
            "easy": [
                "contract_definition",
                "act_section_basic",
                "legal_term_identification",
                "party_rights_basic",
                "statutory_provision_basic"
            ],
            "medium": [
                "contract_validity_analysis",
                "provision_application",
                "legal_consequence_scenario",
                "partnership_rights",
                "negotiable_instrument_basic"
            ],
            "hard": [
                "multi_provision_scenario",
                "breach_consequence_analysis",
                "agency_liability",
                "sale_of_goods_complex",
                "company_compliance_basic"
            ],
            "very_hard": [
                "complex_multi_act_compliance",
                "cross_provision_application",
                "statutory_exception_edge_case",
                "corporate_restructuring_legal_impact",
                "fraud_legal_liability_analysis"
            ]
        }
    },

    "accounting_foundation": {
        "name": "Foundation Accounting",
        "question_types": {
            "easy": [
                "journal_entry_basic",
                "account_classification",
                "debit_credit_rule",
                "asset_definition",
                "accounting_concept"
            ],
            "medium": [
                "multi_entry_transaction",
                "bank_reconciliation",
                "depreciation_calculation",
                "final_accounts_basic",
                "partnership_profit_sharing"
            ],
            "hard": [
                "final_accounts_with_adjustments",
                "partnership_admission_retirement",
                "company_accounts_shares",
                "incomplete_records",
                "not_for_profit_accounts"
            ],
            "very_hard": [
                "company_accounts_debentures_complex",
                "partnership_dissolution_complex",
                "final_accounts_manufacturing",
                "bills_of_exchange_complex",
                "partnership_llp_combined"
            ]
        }
    },

    # ── INTERMEDIATE ──────────────────────────────────────────────────────────

    "advanced_accounts": {
        "name": "Advanced Accounts (Intermediate)",
        "question_types": {
            "easy": [
                "accounting_standard_identification",
                "inventory_valuation_as2",
                "depreciation_as10",
                "revenue_recognition_as9",
                "lease_classification_as19"
            ],
            "medium": [
                "cash_flow_classification_as3",
                "segment_reporting_as17",
                "related_party_as18",
                "earnings_per_share_as20",
                "borrowing_costs_as16"
            ],
            "hard": [
                "consolidation_as21",
                "amalgamation_as14",
                "buyback_of_securities",
                "deferred_tax_as22",
                "branch_accounts_foreign"
            ],
            "very_hard": [
                "complex_consolidation_unrealized_profit",
                "internal_reconstruction_complex",
                "foreign_branch_translation",
                "amalgamation_pooling_vs_purchase",
                "multi_standard_complex_scenario"
            ]
        }
    },

    "auditing_ethics": {
        "name": "Auditing and Ethics (Intermediate)",
        "question_types": {
            "easy": [
                "audit_objective_basic",
                "audit_evidence_type",
                "internal_control_basic",
                "materiality_concept",
                "audit_documentation_basic"
            ],
            "medium": [
                "risk_assessment_application",
                "procedure_selection",
                "audit_report_modification",
                "internal_control_evaluation",
                "bank_audit_basic"
            ],
            "hard": [
                "fraud_risk_assessment",
                "going_concern_evaluation",
                "special_purpose_audit",
                "ethics_independence_threat",
                "audit_sampling_design"
            ],
            "very_hard": [
                "complex_fraud_detection_scenario",
                "multi_risk_audit_planning",
                "professional_ethics_dilemma",
                "audit_evidence_credibility_complex",
                "digital_audit_data_analytics"
            ]
        }
    },

    "corporate_laws": {
        "name": "Corporate and Other Laws (Intermediate)",
        "question_types": {
            "easy": [
                "companies_act_definition",
                "statutory_provision_basic",
                "director_appointment",
                "shareholder_rights_basic",
                "company_types"
            ],
            "medium": [
                "share_capital_compliance",
                "board_meeting_procedure",
                "charge_registration",
                "dividend_declaration_rules",
                "fema_basic_provision"
            ],
            "hard": [
                "corporate_governance_scenario",
                "multi_act_compliance",
                "legal_consequence_analysis",
                "llp_provisions",
                "companies_act_default_penalty"
            ],
            "very_hard": [
                "complex_corporate_restructuring",
                "cross_border_legal_compliance",
                "fraud_corporate_liability",
                "statutory_exception_analysis",
                "multi_act_cross_provision"
            ]
        }
    },

    "cost_management_accounting": {
        "name": "Cost and Management Accounting (Intermediate)",
        "question_types": {
            "easy": [
                "cost_classification_basic",
                "cost_sheet_element",
                "overhead_concept",
                "costing_method_identification",
                "material_cost_basic"
            ],
            "medium": [
                "cost_sheet_calculation",
                "overhead_absorption_rate",
                "marginal_costing_contribution",
                "variance_analysis_basic",
                "process_costing_normal_loss"
            ],
            "hard": [
                "activity_based_costing",
                "make_or_buy_decision",
                "joint_product_cost_allocation",
                "standard_costing_reconciliation",
                "service_costing_complex"
            ],
            "very_hard": [
                "integrated_cvp_with_constraints",
                "multi_product_linear_programming",
                "transfer_pricing_cost_centre",
                "complex_process_abnormal_gain_loss",
                "budgetary_control_with_multiple_variances"
            ]
        }
    },

    "financial_management": {
        "name": "Financial Management (Intermediate)",
        "question_types": {
            "easy": [
                "time_value_concept",
                "capital_budgeting_basic",
                "cost_of_capital_basic",
                "working_capital_concept",
                "dividend_policy_basic"
            ],
            "medium": [
                "npv_irr_calculation",
                "wacc_calculation",
                "capital_structure_analysis",
                "working_capital_estimation",
                "cash_management_basic"
            ],
            "hard": [
                "complex_capital_budgeting_with_tax",
                "leverage_analysis",
                "dividend_impact_analysis",
                "receivables_management_eoq",
                "financing_decision_mm"
            ],
            "very_hard": [
                "multi_period_capital_budgeting_risk",
                "optimal_capital_structure_constraints",
                "integrated_working_capital_decision",
                "dividend_signaling_clientele_effect",
                "financial_distress_restructuring"
            ]
        }
    },

    "indirect_tax": {
        "name": "Indirect Tax — GST (Intermediate)",
        "question_types": {
            "easy": [
                "gst_concept_basic",
                "supply_definition",
                "registration_threshold",
                "tax_rate_classification",
                "invoice_basic"
            ],
            "medium": [
                "place_of_supply_determination",
                "itc_eligibility",
                "time_of_supply",
                "composite_mixed_supply",
                "reverse_charge_mechanism"
            ],
            "hard": [
                "complex_itc_computation",
                "cross_border_supply_gst",
                "gst_valuation_related_party",
                "refund_computation",
                "e_way_bill_compliance"
            ],
            "very_hard": [
                "multi_state_supply_chain_gst",
                "itc_reversal_apportionment",
                "anti_profiteering_compliance",
                "gst_returns_reconciliation_complex",
                "gst_audit_mismatch_resolution"
            ]
        }
    },

    "income_tax": {
        "name": "Income Tax (Intermediate)",
        "question_types": {
            "easy": [
                "income_head_classification",
                "exemption_basic",
                "deduction_basic",
                "residential_status_basic",
                "tds_rate_identification"
            ],
            "medium": [
                "salary_income_computation",
                "house_property_income",
                "business_profession_deduction",
                "capital_gain_computation",
                "deduction_80c_80d_calculation"
            ],
            "hard": [
                "complex_income_multi_head",
                "set_off_carry_forward_losses",
                "advance_tax_interest_computation",
                "tds_tcs_complex_scenario",
                "return_filing_assessment"
            ],
            "very_hard": [
                "multi_head_complex_computation",
                "business_restructuring_tax_impact",
                "capital_gain_indexation_slump_sale",
                "partnership_llp_tax_complex",
                "tax_audit_3cd_implications"
            ]
        }
    },

    "strategic_management": {
        "name": "Strategic Management (Intermediate)",
        "question_types": {
            "easy": [
                "strategy_definition",
                "swot_element_identification",
                "bcg_matrix_basic",
                "competitive_advantage_concept",
                "mission_vision_difference"
            ],
            "medium": [
                "porter_five_forces_analysis",
                "strategic_choice_evaluation",
                "value_chain_analysis",
                "strategic_implementation",
                "balanced_scorecard_basic"
            ],
            "hard": [
                "multi_strategy_scenario",
                "strategic_evaluation_criteria",
                "competitive_positioning_analysis",
                "strategic_alliance_assessment",
                "change_management_strategy"
            ],
            "very_hard": [
                "complex_strategic_decision_constraints",
                "industry_disruption_strategic_response",
                "multi_business_portfolio_strategy",
                "strategic_failure_turnaround_analysis",
                "global_strategy_local_adaptation"
            ]
        }
    },

    # ── FINAL ─────────────────────────────────────────────────────────────────

    "advanced_financial_management": {
        "name": "Advanced Financial Management (Final)",
        "question_types": {
            "easy": [
                "derivative_concept",
                "portfolio_return_basic",
                "forex_rate_concept",
                "mutual_fund_nav_basic",
                "securitization_concept"
            ],
            "medium": [
                "option_pricing_basic",
                "portfolio_beta_calculation",
                "forex_hedging_strategy",
                "futures_payoff_calculation",
                "business_valuation_basic"
            ],
            "hard": [
                "complex_derivatives_strategy",
                "portfolio_optimization_markowitz",
                "interest_rate_swap_valuation",
                "cross_currency_swap",
                "mergers_synergy_valuation"
            ],
            "very_hard": [
                "multi_leg_derivatives_complex",
                "capm_apt_portfolio_optimization",
                "structured_finance_securitization",
                "leveraged_buyout_analysis",
                "international_capital_budgeting_forex"
            ]
        }
    },

    "advanced_auditing": {
        "name": "Advanced Auditing and Assurance (Final)",
        "question_types": {
            "easy": [
                "sqc1_quality_control_basic",
                "assurance_engagement_type",
                "sa_standard_reference",
                "professional_ethics_basic",
                "audit_documentation_basic"
            ],
            "medium": [
                "risk_based_audit_planning",
                "group_audit_communication",
                "bank_audit_procedure",
                "forensic_audit_basic",
                "esg_assurance_basic"
            ],
            "hard": [
                "complex_group_audit_scenario",
                "fraud_investigation_procedure",
                "digital_audit_data_analytics",
                "prospective_financial_information",
                "internal_audit_effectiveness"
            ],
            "very_hard": [
                "complex_fraud_forensic_investigation",
                "multi_entity_group_audit_complex",
                "professional_ethics_complex_dilemma",
                "cyber_security_audit_complex",
                "sdg_esg_assurance_reporting_complex"
            ]
        }
    },

    "direct_tax_international": {
        "name": "Direct Tax Laws and International Taxation (Final)",
        "question_types": {
            "easy": [
                "income_tax_basic_concept",
                "residential_status_basic",
                "dtaa_concept",
                "transfer_pricing_concept",
                "beps_action_basic"
            ],
            "medium": [
                "business_income_complex_deduction",
                "capital_gain_complex_computation",
                "non_resident_taxation",
                "transfer_pricing_arm_length",
                "tax_treaty_application"
            ],
            "hard": [
                "assessment_procedure_complex",
                "dispute_resolution_mechanism",
                "tax_avoidance_gaar",
                "digital_taxation_implication",
                "advance_ruling_scenario"
            ],
            "very_hard": [
                "multi_jurisdiction_treaty_conflict",
                "complex_transfer_pricing_documentation",
                "beneficial_ownership_pe_determination",
                "cryptocurrency_international_taxation",
                "pillar_two_global_minimum_tax"
            ]
        }
    },

    "financial_reporting": {
        "name": "Financial Reporting — IND AS (Final)",
        "question_types": {
            "easy": [
                "ind_as_applicability",
                "fair_value_concept",
                "revenue_recognition_ind115_basic",
                "lease_classification_ind116",
                "financial_instrument_basic"
            ],
            "medium": [
                "ind_as_measurement",
                "financial_instrument_classification",
                "revenue_performance_obligation",
                "ind_as_consolidation_basic",
                "first_time_adoption_ind101"
            ],
            "hard": [
                "complex_fair_value_measurement",
                "financial_instruments_ecl",
                "business_combination_ind103",
                "hedge_accounting_designation",
                "segment_reporting_ind108"
            ],
            "very_hard": [
                "multi_level_consolidation_goodwill_impairment",
                "complex_financial_instruments_derivatives",
                "business_combination_contingent_consideration",
                "first_time_adoption_transition_adjustments",
                "cross_standard_interaction_complex"
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

    config_key = normalize_subject_key(subject)
    config = SUBJECT_CONFIGURATIONS.get(config_key, SUBJECT_CONFIGURATIONS["business_economics"])
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

def get_prompt(difficulty, context, chapter_number, chapter_name, unit_number, unit_name,
               subject_context, question_count=1, topic_name="", used_question_types=None):
    """Generate compact, high-precision prompt for MCQ generation"""
    if used_question_types is None:
        used_question_types = []

    difficulty_lower = difficulty.lower()
    subject_name = subject_context.get("name", "")
    subject = normalize_subject_key(subject_name)

    # Get subject config
    config = SUBJECT_CONFIGURATIONS.get(subject, SUBJECT_CONFIGURATIONS["business_economics"])

    # Select question type appropriate for difficulty, avoiding recently used types
    question_type = select_question_type(
        subject, difficulty_lower, previous_types=used_question_types, chapter_name=chapter_name
    )

    # Get template (only business_economics has question_templates; others use default)
    template = config.get("question_templates", {}).get(question_type, "[{scenario}]. What is the correct answer based on the content?")
    
    # Get difficulty description
    diff_info = DIFFICULTY_DESCRIPTIONS.get(difficulty_lower, DIFFICULTY_DESCRIPTIONS["hard"])
    
    avoid_repetition = (
        f"\n• AVOID REPETITION: Do NOT generate the same type of question as these "
        f"already-asked types: {used_question_types}. Test a different concept or angle."
        if used_question_types else ""
    )

    prompt = f"""GENERATE CA EXAM MCQ — {diff_info['name']} LEVEL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE CONTENT  ← ONLY material you may use
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subject : {subject_name}
Chapter : {chapter_number} — {chapter_name}
Unit    : {unit_number} — {unit_name}
Topic   : {topic_name}

{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE GUARD — MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• This question is for Subject: "{subject_name}", Chapter: "{chapter_name}".
• Generate questions ONLY about concepts explicitly present in the SOURCE CONTENT above.
• NEVER introduce GST / indirect tax questions when the subject is Accounting or Foundation Accounting.
• NEVER introduce topics from other chapters, other subjects, or your training knowledge
  that are not in the source content above.
• If the source content contains GST examples only as illustration inside an Accounting
  chapter, do NOT make the question about GST — make it about the accounting concept.{avoid_repetition}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIFFICULTY: {diff_info['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{get_difficulty_instruction(difficulty_lower, subject)}
Key traits: {', '.join(diff_info['characteristics'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION RULES — ALL MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Use a realistic Indian scenario with specific ₹ amounts where applicable.
• Ask for exactly ONE value or conclusion. NEVER ask "find X and Y" together.
• Every number, rate, and date needed to solve the question MUST appear in the
  question text. Never require students to assume unstated data.
• Each of the 4 options MUST represent a different numerical value or statement.
• Do NOT label any option or piece of data as "Red Herring" — distractors must
  appear natural; students must identify them without being told.
• The explanation MUST end with the sentence:
  "✅ Correct Answer: Option [X]" (where X is the letter A, B, C, or D).

QUESTION TEMPLATE HINT: {template}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANSWER CONSTRUCTION — FOLLOW EXACTLY IN THIS ORDER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — SOLVE THE PROBLEM FIRST:
   Perform every calculation step-by-step and arrive at the exact correct answer.
   Write it down: e.g., "Correct answer = ₹80,000"

STEP 2 — CREATE OPTIONS:
   • Pick one letter from A/B/C/D at random and assign your correct answer to it.
     (Vary the position — do NOT always put the correct answer in option A.)
   • Fill the other 3 letters with WRONG values.
     Wrong values must each represent a realistic mistake a student might make:
     wrong formula, off-by-one step, sign error, omitted adjustment, etc.
   • Every option value must be DIFFERENT from every other option value.

STEP 3 — SET correct_answer:
   Set "correct_answer" to the EXACT LETTER (A, B, C, or D) of the option from
   Step 2 that contains the correct value. Double-check it before writing JSON.

STEP 4 — VERIFY BEFORE WRITING JSON:
   (a) Read options[correct_answer]. Does it contain your Step 1 answer? If not — fix it.
   (b) Do all 4 option values differ? If any two are the same — replace the duplicate.
   (c) Is every number/rate needed to solve the question stated in the question text?
   (d) Does the explanation end with "✅ Correct Answer: Option [X]" where X = correct_answer?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE — Return ONLY valid JSON (no markdown, no extra text):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "difficulty": "{difficulty}",
  "question_type": "{question_type}",
  "question": "Full question text with ALL data needed to solve it.",
  "options": ["A: ...", "B: ...", "C: ...", "D: ..."],
  "correct_answer": "X",
  "explanation": "Step 1: ... Step 2: ... [full working] ... Option Y is wrong because ... Option Z is wrong because ... ✅ Correct Answer: Option X"
}}"""

    return prompt

def get_system_prompt():
    """Get enhanced system prompt"""
    return SYSTEM_PROMPT


# ===== CASE SCENARIO SUBJECT CONFIGURATIONS =====

CASE_SCENARIO_SUBJECT_CONFIGS = {
    "taxation": {
        "name": "Income Taxation",
        "style_guide": """
- Create a realistic individual taxpayer with an Indian name, age, and profession
- Include specific dates using F.Y. 2025-26 / A.Y. 2026-27 timeline
- Provide a formatted table of income/particulars with rupee amounts (₹)
- All computed amounts in distractors must represent common calculation mistakes
- Cover residential status, income heads, deductions, or tax computation
- Later questions may introduce "Assume for this question that..." variations
- Ensure all figures are internally consistent and arithmetically accurate
"""
    },
    "accounting": {
        "name": "Financial Accounting",
        "style_guide": """
- Create a realistic Indian company scenario (public/private limited)
- Include specific transaction dates, asset values, and financial figures in ₹
- Provide a table of transactions or financial data relevant to the topic
- Reference applicable Accounting Standards (AS) or IND AS
- Test accounting treatment, journal entries, or financial statement impact
- Later questions may modify one assumption to test a related concept
- Ensure all figures are internally consistent
"""
    },
    "auditing": {
        "name": "Auditing and Assurance",
        "style_guide": """
- Create a realistic audit engagement scenario with a named Indian company
- Include specific risk factors, financial data, and audit findings
- Provide details about internal controls, fraud indicators, or going concern issues
- Reference applicable Standards on Auditing (SA)
- Test audit procedures, evidence, reporting, and professional judgment
- Later questions may introduce modified facts to test a related SA provision
"""
    },
    "law": {
        "name": "Business Law",
        "style_guide": """
- Create a realistic scenario involving Indian parties (company, partners, or individuals)
- Include specific dates, statutory deadlines, and monetary values
- Provide a timeline or table of events leading to the legal question
- Reference applicable Acts (Companies Act 2013, Indian Contract Act, etc.)
- Test compliance requirements, legal consequences, and statutory provisions
- Later questions may modify a key fact to test a related legal provision
"""
    },
    "business_economics": {
        "name": "Business Economics",
        "style_guide": """
- Create a realistic Indian market or macroeconomic scenario
- Include specific data tables (demand schedule, cost structure, macro indicators)
- Use realistic Indian market context with rupee amounts
- Test economic analysis, decision-making, and policy evaluation
- Later questions may change one variable (e.g., price, cost, policy) to test impact
- Ensure all calculations in distractors represent plausible mistakes
"""
    },
    "cost_accounting": {
        "name": "Cost Accounting",
        "style_guide": """
- Create a realistic Indian manufacturing or service entity scenario
- Include a detailed cost data table with specific rupee amounts and units
- Cover costing methods, variance analysis, or management decisions
- Test cost computation, analysis, and operational decision-making
- Later questions may introduce additional cost components or decision alternatives
- Ensure all cost figures are internally consistent and arithmetically correct
"""
    },

    # ── FOUNDATION ────────────────────────────────────────────────────────────

    "business_law": {
        "name": "Business Law",
        "style_guide": """
- Create a realistic Indian contractual or statutory scenario with named parties
- Include specific dates, monetary values, and relevant provisions
- Reference applicable Acts (Indian Contract Act 1872, Sale of Goods Act 1930,
  Partnership Act 1932, LLP Act 2008, Companies Act 2013, NI Act 1881)
- Provide a timeline of events or a table of facts leading to the legal question
- Test legal validity, rights, obligations, and consequences
- Later questions may modify a key fact (e.g., notice period, consideration amount)
  to test a related provision
- All statutory references must be accurate and internally consistent
"""
    },

    "accounting_foundation": {
        "name": "Foundation Accounting",
        "style_guide": """
- Create a realistic sole proprietor, partnership, or company scenario in India
- Include specific transaction dates, amounts in ₹, and account names
- Provide a table of transactions, trial balance extract, or ledger data
- Cover journal entries, final accounts, depreciation, bank reconciliation,
  partnership accounts, or company accounts (shares/debentures)
- Test accounting treatment, computation, and financial statement presentation
- Later questions may change one figure or assumption to test a related concept
- Ensure all figures are internally consistent and arithmetically accurate
"""
    },

    # ── INTERMEDIATE ──────────────────────────────────────────────────────────    

    "advanced_accounts": {
        "name": "Advanced Accounts (Intermediate)",
        "style_guide": """
- Create a realistic Indian company or entity scenario relevant to the topic in the source content
- Include specific transaction amounts in ₹ and a structured data table from the source content
- Where the source content references specific Accounting Standards (AS), cite those standards
- Do NOT introduce AS topics absent from the source content
- Test concepts, computations, or analysis present in the source content
- Later questions may introduce a revised assumption or additional transaction
- Ensure all figures are internally consistent and arithmetically accurate
"""
    },

    "auditing_ethics": {
        "name": "Auditing and Ethics (Intermediate)",
        "style_guide": """
- Create a realistic audit engagement with a named Indian company
- Include specific financial data, internal control observations, and risk factors
- Cover audit planning, risk assessment, internal controls, evidence,
  reporting, or bank audit
- Reference applicable Standards on Auditing (SA) issued by ICAI
- Test audit procedures, professional scepticism, and reporting decisions
- Later questions may introduce a modified fact (e.g., additional risk identified)
  to test a related SA provision
- Include ethical scenarios involving independence or professional conduct where relevant
"""
    },

    "corporate_laws": {
        "name": "Corporate and Other Laws (Intermediate)",
        "style_guide": """
- Create a realistic Indian company, LLP, or foreign exchange scenario
- Include specific dates, statutory deadlines, monetary values, and party names
- Provide a timeline or table of corporate events leading to the legal question
- Reference applicable Acts (Companies Act 2013, LLP Act 2008, FEMA 1999,
  General Clauses Act 1897)
- Test compliance requirements, statutory filings, penalties, and legal consequences
- Later questions may modify a key fact (e.g., date, threshold amount, directorship)
  to test a related provision
- All statutory references and deadlines must be accurate
"""
    },

    "cost_management_accounting": {
        "name": "Cost and Management Accounting (Intermediate)",
        "style_guide": """
- Create a realistic Indian manufacturing or service entity scenario
- Include a detailed cost data table: units, rates, and amounts in ₹
- Cover job/batch/process costing, standard costing, marginal costing,
  activity-based costing, or budgetary control
- Test cost computation, variance analysis, and management decisions (make/buy, pricing)
- Later questions may introduce an additional cost element or change one variable
  (e.g., overhead rate, output level) to test impact
- Ensure all cost figures are internally consistent and arithmetically correct
"""
    },

    "financial_management": {
        "name": "Financial Management (Intermediate)",
        "style_guide": """
- Create a realistic Indian company or project finance scenario
- Include specific financial data: cash flows, cost of capital, leverage ratios in ₹
- Provide a structured table of financial data (e.g., project cash flows, capital mix)
- Cover capital budgeting (NPV/IRR/Payback), capital structure, dividend decisions,
  or working capital management
- Test financial computation, decision-making, and policy evaluation
- Later questions may change one variable (e.g., discount rate, growth rate, tax rate)
  to test impact on decision
- Ensure all computations are internally consistent and arithmetically accurate
"""
    },

    "indirect_tax": {
        "name": "Indirect Tax — GST (Intermediate)",
        "style_guide": """
- Create a realistic Indian GST-registered supplier or recipient scenario
- Include specific transaction details: GSTIN, supply type, values in ₹, and dates
- Provide a formatted table of supplies, ITC ledger, or return data
- Cover supply, place of supply, time of supply, ITC, registration, returns,
  e-way bills, or reverse charge
- Reference CGST/SGST/IGST provisions and relevant sections
- Test GST computation, ITC eligibility, and compliance obligations
- Later questions may modify one supply detail (e.g., interstate vs. intrastate)
  to test a different provision
- Ensure GST figures and HSN/SAC codes are realistic and consistent
"""
    },

    "income_tax": {
        "name": "Income Tax (Intermediate)",
        "style_guide": """
- Create a realistic individual taxpayer or business entity with an Indian name
  and specific profession/business
- Include specific dates using F.Y. 2025-26 / A.Y. 2026-27 timeline
- Provide a formatted table of income particulars with rupee amounts (₹)
- Cover heads of income (salary, house property, business, capital gains,
  other sources), deductions, advance tax, TDS, or return filing
- Test income computation, deduction eligibility, and tax liability
- Later questions may introduce "Assume for this question that…" variations
- Ensure all figures are internally consistent and arithmetically accurate
"""
    },

    "strategic_management": {
        "name": "Strategic Management (Intermediate)",
        "style_guide": """
- Create a realistic Indian company or industry scenario facing a strategic challenge
- Include specific market data, competitive context, and financial indicators
- Provide a structured SWOT table, Porter's Five Forces matrix, or strategic options
- Cover strategic analysis (SWOT, PESTLE, BCG, Porter), strategic choices,
  implementation, and evaluation
- Test strategic analysis, decision-making, and evaluation of alternatives
- Later questions may change one environmental factor or introduce a new competitor
  to test strategic response
- Use realistic Indian industry context (manufacturing, IT, FMCG, banking, etc.)
"""
    },

    # ── FINAL ─────────────────────────────────────────────────────────────────    

    "advanced_financial_management": {
        "name": "Advanced Financial Management (Final)",
        "style_guide": """
- Create a realistic Indian corporate or institutional finance scenario relevant to the topic in the source content
- Include specific financial data (rates, values in ₹/USD) and a structured data table drawn from the source content
- Where the source content references specific instruments, models, or frameworks, use those
- Do NOT introduce financial topics (derivatives, M&A, portfolio models, etc.) absent from the source content
- Test financial computation, risk analysis, or decision-making based on the source content
- Later questions may change one variable (rate, quantity, assumption) from the scenario
- Ensure all computations are internally consistent and arithmetically accurate
"""
    },

    "advanced_auditing": {
        "name": "Advanced Auditing and Assurance (Final)",
        "style_guide": """
- Create a realistic Indian audit or assurance engagement scenario relevant to the topic in the source content
- Include specific financial data, risk indicators, or audit findings drawn from the source content
- Where the source content references specific SA/SQC standards or ethical provisions, cite those
- Do NOT introduce audit standards or topics absent from the source content
- Test complex audit judgment and professional scepticism based on the source content
- Later questions may introduce a new finding or modified fact from the scenario
- Include ethical considerations only if they appear in the source content
"""
    },

    "direct_tax_international": {
        "name": "Direct Tax Laws and International Taxation (Final)",
        "style_guide": """
- Create a realistic Indian taxpayer, MNC, or NRI scenario relevant to the topic in the source content
- Include specific financial data with rupee / foreign currency amounts; use F.Y. 2025-26 / A.Y. 2026-27 timeline
- Provide a formatted table of income particulars or treaty/TP data drawn from the source content
- Where the source content references specific sections of the Income-tax Act 1961 or OECD/UN articles, cite those
- Do NOT introduce tax provisions or topics absent from the source content
- Test tax computation, treaty interpretation, or anti-avoidance analysis based on the source content
- Later questions may change one jurisdictional fact or assumption from the scenario
- Ensure all figures are internally consistent and arithmetically accurate
"""
    },

    "financial_reporting": {
        "name": "Financial Reporting — IND AS (Final)",
        "style_guide": """
- Create a realistic Indian company or entity scenario relevant to the topic in the source content
- Include specific amounts in ₹ and a structured data table drawn from the source content
- Where the source content references specific Ind AS standards, cite those standards
- Do NOT introduce Ind AS standards or topics that are absent from the source content
- Test understanding, application, or analysis of concepts present in the source content
- Later questions may change one variable or assumption from the scenario
- Ensure all figures are internally consistent and arithmetically accurate
"""
    }
}


def get_case_scenario_prompt(
    difficulty, context, chapter_number, chapter_name,
    unit_number, unit_name, subject_context, num_questions=4, topic_name=""
):
    """
    Generate ICAI-standard case scenario MCQ prompt.
    The LLM will produce ONE shared narrative + num_questions related MCQs.
    """
    difficulty_lower = difficulty.lower().replace("-", "_")
    subject_key = normalize_subject_key(subject_context.get("name", ""))

    subject_config = CASE_SCENARIO_SUBJECT_CONFIGS.get(
        subject_key, CASE_SCENARIO_SUBJECT_CONFIGS["taxation"]
    )

    diff_info = DIFFICULTY_DESCRIPTIONS.get(difficulty_lower, DIFFICULTY_DESCRIPTIONS["hard"])

    complexity_map = {
        "easy": (
            "Straightforward scenario with clear, unambiguous facts. "
            "Questions test basic concept recall with minimal computation."
        ),
        "medium": (
            "Scenario with 2-3 interrelated variables requiring application of "
            "provisions and multi-step computation."
        ),
        "hard": (
            "Complex scenario with multiple variables, edge cases, and provisions "
            "requiring multi-step analysis and judgment."
        ),
        "very_hard": (
            "Highly complex scenario with 4-5 interrelated facts, exceptional "
            "situations, cross-referencing of multiple sections/standards, "
            "requiring expert-level analysis and accurate multi-step computation."
        ),
    }
    complexity_instruction = complexity_map.get(difficulty_lower, complexity_map["hard"])

    subject_name_display = subject_context.get("name", subject_key)

    prompt = f"""GENERATE ICAI EXAM CASE SCENARIO MCQ SET — {diff_info['name']} LEVEL

You are an ICAI exam paper setter. Create a publication-ready CASE SCENARIO \
with exactly {num_questions} MCQs strictly following the ICAI format shown below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  MANDATORY RULE — READ BEFORE ANYTHING ELSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The SOURCE CONTENT below is the ONLY material you may use.
• Read the source content first. Identify the core concepts, facts, and
  terminology it contains.
• Your case scenario narrative and ALL questions MUST be derived from those
  concepts — not from your training knowledge about the subject in general.
• TOPIC to test: "{topic_name}"
• If the source content is about technology (AI, ERP, Blockchain, RPA, etc.),
  the scenario MUST be about that technology — NOT about unrelated accounting
  standards, tax computations, or legal provisions.
• Do NOT introduce any topic that is absent from the source content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE CONTENT  ← derive every fact from here
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chapter : {chapter_number} — {chapter_name}
Unit    : {unit_number} — {unit_name}
Topic   : {topic_name}
Subject : {subject_name_display}

{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STYLE GUIDELINES  (format/presentation only — topic is fixed by source above)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{subject_config['style_guide']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CASE SCENARIO COMPLEXITY — {diff_info['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{complexity_instruction}
Key traits: {', '.join(diff_info['characteristics'])}
{get_difficulty_instruction(difficulty_lower, subject_key)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ICAI FORMAT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CASE SCENARIO NARRATIVE:
  • Realistic Indian person/entity name in a context related to "{topic_name}"
  • Include a formatted data table (Particulars | Details/Value) using numbers
    or facts drawn directly from the source content
  • All facts internally consistent and arithmetically accurate
  • Narrative sufficient to answer ALL {num_questions} questions (200–400 words)
  • Do NOT label any data item as "Red Herring" — distractors must look natural

MCQ QUESTIONS ({num_questions} total):
  • Each question asks for exactly ONE value or conclusion
    (NEVER "find X and Y" together — each sub-question gets its own MCQ)
  • All questions test concepts present in the source content about "{topic_name}"
  • Questions progress from foundational → advanced understanding of the topic
  • Q3 onward MAY introduce "Assume for this question that…" modifications
  • Each question: exactly 4 options (A–D); all 4 option values must differ
  • Correct answer requires reasoning or computation based on the source content
  • Distractors represent common calculation errors or misconceptions — NOT labeled
  • Explanation: step-by-step reasoning (100–160 words) ending with:
    "✅ Correct Answer: Option [X]"

ANSWER CONSTRUCTION (for EACH question):
  STEP 1 — Compute the correct answer precisely.
  STEP 2 — Place it in one of A/B/C/D (vary the position across questions).
  STEP 3 — Fill remaining 3 with distinct wrong values (plausible mistakes).
  STEP 4 — Set correct_answer to the LETTER containing the correct value.
  STEP 5 — Verify: read options[correct_answer letter] — does it match Step 1?
            If not, swap the answer into the right option and update the letter.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE — Return ONLY valid JSON (no markdown, no extra text):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "case_scenario_title": "CASE SCENARIO 1",
  "case_scenario_narrative": "Full narrative about {topic_name} with a data table...",
  "questions": [
    {{
      "question_number": 1,
      "question": "Based on the above case scenario, [specific question about {topic_name}]?",
      "options": ["A: ...", "B: ...", "C: ...", "D: ..."],
      "correct_answer": "A",
      "explanation": "Step 1: ... Step 2: ... [full working] ... Option B is wrong because ... ✅ Correct Answer: Option A",
      "difficulty": "{difficulty}"
    }},
    {{
      "question_number": 2,
      "question": "...",
      "options": ["A: ...", "B: ...", "C: ...", "D: ..."],
      "correct_answer": "C",
      "explanation": "Step 1: ... [full working] ... ✅ Correct Answer: Option C",
      "difficulty": "{difficulty}"
    }}
  ]
}}

CRITICAL: Questions must be based ONLY on the source content provided. Every answer must be verifiable from the source content above."""

    return prompt

def normalize_options_order(mcq):
    """
    Normalize options to A/B/C/D order and remove the "OPTION " prefix.
    Also ensures correct_answer is a clean single letter.

    Critical fix: the previous fallback silently set correct_answer = "A" when
    the letter could not be resolved — causing wrong-answer bugs. The function
    now preserves the raw value so that validate_mcq() can catch the bad state
    and trigger a retry instead of silently accepting a wrong answer.
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

    # Clean letter already present — done.
    if raw_correct in {"A", "B", "C", "D"}:
        mcq["correct_answer"] = raw_correct
        return mcq

    # Try to strip trailing punctuation/label suffix: "A)" → "A"
    match = re.match(r"^\s*([A-D])\s*[\)\:\.\-]?", raw_correct)
    if match:
        mcq["correct_answer"] = match.group(1)
        return mcq

    # Try to match raw_correct body text against option bodies
    cleaned_correct = raw_correct
    for i, opt in enumerate(ordered):
        opt_body = re.sub(r"^[A-D]\s*[\)\:\.\-]\s*", "", opt, flags=re.IGNORECASE).strip().upper()
        if cleaned_correct == opt_body:
            mcq["correct_answer"] = chr(ord("A") + i)
            return mcq

    # Could not resolve — leave as-is (invalid letter) so validate_mcq() catches it
    # and triggers a retry instead of silently accepting a wrong answer.
    print(f"   ⚠️  normalize_options_order: could not resolve correct_answer='{raw_correct}' — will fail validation")
    return mcq
