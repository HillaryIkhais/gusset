"""Independently verify a GUSSET Decision Receipt.

Usage:
    PYTHONPATH=src python src/receipts/verify_receipt.py reports/receipts/<name>.json

The verifier recomputes the scenario hash, transcript hashes, every expected
utility, the oracle action, the regret, and the receipt hash. It does not trust
the numbers stored in the receipt.
"""

import argparse
import json
from pathlib import Path

from receipts.receipt import verify_receipt


def load_scenarios():
    path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"
    with open(path) as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


def main():
    parser = argparse.ArgumentParser(description="Verify a GUSSET Decision Receipt")
    parser.add_argument("receipt", help="Receipt JSON path")
    parser.add_argument("--quiet", action="store_true", help="Only print PASS/FAIL")
    args = parser.parse_args()

    receipt = json.load(open(args.receipt))
    scenarios = load_scenarios()
    result = verify_receipt(receipt, registered_scenarios=scenarios)

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
        for check in result["checks"]:
            print(f"[{'PASS' if check['ok'] else 'FAIL'}] {check['check']} {check['detail']}")
        print("")
        print("PASS" if result["ok"] else "FAIL")
        if result["reasons"]:
            print("\nFailures:")
            for reason in result["reasons"]:
                print(f"- {reason}")
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
