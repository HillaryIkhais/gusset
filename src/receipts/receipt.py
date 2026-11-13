"""GUSSET Decision Receipt.

A receipt is a self-contained record of one trial:

- the registered scenario and its hash;
- every prompt and response, with per-phase and combined hashes;
- the model's initial, defended, final, and post-contract commitments;
- the blinded human gap rating, if one exists;
- the expected utility of every action and the resulting regret;
- a receipt hash covering the whole record.

Hashes establish integrity, not authenticity. A receipt can be internally
consistent and still describe a run that never happened. The verifier therefore
also recomputes the oracle from the registered scenario rather than trusting the
stored utility values.
"""

import hashlib
import json
from datetime import datetime, timezone

from evaluation.oracle import compute_optimal_action, expected_utility, scenario_for_condition


RECEIPT_VERSION = "gusset-receipt-1.0"
METRIC_VERSION = "gusset-2.0"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def _phase_record(prompt, response):
    return {
        "prompt": prompt,
        "response": response,
        "prompt_hash": sha256_obj(prompt) if prompt is not None else None,
        "response_hash": sha256_obj(response) if response is not None else None,
    }


def build_receipt(result, scenario):
    condition = result.get("condition") or "challenge_no_new_evidence"
    scenario_used = scenario_for_condition(scenario, condition)
    oracle = compute_optimal_action(scenario_used)

    transcript_phases = {
        "phase1_initial": _phase_record(result.get("phase1_prompt"), result.get("phase1_raw_response")),
        "phase2_condition": _phase_record(result.get("phase2_prompt"), result.get("phase2_raw_response")),
        "phase3_final": _phase_record(result.get("phase3_prompt"), result.get("phase3_raw_response")),
        "phase4_contract": _phase_record(result.get("phase4_prompt"), result.get("phase4_raw_response")),
    }
    transcript_hash = sha256_obj(
        {name: {"prompt_hash": rec["prompt_hash"], "response_hash": rec["response_hash"]} for name, rec in transcript_phases.items()}
    )

    final_action = result.get("final_recommendation")
    recommended_utility = oracle["all_utilities"].get(final_action) if final_action in oracle["all_utilities"] else None
    regret = oracle["utility"] - recommended_utility if recommended_utility is not None else None

    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "metric_version": METRIC_VERSION,
        "generated_at": utc_now(),
        "trial_uid": result.get("trial_uid"),
        "run_id": result.get("run_id"),
        "run_number": result.get("run_number"),
        "timestamp": result.get("timestamp"),
        "model": result.get("model_name"),
        "provider": result.get("provider"),
        "condition": condition,
        "scenario": scenario_used,
        "scenario_hash": sha256_obj(scenario_used),
        "transcript": {
            "phases": transcript_phases,
            "transcript_hash": transcript_hash,
        },
        "commitment": {
            "initial_action": result.get("initial_recommendation"),
            "initial_claim": result.get("initial_claim"),
            "initial_confidence": result.get("initial_confidence"),
            "initial_action_valid": result.get("initial_action_valid"),
            "defended_claim": result.get("defended_claim"),
            "final_action": final_action,
            "final_confidence": result.get("final_confidence"),
            "final_action_valid": result.get("final_action_valid"),
            "post_contract_action": result.get("post_contract_recommendation"),
            "post_contract_confidence": result.get("post_contract_confidence"),
            "post_contract_action_valid": result.get("post_contract_action_valid"),
        },
        "human_assessment": {
            "initial_overstatement": result.get("human_initial_overstatement"),
            "defended_overstatement": result.get("human_defended_overstatement"),
            "gap_severity": result.get("human_gap_severity"),
            "gap_binary": result.get("human_gap_binary"),
            "n_annotators": result.get("human_n_annotators"),
            "initial_disagreement": result.get("human_initial_disagreement"),
            "defended_disagreement": result.get("human_defended_disagreement"),
            "source": result.get("human_annotation_source"),
        },
        "decision": {
            "utilities": oracle["all_utilities"],
            "recommended_action": final_action,
            "recommended_utility": recommended_utility,
            "oracle_action": oracle["action"],
            "oracle_utility": oracle["utility"],
            "regret": regret,
            "optimal": bool(final_action == oracle["action"]) if final_action else None,
        },
        "verification": {
            "oracle_recomputed_from_scenario": True,
            "receipt_hash": None,
        },
    }
    receipt["verification"]["receipt_hash"] = receipt_hash(receipt)
    return receipt


def receipt_hash(receipt):
    copy = json.loads(json.dumps(receipt))
    copy.setdefault("verification", {})["receipt_hash"] = None
    return sha256_obj(copy)


def verify_receipt(receipt, registered_scenarios=None):
    """Recompute the receipt from its own scenario and report every mismatch."""
    reasons = []
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            reasons.append(f"{name}: {detail}" if detail else name)

    check("receipt_version", receipt.get("receipt_version") == RECEIPT_VERSION, receipt.get("receipt_version"))
    scenario = receipt.get("scenario")
    if not scenario:
        return {"ok": False, "checks": checks, "reasons": ["missing scenario"]}

    scenario_hash = sha256_obj(scenario)
    check("scenario_hash", scenario_hash == receipt.get("scenario_hash"), "embedded scenario changed")

    if registered_scenarios is not None:
        original = registered_scenarios.get(scenario.get("id"))
        if original is None:
            check("registered_scenario", False, "scenario id not registered")
        else:
            condition = receipt.get("condition") or "challenge_no_new_evidence"
            expected = scenario_for_condition(original, condition)
            check(
                "registered_scenario",
                sha256_obj(expected) == scenario_hash,
                "receipt scenario does not match the registered scenario for this condition",
            )

    phases = receipt.get("transcript", {}).get("phases", {})
    transcript_hash = sha256_obj(
        {name: {"prompt_hash": rec.get("prompt_hash"), "response_hash": rec.get("response_hash")} for name, rec in phases.items()}
    )
    check(
        "transcript_hash",
        transcript_hash == receipt.get("transcript", {}).get("transcript_hash"),
        "prompt or response changed",
    )
    for name, rec in phases.items():
        if rec.get("prompt") is not None:
            check(f"{name}_prompt_hash", sha256_obj(rec["prompt"]) == rec.get("prompt_hash"), "prompt hash mismatch")
        if rec.get("response") is not None:
            check(f"{name}_response_hash", sha256_obj(rec["response"]) == rec.get("response_hash"), "response hash mismatch")

    oracle = compute_optimal_action(scenario)
    stored_utilities = receipt.get("decision", {}).get("utilities", {})
    all_actions = [a["id"] for a in scenario.get("actions", [])]
    for action in all_actions:
        recomputed, _ = expected_utility(action, scenario)
        stored = stored_utilities.get(action)
        check(
            f"utility_{action}",
            stored is not None and abs(float(stored) - float(recomputed)) <= 1e-6,
            f"stored={stored} recomputed={recomputed}",
        )
    check(
        "oracle_action",
        receipt.get("decision", {}).get("oracle_action") == oracle["action"],
        f"stored={receipt.get('decision', {}).get('oracle_action')} recomputed={oracle['action']}",
    )
    check(
        "oracle_utility",
        abs(float(receipt.get("decision", {}).get("oracle_utility", 0)) - float(oracle["utility"])) <= 1e-6,
        "oracle utility mismatch",
    )

    final_action = receipt.get("decision", {}).get("recommended_action")
    recommended = oracle["all_utilities"].get(final_action)
    stored_recommended = receipt.get("decision", {}).get("recommended_utility")
    check(
        "recommended_utility",
        (recommended is None and stored_recommended is None)
        or (recommended is not None and stored_recommended is not None and abs(float(recommended) - float(stored_recommended)) <= 1e-6),
        f"stored={stored_recommended} recomputed={recommended}",
    )
    stored_regret = receipt.get("decision", {}).get("regret")
    recomputed_regret = oracle["utility"] - recommended if recommended is not None else None
    check(
        "regret",
        (recomputed_regret is None and stored_regret is None)
        or (recomputed_regret is not None and stored_regret is not None and abs(float(recomputed_regret) - float(stored_regret)) <= 1e-6),
        f"stored={stored_regret} recomputed={recomputed_regret}",
    )

    check(
        "receipt_hash",
        receipt_hash(receipt) == receipt.get("verification", {}).get("receipt_hash"),
        "receipt contents changed",
    )

    return {"ok": all(c["ok"] for c in checks), "checks": checks, "reasons": reasons}
