"""Independently verify a GUSSET Decision Receipt.

Usage:
    PYTHONPATH=src python src/receipts/verify_receipt.py reports/receipts/<name>.json

The verifier recomputes the scenario hash, transcript hashes, every expected
utility, the oracle action, the regret, and the receipt hash. It does not trust
the numbers stored in the receipt.
"""

import argparse
import hashlib
import json
from pathlib import Path

from evaluation import oracle as oracle_v1
from evaluation import oracle_v2 as oracle_v2

DEFAULT_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def load_scenarios(scenarios_path=DEFAULT_SCENARIOS_PATH):
    with open(scenarios_path) as f:
        return json.load(f)["scenarios"]


def find_scenario(scenarios, scenario_id):
    if isinstance(scenarios, dict):
        return scenarios.get(scenario_id)
    for s in scenarios:
        if s["id"] == scenario_id:
            return s
    return None


def verify_receipt(receipt, scenarios=None, scenarios_path=None, oracle_module=None):
    """Verify a receipt by recomputing everything from the stored scenario.

    Returns a dict with 'ok' (bool) and 'reasons' (list of failure reasons).
    """
    if scenarios is None:
        if scenarios_path is None:
            scenarios_path = DEFAULT_SCENARIOS_PATH
        scenarios = load_scenarios(scenarios_path)

    scenario_id = receipt.get("scenario_id") or receipt.get("scenario", {}).get("id")
    scenario = find_scenario(scenarios, scenario_id)
    if scenario is None:
        return {"ok": False, "reasons": [f"scenario '{scenario_id}' not found"]}

    # Determine which oracle to use
    if oracle_module is None:
        oracle_module = oracle_v2 if str(scenarios_path).endswith("scenarios_v2.json") else oracle_v1

    # Recompute scenario hash
    stored_scenario = receipt.get("scenario")
    if stored_scenario is not None:
        computed_hash = sha256_obj(stored_scenario)
        stored_hash = receipt.get("scenario_hash")
        if computed_hash != stored_hash:
            return {
                "ok": False,
                "reasons": [f"scenario hash mismatch: computed={computed_hash}, stored={stored_hash}"],
            }

    # Recompute oracle action and utilities
    condition = receipt.get("condition") or "challenge_no_new_evidence"
    scenario_for_condition = oracle_module.scenario_for_condition(scenario, condition)
    oracle = oracle_module.compute_optimal_action(scenario_for_condition)

    stored_decision = receipt.get("decision", {})
    stored_oracle_action = stored_decision.get("oracle_action")
    stored_oracle_utility = stored_decision.get("oracle_utility")
    stored_regret = stored_decision.get("regret")
    stored_utilities = stored_decision.get("utilities", {})

    reasons = []

    if oracle["action"] != stored_oracle_action:
        reasons.append(f"oracle action mismatch: computed={oracle['action']}, stored={stored_oracle_action}")

    if oracle["utility"] != stored_oracle_utility:
        reasons.append(f"oracle utility mismatch: computed={oracle['utility']}, stored={stored_oracle_utility}")

    # Check all stored utilities match recomputed ones
    for action_name, stored_util in stored_utilities.items():
        if action_name in oracle["all_utilities"]:
            if oracle["all_utilities"][action_name] != stored_util:
                reasons.append(f"utility mismatch for '{action_name}': computed={oracle['all_utilities'][action_name]}, stored={stored_util}")

    # Recompute receipt hash
    receipt_copy = json.loads(json.dumps(receipt))
    receipt_copy["verification"]["receipt_hash"] = None
    computed_receipt_hash = sha256_obj(receipt_copy)
    stored_receipt_hash = receipt.get("verification", {}).get("receipt_hash")

    if stored_receipt_hash is not None and computed_receipt_hash != stored_receipt_hash:
        reasons.append(f"receipt hash mismatch: computed={computed_receipt_hash}, stored={stored_receipt_hash}")

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "computed_oracle_action": oracle["action"],
        "computed_oracle_utility": oracle["utility"],
        "computed_regret": oracle["utility"] - oracle["all_utilities"].get(receipt.get("decision", {}).get("recommended_action")) if receipt.get("decision", {}).get("recommended_action") in oracle["all_utilities"] else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify a GUSSET Decision Receipt")
    parser.add_argument("receipt", help="Receipt JSON path")
    parser.add_argument("--scenario-file", default=None, help="Path to scenario JSON file")
    parser.add_argument("--quiet", action="store_true", help="Only print PASS/FAIL")
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenario_file)

    if args.scenario_file and args.scenario_file.endswith("scenarios_v2.json"):
        oracle_module = oracle_v2
    else:
        oracle_module = oracle_v1

    receipt = json.load(open(args.receipt))
    result = verify_receipt(receipt, scenarios, args.scenario_file, oracle_module)

    if args.quiet:
        print("PASS" if result["ok"] else "FAIL")
    else:
        print(f"Receipt: {args.receipt}")
        print(f"Trial: {receipt.get('trial_uid')}")
        print(f"Model: {receipt.get('model')}")
        print(f"Condition: {receipt.get('condition')}")
        print(f"Oracle: {receipt.get('decision', {}).get('oracle_action')}")
        print(f"Recommended: {receipt.get('decision', {}).get('recommended_action')}")
        print(f"Regret: {receipt.get('decision', {}).get('regret')}")
        print("")
        for check in result.get("reasons", []):
            print(f"- {check}")
        print("")
        print("PASS" if result["ok"] else "FAIL")
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()