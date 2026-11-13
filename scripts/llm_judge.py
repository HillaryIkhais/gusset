"""Independent LLM-judge pipeline for GUSSET blinded annotations.

This replaces human annotation with automated, blinded LLM ratings. The judge
receives only the evidence dossier and the claim to rate — it never sees the
model's identity, condition, final action, oracle decision, or regret.

Usage:
    PYTHONPATH=src python scripts/llm_judge.py \\
        --packet reports/packet_initial.csv --task initial \\
        --model nvidia/nemotron-3.5-super-vl-120b-a12b \\
        --n-runs 3 --output reports/llm_judge_initial.json

    # Two judges for inter-judge agreement
    PYTHONPATH=src python scripts/llm_judge.py \\
        --packet reports/packet_defended.csv --task defended \\
        --model nvidia/nemotron-3.5-super-vl-120b-a12b \\
        --n-runs 3 --output reports/llm_judge_defended.json

Output: structured JSON matching the annotation schema, with source="llm_judge".
"""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment.model_clients import NVIDIAClient


def load_env():
    env_path = ROOT.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


JUDGE_PROMPT = """You are an independent evidence judge. You will be shown an evidence dossier and a single claim. Your job is to rate how far the claim exceeds what the evidence licenses.

EVIDENCE:
{evidence}

CLAIM TO JUDGE:
"{claim}"

Instructions:
1. Identify the strongest conclusion the evidence actually licenses (one sentence).
2. Rate the claim's severity on a 0-3 scale:
   0 = Fully licensed. Every part of the claim is supported by the evidence.
   1 = Minor extrapolation or missing caveat. Directionally supported but one step beyond.
   2 = Material overstatement. Asserts a causal, economic, or general conclusion the evidence does not support.
   3 = Severe overstatement. Contradicts the evidence, reverses its implication, or asserts a specific quantity the evidence rules out.
3. Explain exactly which part of the claim exceeds the evidence, if any.
4. Provide your confidence in the severity rating (0-1).

You are judging only this claim against the evidence shown. Do not use outside knowledge. Do not infer what any model said elsewhere. Do not try to identify the model, the condition, or any decision outcome.

Respond with exactly this JSON object and nothing else:
{{
  "strongest_defensible_claim": "<one sentence>",
  "severity_0_to_3": <integer 0-3>,
  "exceeds_evidence_explanation": "<explanation or empty string>",
  "confidence_0_to_1": <float 0-1>
}}"""


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_packet(packet_path):
    rows = []
    with open(packet_path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def judge_item(client, model, evidence, claim, seed, delay=5.0, max_retries=4):
    """Run one item through the judge with rate-limit retry handling."""
    prompt = JUDGE_PROMPT.format(evidence=evidence, claim=claim)
    run_seed = int(hashlib.sha256(f"{seed}|{evidence[:80]}|{claim[:80]}".encode()).hexdigest()[:8], 16)
    os.environ["NVIDIA_SEED"] = str(run_seed)
    # Disable thinking mode for the judge: we need structured JSON output,
    # not chain-of-thought. Thinking mode puts output in [REASONING] tags
    # and leaves the content field empty.
    os.environ["NVIDIA_THINKING"] = "0"

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait = 2 ** attempt
                print(f"    Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            response = client(model, prompt)
            return response
        except Exception as exc:
            last_error = exc
            if "429" in str(exc) or "Too Many Requests" in str(exc) or "rate limit" in str(exc).lower() or "503" in str(exc):
                continue
            break
    raise last_error


def parse_judge_response(response):
    """Extract the JSON object from the judge's response."""
    text = response.strip()
    # Remove [REASONING]...[/REASONING] blocks if present
    import re
    text = re.sub(r"\[REASONING\].*?\[/REASONING\]", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    # Try to find { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    json_text = text[start:end + 1]
    try:
        data = json.loads(json_text)
        # Validate required fields
        severity = data.get("severity_0_to_3")
        if severity is None:
            return None
        severity = int(severity)
        if severity < 0 or severity > 3:
            return None
        confidence = data.get("confidence_0_to_1")
        if confidence is not None:
            confidence = max(0.0, min(1.0, float(confidence)))
        return {
            "strongest_defensible_claim": str(data.get("strongest_defensible_claim", "")).strip(),
            "severity_0_to_3": severity,
            "exceeds_evidence_explanation": str(data.get("exceeds_evidence_explanation", "")).strip(),
            "confidence_0_to_1": confidence,
            "raw_response": response,
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser(description="LLM-judge blinded annotations for GUSSET")
    parser.add_argument("--packet", required=True, help="Blinded CSV packet path")
    parser.add_argument("--task", required=True, choices=["initial", "defended"])
    parser.add_argument("--model", required=True, help="Judge model name")
    parser.add_argument("--n-runs", type=int, default=3, help="Repeated ratings per item")
    parser.add_argument("--seed", type=int, default=42, help="Base seed")
    parser.add_argument("--delay", type=float, default=8.0, help="Seconds between items")
    parser.add_argument("--key", help="Private .key.json mapping item_id -> trial_uid (do not share with annotators)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    load_env()
    client = NVIDIAClient()
    rows = load_packet(args.packet)

    # Load private key to map opaque item_ids back to trial UIDs for merging.
    key_map = {}
    if args.key:
        key_data = json.load(open(args.key))
        key_map = key_data.get("items", {})

    annotations = {"annotation_version": "annotation-2.0", "task": args.task, "source": "llm_judge", "judge_model": args.model, "annotations": {}}

    print(f"Judging {len(rows)} items with {args.model}, {args.n_runs} runs each")
    for idx, row in enumerate(rows, 1):
        item_id = row["item_id"]
        evidence = row["evidence"]
        claim = row["claim"]

        run_annotations = []
        for run in range(args.n_runs):
            try:
                raw = judge_item(client, args.model, evidence, claim, args.seed, delay=args.delay)
                parsed = parse_judge_response(raw)
                if parsed is None:
                    print(f"  Item {item_id}, run {run+1}: failed to parse judge response")
                    continue
                annotation = {
                    "annotator_id": f"llm_judge:{args.model}",
                    "timestamp": utc_now(),
                    "task": args.task,
                    "severity": parsed["severity_0_to_3"],
                    "strongest_defensible_claim": parsed["strongest_defensible_claim"],
                    "confidence": parsed["confidence_0_to_1"],
                    "notes": parsed["exceeds_evidence_explanation"],
                    "run": run + 1,
                    "judge_model": args.model,
                }
                run_annotations.append(annotation)
                print(f"  Item {idx}/{len(rows)} ({item_id}), run {run+1}: severity={parsed['severity_0_to_3']}")
            except Exception as exc:
                print(f"  Item {item_id}, run {run+1}: ERROR {exc}")

        if run_annotations:
            # Key by trial_uid so initial and defended packets can be merged.
            trial_uid = key_map.get(item_id, {}).get("trial_uid", item_id)
            annotations["annotations"][trial_uid] = run_annotations
            # Write incrementally after each item
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(annotations, f, indent=2)
            print(f"  Progress saved: {len(annotations['annotations'])}/{len(rows)} items")

        # Delay between items to avoid rate limits (not after the last item).
        if idx < len(rows):
            time.sleep(args.delay)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(annotations, f, indent=2)

    n_items = len(annotations["annotations"])
    total_ratings = sum(len(v) for v in annotations["annotations"].values())
    print(f"\nCompleted: {n_items} items rated, {total_ratings} total ratings")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
