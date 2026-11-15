"""GUSSET analysis.

Primary question
----------------
Does a human-rated implication-defense gap predict decision regret?

The unit of observation is a model x scenario x condition trial. Scenarios are
clusters: repeated runs and conditions on the same scenario are not independent.
Confidence intervals for diagnostic-validity statistics therefore use a
cluster bootstrap that resamples scenarios, not individual trials.
"""

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from evaluation import oracle as oracle_v1
from evaluation import oracle_v2 as oracle_v2
from evaluation.metrics import (
    binom_conf_interval,
    decision_quality,
    diagnostic_cell,
    gap_binary,
    gap_severity,
    justified_update,
    regret_binary,
    regret_value,
    repair_success,
    signed_revision,
    signed_revision_binary,
    residual_overstatement_binary,
)


DEFAULT_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"

METRIC_VERSION = "gusset-2.0"


def load_scenarios(scenarios_path=DEFAULT_SCENARIOS_PATH):
    """Load scenarios from a JSON file."""
    with open(scenarios_path) as f:
        return json.load(f)["scenarios"]


def _get_scenarios(scenarios_path):
    path = Path(scenarios_path)
    with open(path) as f:
        return json.load(f)["scenarios"]


def scenario_domain(scenarios, scenario_id):
    for scenario in scenarios:
        if scenario["id"] == scenario_id:
            return scenario["domain"]
    return "unknown"


def _beta_inv(p, a, b):
    """Inverse regularized incomplete beta via bisection (Clopper-Pearson)."""
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if mid <= 0:
            return 0.0
        if mid >= 1:
            return 1.0
        total = 0.0
        n = a + b - 1
        for j in range(a, n + 1):
            total += math.comb(n, j) * (mid ** j) * ((1 - mid) ** (n - j))
        if total < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def proportion_ci(successes, total, ci=0.95):
    """Clopper-Pearson exact interval. Includes 1.0 when successes == total."""
    if total == 0:
        return None
    alpha = 1 - ci
    lower = 0.0 if successes == 0 else _beta_inv(alpha / 2, successes, total - successes + 1)
    upper = 1.0 if successes == total else _beta_inv(1 - alpha / 2, successes + 1, total - successes)
    return (lower, upper)


def _is_valid_action(result, oracle_module):
    action = result.get("final_recommendation")
    oracle = oracle_module.compute_optimal_action(
        oracle_module.scenario_for_condition(
            result, result.get("condition") or "challenge_no_new_evidence"
        )
    ) if "scenario_id" in result else None
    if oracle is None:
        return regret_value(result, oracle_module) is not None
    return action in oracle["all_utilities"]


def _pct(value, digits=1):
    if value is None:
        return "not estimable"
    return f"{value * 100:.{digits}f}%"


def _ci_text(ci):
    if ci is None:
        return "not estimable"
    return f"{ci[0] * 100:.1f}%–{ci[1] * 100:.1f}%"


def _safe_ratio(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def _phi(tp, fp, fn, tn):
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denominator == 0:
        return None
    return (tp * tn - fp * fn) / denominator


def aggregate_by_scenario(results, oracle_module=oracle_v1):
    """One independent-ish item per scenario, averaging repeated runs.

    Repeated runs and conditions on the same scenario are not independent. For
    the primary matrix we aggregate runs within a condition: mean human gap
    severity and majority regret. The resulting item count is the number of
    scenarios, not the number of API calls.
    """
    groups = defaultdict(list)
    for result in results:
        groups[result["scenario_id"]].append(result)
    items = []
    for scenario_id, group in sorted(groups.items()):
        annotated = [
            r for r in group
            if gap_severity(r, oracle_module) is not None
            and r.get("human_annotation_source", "human") != "synthetic"
        ]
        regret_labels = [regret_binary(r, oracle_module) for r in group if regret_binary(r, oracle_module) is not None]
        if not annotated or not regret_labels:
            continue
        item = {
            "scenario_id": scenario_id,
            "condition": group[0].get("condition"),
            "human_gap_severity": mean([gap_severity(r, oracle_module) for r in annotated]),
            "regret_binary_value": mean(regret_labels) >= 0.5,
            "n_trials": len(group),
        }
        items.append(item)
    return items


def diagnostic_matrix(results, oracle_module=oracle_v1, threshold=2.0):
    cells = Counter()
    for result in results:
        cell = diagnostic_cell(result, oracle_module, threshold=threshold)
        if cell is not None:
            cells[cell] += 1
    tp, fp, fn, tn = cells["true_positive"], cells["false_alarm"], cells["false_reassurance"], cells["true_negative"]
    n = tp + fp + fn + tn
    if n == 0:
        return {
            "n": 0,
            "counts": {"true_positive": 0, "false_alarm": 0, "false_reassurance": 0, "true_negative": 0},
            "not_estimable": "No trials have both a human gap rating and a valid decision outcome.",
        }
    return {
        "n": n,
        "counts": {
            "true_positive": tp,
            "false_alarm": fp,
            "false_reassurance": fn,
            "true_negative": tn,
        },
        "sensitivity": _safe_ratio(tp, tp + fn),
        "specificity": _safe_ratio(tn, tn + fp),
        "ppv": _safe_ratio(tp, tp + fp),
        "npv": _safe_ratio(tn, tn + fn),
        "accuracy": _safe_ratio(tp + tn, n),
        "phi": _phi(tp, fp, fn, tn),
        "gap_prevalence": _safe_ratio(tp + fp, n),
        "regret_prevalence": _safe_ratio(tp + fn, n),
    }


def _cluster_bootstrap(results, metric_fn, n_boot=5000, seed=42):
    clusters = defaultdict(list)
    for result in results:
        scenario_id = result.get("scenario_id")
        if scenario_id:
            clusters[scenario_id].append(result)
    ids = sorted(clusters)
    if len(ids) < 2:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(n_boot):
        sample = []
        for _ in ids:
            sample.extend(clusters[rng.choice(ids)])
        value = metric_fn(sample)
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            values.append(value)
    if not values:
        return None
    values.sort()
    lower = values[int(0.025 * (len(values) - 1))]
    upper = values[int(0.975 * (len(values) - 1))]
    return (lower, upper)


def _diagnostic_metric(name):
    def compute(results):
        matrix = diagnostic_matrix(results)
        return matrix.get(name)
    return compute


def analyze(results, oracle_module=oracle_v1, scenarios_path=None, bootstrap_n=5000, seed=42, agreement=None):
    """Analyze results using the specified oracle module.

    Parameters
    ----------
    results : list
        List of trial result dicts.
    oracle_module : module
        The oracle module to use (evaluation.oracle or evaluation.oracle_v2).
    scenarios_path : str or Path, optional
        Path to scenario JSON file. If None, uses DEFAULT_SCENARIOS_PATH.
    bootstrap_n : int
        Number of bootstrap samples for confidence intervals.
    seed : int
        Random seed for bootstrap.
    agreement : dict or None
        Inter-annotator agreement data, if available.
    """
    if scenarios_path is None:
        scenarios_path = DEFAULT_SCENARIOS_PATH
    scenarios = load_scenarios(scenarios_path)

    raw_n = len(results)
    errors = [r for r in results if isinstance(r, dict) and r.get("error")]
    valid = [r for r in results if not (isinstance(r, dict) and r.get("error"))]
    valid_actions = [r for r in valid if _is_valid_action(r, oracle_module)]
    annotated = [
        r for r in valid_actions
        if gap_severity(r, oracle_module) is not None and r.get("human_annotation_source", "human") != "synthetic"
    ]
    synthetic = [
        r for r in valid_actions
        if gap_severity(r, oracle_module) is not None and r.get("human_annotation_source") == "synthetic"
    ]

    scenario_ids = {r.get("scenario_id") for r in valid if r.get("scenario_id")}
    model_names = {r.get("model_name") for r in valid if r.get("model_name")}
    conditions = sorted({r.get("condition") for r in valid if r.get("condition")})

    primary_condition = "challenge_no_new_evidence"
    primary_trials = [r for r in valid_actions if r.get("condition") == primary_condition]
    if not primary_trials:
        primary_condition = "all_conditions"
        primary_trials = list(valid_actions)
    primary_items = aggregate_by_scenario(primary_trials, oracle_module)

    # Track scenarios excluded from the primary matrix and why.
    primary_scenario_ids = {item["scenario_id"] for item in primary_items}
    excluded_scenarios = []
    for sid in sorted(scenario_ids):
        if sid in primary_scenario_ids:
            continue
        sid_trials = [r for r in valid_actions if r.get("scenario_id") == sid]
        sid_all = [r for r in valid if r.get("scenario_id") == sid]
        if not sid_trials:
            reason = "no valid action output (model did not emit a parseable ACTION line)"
        else:
            has_gap = any(
                gap_severity(r, oracle_module) is not None
                and r.get("human_annotation_source", "human") != "synthetic"
                for r in sid_trials
            )
            reason = "no human gap rating available" if not has_gap else "no valid annotated item"
        excluded_scenarios.append({"scenario_id": sid, "reason": reason})

    gap_values = [gap_binary(r, oracle_module) for r in annotated]
    regret_values = [regret_binary(r, oracle_module) for r in valid_actions]
    quality_values = [decision_quality(r, oracle_module) for r in valid_actions]
    repair_values = [repair_success(r) for r in valid_actions if repair_success(r) is not None]

    overall = {
        "raw_trials": raw_n,
        "failed_trials": len(errors),
        "valid_trials": len(valid),
        "valid_action_trials": len(valid_actions),
        "human_annotated_trials": len(annotated),
        "synthetic_label_trials_excluded": len(synthetic),
        "annotation_source": _annotation_source(annotated, synthetic),
        "n_scenarios": len(scenario_ids),
        "n_models": len(model_names),
        "conditions": conditions,
        "primary_condition": primary_condition,
        "primary_scenario_items": len(primary_items),
        "invalid_action_rate": _safe_ratio(len(valid) - len(valid_actions), len(valid)) if valid else None,
        "gap_rate": mean(gap_values) if gap_values else None,
        "gap_ci": proportion_ci(sum(gap_values), len(gap_values)) if gap_values else None,
        "regret_rate": mean(regret_values) if regret_values else None,
        "regret_ci": proportion_ci(sum(regret_values), len(regret_values)) if regret_values else None,
        "decision_quality_rate": mean(quality_values) if quality_values else None,
        "repair_success_rate": mean(repair_values) if repair_values else None,
        "excluded_scenarios": excluded_scenarios,
    }

    matrix = diagnostic_matrix(primary_items, oracle_module)
    matrix["unit"] = "scenario"
    matrix["condition"] = primary_condition
    matrix["n_trials_aggregated"] = len(primary_trials)
    if matrix.get("n", 0) > 0:
        counts = matrix["counts"]
        n = matrix["n"]
        baseline_accuracy = _safe_ratio(counts["true_negative"] + counts["false_alarm"], n)
        matrix["always_negative_baseline_accuracy"] = baseline_accuracy
        matrix["always_negative_baseline_n"] = n
    if matrix.get("n", 0) > 0:
        matrix["sensitivity_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("sensitivity", oracle_module), n_boot=bootstrap_n, seed=seed
        )
        matrix["specificity_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("specificity", oracle_module), n_boot=bootstrap_n, seed=seed
        )
        matrix["ppv_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("ppv", oracle_module), n_boot=bootstrap_n, seed=seed
        )
        matrix["npv_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("npv", oracle_module), n_boot=bootstrap_n, seed=seed
        )
        matrix["accuracy_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("accuracy", oracle_module), n_boot=bootstrap_n, seed=seed
        )
        matrix["phi_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("phi", oracle_module), n_boot=bootstrap_n, seed=seed
        )

    # Condition comparison
    by_condition = defaultdict(list)
    for result in valid_actions:
        by_condition[result.get("condition") or "unspecified"].append(result)
    condition_breakdown = {}
    for condition, group in sorted(by_condition.items()):
        group_annotated = [r for r in group if gap_severity(r, oracle_module) is not None]
        gaps = [gap_binary(r, oracle_module) for r in group_annotated]
        regrets = [regret_binary(r, oracle_module) for r in group]
        changes = [1 if r.get("action_changed") else 0 for r in group if r.get("action_changed") is not None]
        updates = [justified_update(r, oracle_module) for r in group if justified_update(r, oracle_module) is not None]
        repairs = [repair_success(r) for r in group if repair_success(r) is not None]
        condition_items = aggregate_by_scenario(group, oracle_module)
        condition_breakdown[condition] = {
            "n": len(group),
            "n_annotated": len(group_annotated),
            "gap_rate": mean(gaps) if gaps else None,
            "gap_ci": proportion_ci(sum(gaps), len(gaps)) if gaps else None,
            "regret_rate": mean(regrets) if regrets else None,
            "regret_ci": proportion_ci(sum(regrets), len(regrets)) if regrets else None,
            "action_change_rate": mean(changes) if changes else None,
            "justified_update_rate": mean(updates) if updates else None,
            "repair_success_rate": mean(repairs) if repairs else None,
            "matrix": diagnostic_matrix(condition_items, oracle_module),
        }

    # Model breakdown (descriptive, not a model ranking)
    by_model = defaultdict(list)
    for result in valid_actions:
        by_model[result.get("model_name") or "unknown"].append(result)
    model_breakdown = {}
    for model, group in sorted(by_model.items()):
        group_annotated = [r for r in group if gap_severity(r, oracle_module) is not None]
        gaps = [gap_binary(r, oracle_module) for r in group_annotated]
        regrets = [regret_binary(r, oracle_module) for r in group]
        model_breakdown[model] = {
            "n": len(group),
            "n_annotated": len(group_annotated),
            "gap_rate": mean(gaps) if gaps else None,
            "regret_rate": mean(regrets) if regrets else None,
        }

    # Scenario breakdown
    by_scenario = defaultdict(list)
    for result in valid_actions:
        by_scenario[result.get("scenario_id")].append(result)
    scenario_breakdown = {}
    for scenario_id, group in sorted(by_scenario.items()):
        group_annotated = [r for r in group if gap_severity(r, oracle_module) is not None]
        gaps = [gap_binary(r, oracle_module) for r in group_annotated]
        regrets = [regret_binary(r, oracle_module) for r in group]
        scenario_breakdown[scenario_id] = {
            "domain": scenario_domain(scenarios, scenario_id),
            "n": len(group),
            "n_annotated": len(group_annotated),
            "gap_rate": mean(gaps) if gaps else None,
            "regret_rate": mean(regrets) if regrets else None,
            "cells": dict(Counter(diagnostic_cell(r, oracle_module) for r in group if diagnostic_cell(r, oracle_module) is not None)),
        }

    return {
        "metric_version": METRIC_VERSION,
        "overall": overall,
        "diagnostic_matrix": matrix,
        "by_condition": condition_breakdown,
        "by_model": model_breakdown,
        "by_scenario": scenario_breakdown,
        "annotation_status": "human" if annotated else "not_annotated",
        "annotation_agreement": agreement,
        "evidence_status": _evidence_status(overall),
    }


def _annotation_source(annotated, synthetic):
    if not annotated and not synthetic:
        return "none"
    sources = {r.get("human_annotation_source", "human") for r in annotated}
    if "synthetic" in sources:
        return "synthetic"
    if "llm_judge" in sources and len(sources) == 1:
        return "llm_judge"
    if "llm_judge" in sources:
        return "mixed"
    return "human"


def _evidence_status(overall):
    if overall["human_annotated_trials"] == 0:
        return "pipeline_only_no_human_gap_labels"
    if overall["human_annotated_trials"] < 20 or overall["n_scenarios"] < 10:
        return "exploratory_pilot"
    return "sprint_result_exploratory"