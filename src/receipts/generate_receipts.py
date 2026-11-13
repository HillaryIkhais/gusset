"""Generate GUSSET Decision Receipts from a trial-results file.

Usage:
    PYTHONPATH=src python src/receipts/generate_receipts.py \
        --input reports/live.json --output-dir reports/receipts
"""

import argparse
import json
import re
from pathlib import Path

from receipts.receipt import build_receipt, verify_receipt


def load_scenarios():
    path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"
    with open(path) as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


def safe_name(trial_uid):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", trial_uid or "unknown")[:180]


def main():
    parser = argparse.ArgumentParser(description="Generate GUSSET Decision Receipts")
    parser.add_argument("--input", required=True, help="Trial results JSON")
    parser.add_argument("--output-dir", default="reports/receipts")
    parser.add_argument("--index", default=None, help="Receipt index JSON path")
    args = parser.parse_args()

    results = json.load(open(args.input))
    scenarios = load_scenarios()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    index = []
    for result in results:
        if result.get("error"):
            continue
        scenario = scenarios.get(result.get("scenario_id"))
        if scenario is None:
            print(f"SKIP {result.get('trial_uid')}: unknown scenario")
            continue
        receipt = build_receipt(result, scenario)
        verification = verify_receipt(receipt, registered_scenarios=scenarios)
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
