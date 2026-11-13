"""CLI entry point for running GUSSET experiments.

Examples:
    # Pipeline check only; this is not evidence.
    PYTHONPATH=src python src/experiment/run_cli.py --mock --conditions all \
        --output reports/mock_run.json

    # Live pilot: one condition, one run per scenario.
    PYTHONPATH=src python src/experiment/run_cli.py \
        --provider nvidia \
        --models nvidia/nemotron-3.5-super-vl-120b-a12b \
        --conditions challenge_no_new_evidence \
        --n-runs 1 --request-delay 10 \
        --output reports/live_challenge.json

    # Full control design once rate limits allow.
    PYTHONPATH=src python src/experiment/run_cli.py \
        --provider nvidia \
        --models nvidia/nemotron-3.5-super-vl-120b-a12b \
        --conditions all --n-runs 3 --request-delay 10 \
        --output reports/live_all.json

Required env var: NVIDIA_API_KEY for the NVIDIA provider.
"""

import argparse
import json
import sys
from pathlib import Path

from experiment.runner import CONDITIONS, WarrantRunner
from experiment.model_clients import make_client


def mock_model(model_name, prompt):
    import re

    actions = re.findall(r"^- ([a-z0-9_]+):", prompt, flags=re.MULTILINE)
    action = actions[0] if actions else "unknown"
    if "DEFENDED CLAIM" in prompt:
        return "DEFENDED CLAIM: The evidence shows an association, not a demonstrated causal benefit."
    if "DECISION CONTRACT" in prompt:
        return f"ACTION: {action}\nCONFIDENCE: 0.9"
    return (
        f"ACTION: {action}\n"
        "CLAIM: The evidence supports this action, although the comparison is uncertain.\n"
        "CONFIDENCE: 0.7"
    )


def main():
    parser = argparse.ArgumentParser(description="Run GUSSET experiment")
    parser.add_argument("--provider", choices=["anthropic", "openai", "nvidia"])
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--mock", action="store_true", help="Run with a deterministic mock model")
    parser.add_argument("--scenarios", nargs="+", help="Scenario IDs (default: all)")
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["challenge_no_new_evidence"],
        help=f"Conditions to run: {', '.join(CONDITIONS)}, or 'all'",
    )
    parser.add_argument("--n-runs", type=int, default=1)
    parser.add_argument("--output", default="reports/run_results.json")
    parser.add_argument("--request-delay", type=float, default=0.0, help="Seconds between trials")
    parser.add_argument("--no-intervention", action="store_true", help="Skip the decision-contract call")
    parser.add_argument("--max-retries", type=int, default=4)
    args = parser.parse_args()

    if args.mock:
        model_interface = mock_model
        model_names = ["mock-model"]
        providers = {"mock-model": "mock"}
    else:
        if not args.provider or not args.models:
            parser.error("--provider and --models are required unless --mock is set")
        client = make_client(args.provider)
        model_interface = lambda model, prompt: client(model, prompt)
        model_names = args.models
        providers = {model: args.provider for model in args.models}

    conditions = args.conditions
    if conditions == ["all"]:
        conditions = "all"

    runner = WarrantRunner(model_interface)
    results = runner.run(
        model_names,
        scenario_ids=args.scenarios,
        n_runs=args.n_runs,
        providers=providers,
        conditions=conditions,
        run_intervention=not args.no_intervention,
        request_delay=args.request_delay,
        max_retries=args.max_retries,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    runner.save(output_path)

    print(f"\nSaved {len(results)} trial records to {output_path}")
    print(json.dumps(runner.summary(), indent=2))


if __name__ == "__main__":
    main()
