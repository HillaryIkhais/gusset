"""Run the decision-contract pass on existing trial records.

This is separate from the initial/defended/final protocol so that a slow or
truncated contract call does not force a re-run of the whole trial.

Usage:
    PYTHONPATH=src python scripts/run_contracts.py \
        --input reports/live_challenge.json \
        --output reports/live_challenge_contracts.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.oracle import compute_optimal_action, scenario_for_condition
from experiment.model_clients import NVIDIAClient
from experiment.runner import WarrantRunner, load_scenarios, utc_now


def load_env():
    env_path = ROOT.parent / ".env"
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


def main():
    parser = argparse.ArgumentParser(description="Run GUSSET decision contracts")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="reports/live_with_contracts.json")
    parser.add_argument("--model", default="nvidia/nemotron-3.5-super-vl-120b-a12b")
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--max-tokens", type=int, default=1024, help="Token budget for contract calls")
    parser.add_argument("--force", action="store_true", help="Re-run contracts that already exist")
    args = parser.parse_args()

    load_env()
    os.environ.setdefault("NVIDIA_CONTRACT_MAX_TOKENS", str(args.max_tokens))
    results = json.load(open(args.input))
    scenarios = {s["id"]: s for s in load_scenarios()}
    client = NVIDIAClient()
    runner = WarrantRunner(lambda model, prompt: client(model, prompt))

    done = 0
    skipped = 0
    for result in results:
        if result.get("error"):
            continue
        if result.get("post_contract_recommendation") and not args.force:
            skipped += 1
            continue
        scenario = scenarios.get(result["scenario_id"])
        if scenario is None:
            continue
        condition = result.get("condition") or "challenge_no_new_evidence"
        condition_scenario = scenario_for_condition(scenario, condition)
        oracle = compute_optimal_action(condition_scenario)
        valid_actions = {a["id"] for a in condition_scenario["actions"]}
        prompt = runner._build_contract_prompt(condition_scenario, result.get("final_recommendation"))
        try:
            response = client(args.model, prompt)
        except Exception as exc:
            print(f"ERROR {result.get('trial_uid')}: {exc}")
            continue
        action, _claim, confidence, valid = runner._parse_decision(response, valid_actions)
        result["phase4_prompt"] = prompt
        result["phase4_raw_response"] = response
        result["post_contract_recommendation"] = action
        result["post_contract_confidence"] = confidence
        result["post_contract_action_valid"] = valid
        result["intervention_applied"] = True
        result["verified_recommendation"] = action
        result["repair_success"] = action == oracle["action"]
        result["contract_timestamp"] = utc_now()
        done += 1
        print(f"{result.get('scenario_id')}: {result.get('final_recommendation')} -> {action} (oracle {oracle['action']})")
        time.sleep(args.delay)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Ran {done} contracts, skipped {skipped}, saved to {args.output}")


if __name__ == "__main__":
    main()
