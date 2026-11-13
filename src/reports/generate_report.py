"""Render a markdown research report from the GUSSET analysis JSON.

This replaces the earlier hardcoded report generator. It reads only the
machine-readable analysis, so it cannot silently substitute a mock finding for
a real one.
"""

import argparse
import json
from pathlib import Path

from analysis.analyze import format_report


def main():
    parser = argparse.ArgumentParser(description="Render GUSSET markdown report")
    parser.add_argument("--analysis", default="reports/analysis.json")
    parser.add_argument("--output", default="reports/GUSSET_report.md")
    args = parser.parse_args()

    with open(args.analysis) as f:
        analysis = json.load(f)
    report = format_report(analysis)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report)
    print(f"Markdown report saved to {args.output}")


if __name__ == "__main__":
    main()
