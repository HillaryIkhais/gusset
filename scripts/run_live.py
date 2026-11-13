"""Live NVIDIA run helper.

Loads NVIDIA_API_KEY from the workspace .env without printing it, sets a
pilot-friendly token limit, and runs the registered conditions.

Example:
    PYTHONPATH=src python scripts/run_live.py \
        --conditions challenge_no_new_evidence --n-runs 1 --delay 8 \
        --output reports/live_challenge.json
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment.model_clients import NVIDIAClient
from experiment.runner import WarrantRunner


def load_env():
    env_path = ROOT.parent / ".env"
    if not env_path.exists():
        raise SystemExit(f"Missing {env_path}")
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


def main():
    parser = argparse.ArgumentParser(description="Run a live GUSSET pilot")
    parser.add_argument("--model", default="nvidia/nemotron-3.5-super-vl-120b-a12b")
    parser.add_argument("--conditions", nargs="+", default=["challenge_no_new_evidence"])
    parser.add_argument("--scenarios", nargs="+")
    parser.add_argument("--n-runs", type=int, default=1)
    parser.add_argument("--delay", type=float, default=8.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--no-intervention", action="store_true")
    parser.add_argument("--output", default="reports/live_challenge.json")
    args = parser.parse_args()

    load_env()
    os.environ.setdefault("NVIDIA_MAX_TOKENS", str(args.max_tokens))
    os.environ.setdefault("NVIDIA_TIMEOUT", str(args.timeout))

    client = NVIDIAClient()
    runner = WarrantRunner(lambda model, prompt: client(model, prompt))
    conditions = "all" if args.conditions == ["all"] else args.conditions
    results = runner.run(
        [args.model],
        scenario_ids=args.scenarios,
        conditions=conditions,
        n_runs=args.n_runs,
        providers={args.model: "nvidia"},
        output_path=args.output,
        run_intervention=not args.no_intervention,
        request_delay=args.delay,
        max_retries=3,
    )

    errors = [r for r in results if isinstance(r, dict) and r.get("error")]
    ok = [r for r in results if not (isinstance(r, dict) and r.get("error"))]
    print(f"\nSaved {len(results)} records ({len(ok)} ok, {len(errors)} errors) to {args.output}")
    for result in errors:
        print(f"  ERROR {result.get('scenario_id')} {result.get('condition')}: {result.get('error', '')[:160]}")


if __name__ == "__main__":
    main()
