"""Verify every receipt in a receipt directory.

Usage:
    PYTHONPATH=src python scripts/verify_all_receipts.py reports/receipts

Exits non-zero if any receipt fails verification. This is the check to run
before citing a receipt in the report.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from receipts.receipt import verify_receipt


def load_scenarios():
    path = ROOT / "data" / "scenarios" / "scenarios.json"
    with open(path) as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


def main():
    parser = argparse.ArgumentParser(description="Verify all GUSSET receipts")
    parser.add_argument("directory", nargs="?", default="reports/receipts")
    parser.add_argument("--write-summary", default=None)
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        raise SystemExit(f"No such directory: {directory}")

    scenarios = load_scenarios()
    paths = sorted(p for p in directory.glob("*.json") if p.name != "index.json")
    if not paths:
        raise SystemExit(f"No receipts found in {directory}")

    summary = []
    failures = 0
    for path in paths:
        receipt = json.load(open(path))
        result = verify_receipt(receipt, registered_scenarios=scenarios)
        if not result["ok"]:
            failures += 1
        summary.append(
            {
                "path": str(path),
                "trial_uid": receipt.get("trial_uid"),
                "condition": receipt.get("condition"),
                "ok": result["ok"],
                "reasons": result["reasons"],
                "checks": len(result["checks"]),
            }
        )
        print(f"[{'PASS' if result['ok'] else 'FAIL'}] {path.name}")
        for reason in result["reasons"]:
            print(f"       {reason}")

    print(f"\n{len(paths) - failures}/{len(paths)} receipts verified")

    if args.write_summary:
        Path(args.write_summary).parent.mkdir(parents=True, exist_ok=True)
        with open(args.write_summary, "w") as f:
            json.dump(
                {
                    "n_receipts": len(paths),
                    "n_passed": len(paths) - failures,
                    "n_failed": failures,
                    "receipts": summary,
                },
                f,
                indent=2,
            )
        print(f"Summary: {args.write_summary}")

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
