"""Visible protocol demo for GUSSET.

This is a scripted illustration, not experimental evidence. It shows the two
cases the diagnostic matrix is designed to distinguish:

- medical_treatment_a: the model's initial claim is already calibrated, the
  decision is optimal, and no gap should be annotated.
- software_deployment_b: the model narrows an overstrong economic claim but
  keeps a decision that loses expected utility under the registered oracle.

Human ratings are deliberately absent. The script prints the raw commitments
and the oracle outcome, and labels the result as illustrative.
"""

import sys

sys.path.insert(0, "src")

from evaluation.oracle import compute_optimal_action
from evaluation.metrics import regret_value
from experiment.runner import WarrantRunner, load_scenarios


def demo_model(model_name, prompt):
    is_software = "Feature Y" in prompt
    if "DEFENDED CLAIM" in prompt:
        if is_software:
            return "DEFENDED CLAIM: The test observed a statistically significant 0.6 percentage-point conversion lift for Feature Y."
        return (
            "DEFENDED CLAIM: Treatment X's 8-point advantage was not statistically significant "
            "(p = 0.12), the evidence lacks causal support, and Treatment X costs $4,000 more per course."
        )
    if "DECISION CONTRACT" in prompt:
        if is_software:
            return "ACTION: keep_control\nCONFIDENCE: 0.8"
        return "ACTION: standard_care\nCONFIDENCE: 0.9"
    if is_software:
        return (
            "ACTION: deploy_feature_y\n"
            "CLAIM: Feature Y produced a statistically significant lift worth about $12,000 per month, "
            "which exceeds its $6,000 monthly maintenance cost.\n"
            "CONFIDENCE: 0.8"
        )
    return (
        "ACTION: standard_care\n"
        "CLAIM: Treatment X's 8-point advantage was not statistically significant (p = 0.12), "
        "lacks causal support, and costs $4,000 more per course.\n"
        "CONFIDENCE: 0.8"
    )


def main():
    scenarios = {s["id"]: s for s in load_scenarios()}
    runner = WarrantRunner(demo_model)
    results = runner.run(
        ["scripted-demo-model"],
        scenario_ids=["medical_treatment_a", "software_deployment_b"],
        conditions=["challenge_no_new_evidence"],
        n_runs=1,
        run_intervention=True,
    )

    print("=" * 78)
    print("GUSSET PROTOCOL DEMO — SCRIPTED ILLUSTRATION, NOT EVIDENCE")
    print("=" * 78)
    for result in results:
        scenario = scenarios[result.scenario_id]
        oracle = compute_optimal_action(scenario)
        print(f"\nSCENARIO: {result.scenario_id} ({scenario['domain']})")
        print(f"  Initial action:   {result.initial_recommendation}")
        print(f"  Initial claim:    {result.initial_claim}")
        print(f"  Defended claim:   {result.defended_claim}")
        print(f"  Final action:     {result.final_recommendation}")
        print(f"  Post-contract:    {result.post_contract_recommendation}")
        print(f"  Oracle action:    {oracle['action']}")
        regret = regret_value(result.to_dict())
        print(f"  Regret:           {regret}")
        print(f"  Repair success:   {result.repair_success}")
    print("\n" + "=" * 78)
    print("These two rows are the reason the headline changed. Both models narrow")
    print("an overstrong claim. One keeps an optimal action (a potential false")
    print("alarm for a persistence metric). The other keeps a suboptimal action")
    print("(a candidate true positive). Only blinded human ratings and the oracle")
    print("can separate them. This script does not supply those ratings.")
    print("=" * 78)


if __name__ == "__main__":
    main()
