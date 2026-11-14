"""Print the GUSSET headline table from the committed evidence file.

Works from a clean clone: reads only evidence/headline_results.json, which is
committed to the repository. No reports/ directory and no API key required.

Usage:
    python3 scripts/show_evidence.py
    python3 scripts/show_evidence.py --json
"""

import argparse
import json
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence" / "headline_results.json"


def main():
    parser = argparse.ArgumentParser(description="Show GUSSET headline evidence")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    args = parser.parse_args()

    if not EVIDENCE.exists():
        print(f"ERROR: evidence file not found: {EVIDENCE}", file=sys.stderr)
        return 1

    with open(EVIDENCE) as f:
        ev = json.load(f)

    if args.json:
        print(json.dumps(ev, indent=2))
        return 0

    h = ev["headline"]
    s = ev["sample"]
    m = h["diagnostic_matrix"]

    print("=" * 70)
    print("GUSSET HEADLINE EVIDENCE")
    print("=" * 70)
    print(f"Evidence version:  {ev['evidence_version']}")
    print(f"Evidence class:    {h['evidence_class']}")
    print(f"Source:            {ev['generated_from']}")
    print()
    print("CLAIM")
    print(f"  {h['claim']}")
    print()
    print("SAMPLE  (state N next to any percentage)")
    print(f"  Annotated items:     {s['annotated_items']}   (raw trials: {s['raw_trials']})")
    print(f"  Annotation source:   {s['annotation_source']}")
    print(f"  Models / conditions: {s['models']} / {', '.join(s['conditions'])}")
    print(f"  Excluded:            {[e['scenario_id'] for e in s['excluded']]}")
    print(f"  NOTE:                {s['note']}")
    print()
    print("PRIMARY RESULT: does the gap predict regret?   (N = %d)" % h["n"])
    print("-" * 70)
    print("                    Regret    No regret")
    print(f"  Gap present       {m['true_positive']:>4}       {m['false_alarm']:>4}")
    print(f"  No gap            {m['false_reassurance']:>4}       {m['true_negative']:>4}")
    print("-" * 70)
    print(f"  Judge accuracy:            {h['judge_accuracy'] * 100:5.1f}%")
    print(f"  Always-negative baseline:  {h['always_negative_baseline_accuracy'] * 100:5.1f}%")
    print(f"  Sensitivity:               {h['sensitivity'] * 100:5.1f}%")
    print(f"  Specificity:               {h['specificity'] * 100:5.1f}%")
    print(f"  Matthews phi:              {h['phi']:+.3f}")
    print()
    print("INTERPRETATION")
    print("  The judge scored WORSE than predicting 'no regret' every time.")
    print("  It identified 0 of the regret cases. Honesty rating and decision")
    print("  quality did not track each other in this sample.")
    print()
    print("CONTRASTING CASES")
    for c in ev["contrasting_cases"]:
        print(f"  {c['scenario_id']}")
        print(f"    gap={c['gap_severity']}  regret={c['regret']:.0f}  "
              f"cell={c['diagnostic_cell']}")
        print(f"    model chose: {c['final_action']}   oracle: {c['oracle_action']}")
    print()
    print("EVIDENCE CLASSES")
    for k, v in ev["evidence_classes"].items():
        print(f"  {k:12s} {v}")
    print()
    print("=" * 70)
    print("VERIFY INDEPENDENTLY:")
    print("  PYTHONPATH=src python3 -m unittest discover -s tests   # 11/11")
    print("  PYTHONPATH=src python3 demo/gusset_demo.py             # 2 cases")
    print("  python3 scripts/show_evidence.py                       # this table")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
