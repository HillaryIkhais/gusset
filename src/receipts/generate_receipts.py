"""Generate GUSSET Decision Receipts from a trial-results file.

Usage:
    PYTHONPATH=src python src/receipts/generate_receipts.py \
        --input reports/live.json --output-dir reports/receipts

    To use v2 scenarios:
    PYTHONPATH=src python src/receipts/generate_receipts.py \
        --input reports/live_v2.json \
        --scenario-file data/scenarios/scenarios_v2.json \
        --output-dir reports/receipts_v2
"""

import argparse
import json
import re
from pathlib import Path

from evaluation import oracle as oracle_v1
from evaluation import oracle_v2 as oracle_v2
from receipts.receipt import build_receipt
from receipts.verify_receipt import verify_receipt


DEFAULT_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"


def load_scenarios(scenarios_path=DEFAULT_SCENARIOS_PATH):
    with open(scenarios_path) as f:
        return json.load(f)["scenarios"]


def oracle_for_scenarios(scenarios_path):
    """v2 datasets are scored with the v2 oracle; everything else uses v1."""
    if scenarios_path and Path(scenarios_path).name == "scenarios_v2.json":
        return oracle_v2
    return oracle_v1


def safe_name(trial_uid):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", trial_uid or "unknown")[:180]


def main():
    parser = argparse.ArgumentParser(description="Generate GUSSET Decision Receipts")
    parser.add_argument("--input", required=True, help="Trial results JSON")
    parser.add_argument("--scenario-file", default=None, help="Path to scenario JSON file")
    parser.add_argument("--output-dir", default="reports/receipts")
    parser.add_argument("--index", default=None, help="Receipt index JSON path")
    args = parser.parse_args()

    results = json.load(open(args.input))
    scenarios_path = args.scenario_file or DEFAULT_SCENARIOS_PATH
    scenarios = load_scenarios(scenarios_path)
    oracle_module = oracle_for_scenarios(scenarios_path)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    index = []
    for result in results:
        if result.get("error"):
            continue
        scenario_id = result.get("scenario_id")
        scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
        if scenario is None:
            print(f"SKIP {result.get('trial_uid')}: unknown scenario {scenario_id}")
            continue
        receipt = build_receipt(result, scenario, oracle_module)
        verification = verify_receipt(
            receipt,
            scenarios=scenarios,
            scenarios_path=scenarios_path,
            oracle_module=oracle_module,
        )
        if not verification["ok"]:
            print(f"WARNING {result.get('trial_uid')}: receipt failed self-verification")
            for reason in verification["reasons"]:
                print(f"  - {reason}")
        name = safe_name(result.get("trial_uid") or result.get("run_id"))
        path = output_dir / f"{name}.json"
        with open(path, "w") as f:
            json.dump(receipt, f, indent=2)
        index.append(
            {
                "trial_uid": receipt["trial_uid"],
                "path": str(path),
                "scenario_id": scenario["id"],
                "condition": receipt["condition"],
                "oracle_action": receipt["decision"]["oracle_action"],
                "recommended_action": receipt["decision"]["recommended_action"],
                "regret": receipt["decision"]["regret"],
                "receipt_hash": receipt["verification"]["receipt_hash"],
                "self_verified": verification["ok"],
            }
        )

    index_path = args.index or str(output_dir / "index.json")
    with open(index_path, "w") as f:
        json.dump(
            {
                "receipt_version": "gusset-receipt-index-1.0",
                "source_results": args.input,
                "scenario_file": args.scenario_file,
                "n_receipts": len(index),
                "receipts": index,
            },
            f,
            indent=2,
        )
    print(f"Wrote {len(index)} receipts to {output_dir}")
    print(f"Index: {index_path}")
    print(f"Self-verified: {sum(1 for item in index if item['self_verified'])}/{len(index)}")


if __name__ == "__main__":
    main()