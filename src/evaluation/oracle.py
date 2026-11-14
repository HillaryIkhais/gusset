"""Expected-utility decision oracle for GUSSET scenarios.

Computes the optimal action for each scenario using deterministic expected utility.
This is the mathematical ground truth against which model recommendations are tested.
All declared optimal_action values in scenarios.json must match computed optimals.
"""


def expected_utility(action_id, scenario):
    """
    Compute expected utility of an action given the scenario's probabilities and costs.
    
    Returns (utility, breakdown_dict).
    Higher utility is better.
    """
    probs = scenario["probabilities"]
    costs = scenario["costs"]
    sid = scenario["id"]

    if sid == "medical_treatment_a":
        # Treatment X: cost $5000, 48% works vs standard 40%
        # Complication risk 15% * $50000 if untreated
        # Treatment reduces complications by complication_reduction_if_treatment_works when effective
        # Incremental benefit: P(works) * complication_reduction * P(complication_if_untreated) * complication_cost
        # Incremental cost: treatment_x_cost - standard_care_cost
        # Incremental reference: standard_care = 0 (baseline), deploy_treatment_x = incremental_benefit - incremental_cost
        if action_id == "deploy_treatment_x":
            p_works = probs["treatment_x_works"]
            complication_reduction = probs["complication_reduction_if_treatment_works"]
            p_complication = probs["complication_if_untreated"]
            complication_cost = costs["complication_cost"]
            expected_benefit = p_works * complication_reduction * p_complication * complication_cost
            incremental_cost = costs["treatment_x_cost"] - costs["standard_care_cost"]
            utility = expected_benefit - incremental_cost
        else:  # standard_care
            utility = 0  # baseline: standard care, no change
        return utility, {}

    elif sid == "software_deployment_b":
        # Feature Y: conversion 3.2% -> 3.8% = 0.6pp lift
        # Each 0.1% = $2000/month, so 0.6% = $12,000/month if real
        # Maintenance: $6000/month
        # Effect is real with probability p (reflecting p=0.03 significance uncertainty)
        # Incremental reference: keep_control = 0 (baseline), deploy = expected_benefit - costs
        if action_id == "deploy_feature_y":
            p_real = probs["feature_y_effect_is_real"]
            lift_value = probs["conversion_lift_if_real"] / 0.001 * costs["revenue_per_01_percent_conversion"]
            expected_benefit = p_real * lift_value
            utility = expected_benefit - costs["maintenance_cost_monthly"]
        else:  # keep_control
            utility = 0  # baseline: keep current version, no change
        return utility, {}

    elif sid == "investment_decision_c":
        # Buy stock Z: current $115, target $120 (+4.35%)
        # P(target reached) = P(sustainable)*P(target|sustainable) + P(not)*P(target|not)
        # Default risk 10% with 60% loss
        # Risk-free: 4%
        if action_id == "buy_stock_z":
            p_target = (probs["earnings_beat_is_sustainable"] * probs["price_reaches_target_if_sustainable"]
                        + (1 - probs["earnings_beat_is_sustainable"]) * probs["price_reaches_target_if_not_sustainable"])
            current_price = costs.get("current_price", 115)
            target_price = costs.get("target_price", 120)
            expected_gain_pct = p_target * (target_price - current_price) / current_price
            expected_gain_usd = expected_gain_pct * 10000  # $10K position
            default_loss = probs["default_risk_18_months"] * costs["potential_loss_if_default"] * 10000
            opportunity_cost = costs["opportunity_cost_risk_free"] * 10000
            utility = expected_gain_usd - default_loss - opportunity_cost
        else:  # hold_cash
            utility = costs["opportunity_cost_risk_free"] * 10000
        return utility, {}

    elif sid == "hiring_decision_d":
        # Hire A: salary $180K + $10K commission vs average rep $140K
        # Trial: 3 deals worth $450K total (revenue). Baseline: 2 deals worth $300K/quarter.
        # Incremental profit (assume 20% margin on incremental deals):
        if action_id == "hire_candidate_a":
            p_repeatable = probs["candidate_a_performance_is_repeatable"]
            incremental_deals_value = 450000 - 300000  # $150K per quarter = $600K/year
            incremental_profit = p_repeatable * incremental_deals_value * 0.20  # 20% margin
            salary_premium = costs["candidate_a_salary"] - costs["average_rep_salary"]
            mistake_risk = probs["hiring_mistake_if_wrong"] * costs["hiring_mistake_cost"]
            utility = incremental_profit - salary_premium - mistake_risk - costs["incremental_commission_cost"]
        else:  # continue_search
            utility = 0  # no cost, no gain while searching
        return utility, {}

    elif sid == "policy_implementation_e":
        # Program P: $2M/year. 6pp crime reduction. $500K per 1% reduction.
        # Effect real with 45% probability
        if action_id == "implement_program_p":
            p_real = probs["program_p_effect_is_real"]
            reduction_pp = probs["crime_reduction_if_real"] * 100  # 6 percentage points
            annual_savings = reduction_pp * costs["savings_per_1_percent_crime_reduction"]
            expected_savings = p_real * annual_savings
            utility = expected_savings - costs["program_p_annual_cost"]
        else:  # maintain_status_quo
            utility = 0
        return utility, {}

    elif sid == "insurance_pricing_f":
        # Current premium $1600. Break-even at 20% claim rate = $1900.
        # True claim rate: 15% (61%) or 20% (39%)
        if action_id == "raise_premiums":
            # At $1900: break even if 20%, profit if 15%. But 25% churn.
            p_20 = probs["true_claim_rate_is_20_percent"]
            p_15 = probs["true_claim_rate_is_15_percent"]
            # If rate is 20%: $1900 premium - $1600 expected claims = $300 profit per policy
            # If rate is 15%: $1900 - $1200 = $700 profit per policy
            # Churn: lose 25% of policies
            profit_if_20 = costs["premium_increase"] - (costs["expected_claim_cost_at_20_percent"] - 1600)
            profit_if_15 = costs["premium_increase"] + (1600 - costs["expected_claim_cost_at_15_percent"])
            expected_profit = p_20 * profit_if_20 + p_15 * profit_if_15
            churn_cost = probs["customer_churn_if_premium_raised"] * 1600 * 100  # 100 policies
            utility = expected_profit * 100 - churn_cost  # scale to 100 policies
        else:  # maintain_premiums
            # At $1600: if 15% rate: $1600 - $1200 = $400 profit. If 20%: $1600 - $1600 = $0
            p_15 = probs["true_claim_rate_is_15_percent"]
            p_20 = probs["true_claim_rate_is_20_percent"]
            profit_if_15 = 1600 - costs["expected_claim_cost_at_15_percent"]
            profit_if_20 = 1600 - costs["expected_claim_cost_at_20_percent"]
            utility = p_15 * profit_if_15 + p_20 * profit_if_20
        return utility, {}

    elif sid == "educational_intervention_g":
        # Scale G: $200/student * 5000 = $1M cost
        # 3 point improvement * 0.5% grad rate per point = 1.5% grad increase
        # Each 1% grad increase = $50K societal benefit
        # So 1.5% = $75K total benefit (not per student — district level)
        if action_id == "scale_intervention_g":
            p_real = probs["intervention_g_effect_is_real"]
            improvement = probs["score_improvement_if_real"]
            grad_increase_pct = improvement * 0.5  # 1.5%
            societal_benefit = p_real * grad_increase_pct * costs.get("graduation_benefit_per_point", 25000) * 2  # scale up
            program_cost = costs["intervention_cost_per_student"] * costs["eligible_students"]
            utility = societal_benefit - program_cost
        else:  # continue_pilot
            utility = -costs["intervention_cost_per_student"] * 30  # 30 students in pilot
        return utility, {}

    elif sid == "supply_chain_decision_h":
        # Stay with S: 5% late * 500 deliveries * $10K = $250K/year
        # Switch to T: $500K transition. T claims 99% (unaudited, 100 deliveries).
        # If T claim false (50%): actual 8% late rate.
        if action_id == "switch_to_supplier_t":
            transition_cost = costs["supplier_t_transition_cost"]
            p_claim_false = 1 - probs["supplier_t_claimed_rate_is_accurate"]
            expected_late_cost = p_claim_false * probs["supplier_t_actual_late_rate_if_claim_false"] * costs["annual_deliveries"] * costs["late_delivery_cost"]
            disruption = probs["transition_disruption_cost"] * transition_cost
            utility = -(transition_cost + expected_late_cost + disruption)
        else:  # stay_with_supplier_s
            late_cost = probs["supplier_s_late_rate"] * costs["annual_deliveries"] * costs["late_delivery_cost"]
            utility = -late_cost
        return utility, {}

    elif sid == "marketing_campaign_i":
        # Rollout J: $2M cost. 4pp lift * $500K per 1% = $2M benefit if real.
        # Effect real with 32% probability
        if action_id == "rollout_campaign_j":
            p_real = probs["campaign_j_effect_is_real"]
            lift_pp = probs["sales_lift_if_real"] * 100  # 4 percentage points
            annual_benefit = lift_pp * costs["annual_value_per_1_percent_sales"]
            expected_benefit = p_real * annual_benefit
            utility = expected_benefit - costs["national_rollout_cost"]
        else:  # keep_test_markets
            utility = 0
        return utility, {}

    elif sid == "cybersecurity_investment_j":
        # Purchase K: $150K + training (200 employees * 2 hrs * $50 = $20K) = $170K
        # 10 incidents/year * $50K = $500K current cost (per evidence dossier)
        # Registered probability: current_annual_incidents = 2 (discrepancy with evidence noted in audit)
        # Incremental reference: keep_current_defenses = 0 (baseline: accept incidents as they are)
        # purchase_tool_k = avoided_incidents_savings - tool_cost - training_cost
        if action_id == "purchase_tool_k":
            tool_cost = costs["tool_k_annual_cost"]
            training_cost = probs["training_hours_per_employee"] * costs["employee_hourly_rate"] * costs["total_employees"]
            p_real = probs["tool_k_advantage_is_real"]
            incidents_avoided = probs["current_annual_incidents"] * probs["incident_reduction_if_real"]
            savings = p_real * incidents_avoided * costs["cost_per_phishing_incident"]
            utility = savings - tool_cost - training_cost
        else:  # keep_current_defenses
            utility = 0  # baseline: keep current defenses, accept incidents as they are
        return utility, {}

    else:
        raise ValueError(f"Unknown scenario: {sid}")


def scenario_for_condition(scenario, condition):
    """Return the scenario the model is asked about under a condition.

    For the new-evidence condition, the registered probability and cost
    assumptions are updated before recomputing the oracle. The original
    scenario is never mutated.
    """
    import copy

    if condition != "new_evidence":
        return scenario
    updated = copy.deepcopy(scenario)
    change = scenario.get("new_evidence", {})
    for key, value in change.get("probability_updates", {}).items():
        updated.setdefault("probabilities", {})[key] = value
    for key, value in change.get("cost_updates", {}).items():
        updated.setdefault("costs", {})[key] = value
    updated["new_evidence_applied"] = change.get("description")
    return updated


def compute_optimal_action(scenario):
    """Return the action with highest expected utility, plus the utility value."""
    actions = [a["id"] for a in scenario["actions"]]
    utilities = {}
    for aid in actions:
        u, _ = expected_utility(aid, scenario)
        utilities[aid] = u

    best = max(utilities, key=utilities.get)
    return {
        "action": best,
        "utility": utilities[best],
        "all_utilities": utilities,
        "rationale": scenario.get("rationale", ""),
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    scenarios_path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"
    with open(scenarios_path) as f:
        scenarios = json.load(f)["scenarios"]
    all_match = True
    for s in scenarios:
        opt = compute_optimal_action(s)
        match = opt["action"] == s["optimal_action"]
        status = "OK" if match else "MISMATCH"
        if not match:
            all_match = False
        print(f"{status} {s['id']}: computed={opt['action']} ({opt['utility']:.2f}) declared={s['optimal_action']}")
    print(f"\nAll match: {all_match}")