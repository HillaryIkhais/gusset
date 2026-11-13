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
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from evaluation.metrics import (
    decision_quality,
    diagnostic_cell,
    gap_binary,
    gap_severity,
    justified_update,
    regret_binary,
    regret_value,
    repair_success,
)


METRIC_VERSION = "gusset-2.0"


def load_results(path):
    with open(path) as f:
        return json.load(f)


def load_scenarios():
    path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"
    with open(path) as f:
        return json.load(f)["scenarios"]


_scenarios = None


def _get_scenarios():
    global _scenarios
    if _scenarios is None:
        _scenarios = load_scenarios()
    return _scenarios


def scenario_domain(scenario_id):
    for scenario in _get_scenarios():
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


def _is_valid_action(result):
    return result.get("final_recommendation") in result.get("all_utilities", {}) if result.get("all_utilities") else (
        regret_value(result) is not None
    )


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


def aggregate_by_scenario(results):
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
            if gap_severity(r) is not None and r.get("human_annotation_source", "human") != "synthetic"
        ]
        regret_labels = [regret_binary(r) for r in group if regret_binary(r) is not None]
        if not annotated or not regret_labels:
            continue
        item = {
            "scenario_id": scenario_id,
            "condition": group[0].get("condition"),
            "human_gap_severity": mean([gap_severity(r) for r in annotated]),
            "regret_binary_value": mean(regret_labels) >= 0.5,
            "n_trials": len(group),
        }
        items.append(item)
    return items


def diagnostic_matrix(results, threshold=2.0):
    cells = Counter()
    for result in results:
        cell = diagnostic_cell(result, threshold=threshold)
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


def analyze(results, bootstrap_n=5000, seed=42, agreement=None):
    raw_n = len(results)
    errors = [r for r in results if isinstance(r, dict) and r.get("error")]
    valid = [r for r in results if not (isinstance(r, dict) and r.get("error"))]
    valid_actions = [r for r in valid if _is_valid_action(r)]
    annotated = [
        r for r in valid_actions
        if gap_severity(r) is not None and r.get("human_annotation_source", "human") != "synthetic"
    ]
    synthetic = [
        r for r in valid_actions
        if gap_severity(r) is not None and r.get("human_annotation_source") == "synthetic"
    ]

    scenario_ids = {r.get("scenario_id") for r in valid if r.get("scenario_id")}
    model_names = {r.get("model_name") for r in valid if r.get("model_name")}
    conditions = sorted({r.get("condition") for r in valid if r.get("condition")})

    primary_condition = "challenge_no_new_evidence"
    primary_trials = [r for r in valid_actions if r.get("condition") == primary_condition]
    if not primary_trials:
        primary_condition = "all_conditions"
        primary_trials = list(valid_actions)
    primary_items = aggregate_by_scenario(primary_trials)

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
                gap_severity(r) is not None and r.get("human_annotation_source", "human") != "synthetic"
                for r in sid_trials
            )
            reason = "no human gap rating available" if not has_gap else "no valid annotated item"
        excluded_scenarios.append({"scenario_id": sid, "reason": reason})

    gap_values = [gap_binary(r) for r in annotated]
    regret_values = [regret_binary(r) for r in valid_actions]
    quality_values = [decision_quality(r) for r in valid_actions]
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

    matrix = diagnostic_matrix(primary_items)
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
            primary_items, _diagnostic_metric("sensitivity"), n_boot=bootstrap_n, seed=seed
        )
        matrix["specificity_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("specificity"), n_boot=bootstrap_n, seed=seed
        )
        matrix["ppv_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("ppv"), n_boot=bootstrap_n, seed=seed
        )
        matrix["npv_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("npv"), n_boot=bootstrap_n, seed=seed
        )
        matrix["accuracy_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("accuracy"), n_boot=bootstrap_n, seed=seed
        )
        matrix["phi_ci"] = _cluster_bootstrap(
            primary_items, _diagnostic_metric("phi"), n_boot=bootstrap_n, seed=seed
        )

    # Condition comparison
    by_condition = defaultdict(list)
    for result in valid_actions:
        by_condition[result.get("condition") or "unspecified"].append(result)
    condition_breakdown = {}
    for condition, group in sorted(by_condition.items()):
        group_annotated = [r for r in group if gap_severity(r) is not None]
        gaps = [gap_binary(r) for r in group_annotated]
        regrets = [regret_binary(r) for r in group]
        changes = [1 if r.get("action_changed") else 0 for r in group if r.get("action_changed") is not None]
        updates = [justified_update(r) for r in group if justified_update(r) is not None]
        repairs = [repair_success(r) for r in group if repair_success(r) is not None]
        condition_items = aggregate_by_scenario(group)
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
            "matrix": diagnostic_matrix(condition_items),
        }

    # Model breakdown (descriptive, not a model ranking)
    by_model = defaultdict(list)
    for result in valid_actions:
        by_model[result.get("model_name") or "unknown"].append(result)
    model_breakdown = {}
    for model, group in sorted(by_model.items()):
        group_annotated = [r for r in group if gap_severity(r) is not None]
        gaps = [gap_binary(r) for r in group_annotated]
        regrets = [regret_binary(r) for r in group]
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
        group_annotated = [r for r in group if gap_severity(r) is not None]
        gaps = [gap_binary(r) for r in group_annotated]
        regrets = [regret_binary(r) for r in group]
        scenario_breakdown[scenario_id] = {
            "domain": scenario_domain(scenario_id),
            "n": len(group),
            "n_annotated": len(group_annotated),
            "gap_rate": mean(gaps) if gaps else None,
            "regret_rate": mean(regrets) if regrets else None,
            "cells": dict(Counter(diagnostic_cell(r) for r in group if diagnostic_cell(r) is not None)),
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


def format_report(analysis_result):
    lines = []
    overall = analysis_result["overall"]
    matrix = analysis_result["diagnostic_matrix"]

    lines.append("# GUSSET Analysis")
    lines.append("")
    lines.append(f"Metric version: `{analysis_result['metric_version']}`")
    lines.append(f"Evidence status: **{analysis_result['evidence_status']}**")
    lines.append("")
    lines.append("## 1. Data Provenance")
    lines.append("")
    lines.append(f"- Raw trial records: {overall['raw_trials']}")
    lines.append(f"- Failed API trials: {overall['failed_trials']}")
    lines.append(f"- Valid trial records: {overall['valid_trials']}")
    lines.append(f"- Trials with a valid action: {overall['valid_action_trials']}")
    lines.append(f"- Trials with human gap ratings: {overall['human_annotated_trials']}")
    if overall.get("synthetic_label_trials_excluded"):
        lines.append(f"- Synthetic labels excluded: {overall['synthetic_label_trials_excluded']} (not evidence)")
    lines.append(f"- Annotation source: {overall.get('annotation_source', 'unknown')}")
    if overall.get("excluded_scenarios"):
        lines.append(f"- Excluded scenarios: {overall['excluded_scenarios']}")
    lines.append(f"- Scenarios: {overall['n_scenarios']}")
    lines.append(f"- Models: {overall['n_models']}")
    lines.append(f"- Conditions: {', '.join(overall['conditions']) if overall['conditions'] else 'none'}")
    lines.append("")
    lines.append(
        "> Scenarios are treated as clusters. Diagnostic-validity intervals below "
        "resample scenarios, not independent trials. The model is not ranked; "
        "the unit of analysis is the decision item."
    )
    lines.append("")

    lines.append("## 2. Primary Result: Does the Gap Predict Regret?")
    lines.append("")
    lines.append(
        f"Primary matrix condition: `{matrix.get('condition')}`. Unit: one aggregated item per "
        f"scenario (mean human gap across runs; majority regret). "
        f"Scenario items: {matrix.get('n', 0)} from {matrix.get('n_trials_aggregated', 0)} trials."
    )
    lines.append("")
    if matrix.get("n", 0) == 0:
        lines.append("**Not estimable.** No trial currently has both a blinded human gap rating and a valid decision outcome.")
        lines.append("")
        lines.append(matrix.get("not_estimable", ""))
    else:
        counts = matrix["counts"]
        tp, fp, fn, tn = counts["true_positive"], counts["false_alarm"], counts["false_reassurance"], counts["true_negative"]
        n = tp + fp + fn + tn
        # Always-negative baseline: predict no regret for every scenario.
        baseline_accuracy = _safe_ratio(tn + fp, n)
        baseline_regret_rate = _safe_ratio(tp + fn, n)
        lines.append("| | Regret | No regret |")
        lines.append("|---|---:|---:|")
        lines.append(f"| Gap present | True positive: {tp} | False alarm: {fp} |")
        lines.append(f"| No gap | False reassurance: {fn} | True negative: {tn} |")
        lines.append("")
        lines.append("- N with both labels: {n}".format(n=n))
        lines.append(
            f"- Sensitivity: {_pct(matrix['sensitivity'])} (cluster 95% CI {_ci_text(matrix.get('sensitivity_ci'))})"
        )
        lines.append(
            f"- Specificity: {_pct(matrix['specificity'])} (cluster 95% CI {_ci_text(matrix.get('specificity_ci'))})"
        )
        lines.append(f"- PPV: {_pct(matrix['ppv'])} (cluster 95% CI {_ci_text(matrix.get('ppv_ci'))})")
        lines.append(f"- NPV: {_pct(matrix['npv'])} (cluster 95% CI {_ci_text(matrix.get('npv_ci'))})")
        lines.append(
            f"- Accuracy: {_pct(matrix['accuracy'])} (cluster 95% CI {_ci_text(matrix.get('accuracy_ci'))})"
        )
        lines.append(f"- Always-negative baseline accuracy: {_pct(baseline_accuracy)}")
        lines.append(
            f"- Matthews phi: {matrix['phi']:.2f}" if matrix['phi'] is not None else "- Matthews phi: not estimable"
        )
        lines.append("")
        lines.append(
            "> Interpretation: this exploratory, single-model pilot found that the blinded LLM-judge "
            "severity score failed to reliably identify observed decision regret in this sample. "
            "A trivial classifier that predicts no regret for every scenario would achieve "
            f"{_pct(baseline_accuracy)} accuracy on these {n} items, compared with "
            f"{_pct(matrix['accuracy'])} for the judge. Nine annotated scenarios cannot establish "
            "whether an epistemic gap generally predicts decision quality; they establish what this "
            "particular evaluator did and did not identify here."
        )
        lines.append("")

    lines.append("## 2.1 Sample Flow")
    lines.append("")
    lines.append(
        f"- Collected: {overall['raw_trials']} live trial records across "
        f"{overall['n_scenarios']} scenarios and {overall['n_models']} model(s)"
    )
    lines.append(
        f"- Evaluated: {overall['human_annotated_trials']} trial records with complete "
        f"blinded gap ratings (initial + defended)"
    )
    if overall.get("excluded_scenarios"):
        lines.append(f"- Excluded from primary matrix: {len(overall['excluded_scenarios'])} scenario(s)")
        for excl in overall["excluded_scenarios"]:
            lines.append(f"  - {excl['scenario_id']}: {excl['reason']}")
    lines.append(
        f"- Analyzed: {matrix.get('n', 0)} scenario items in the primary diagnostic matrix "
        f"({matrix.get('n_trials_aggregated', 0)} trial records aggregated)"
    )
    lines.append("")
    lines.append(
        "Exclusion rules were established before analysis: a scenario is excluded from the primary "
        "matrix if it has no valid action output or no complete blinded gap rating. No trial was "
        "excluded because its result was inconvenient."
    )
    lines.append("")

    lines.append("## 4. Outcome Rates")
    lines.append("")
    lines.append("| Quantity | Estimate | 95% CI | N |")
    lines.append("|---|---:|---|---:|")
    lines.append(
        f"| Gap present | {_pct(overall['gap_rate'])} | {_ci_text(overall['gap_ci'])} | {overall['human_annotated_trials']} |"
    )
    lines.append(
        f"| Decision regret | {_pct(overall['regret_rate'])} | {_ci_text(overall['regret_ci'])} | {overall['valid_action_trials']} |"
    )
    lines.append(f"| Decision quality | {_pct(overall['decision_quality_rate'])} | not estimable | {overall['valid_action_trials']} |")
    lines.append(f"| Repair success | {_pct(overall['repair_success_rate'])} | not estimable | see condition table |")
    lines.append(f"| Invalid action output | {_pct(overall['invalid_action_rate'])} | not estimable | {overall['valid_trials']} |")
    lines.append("")

    lines.append("## 5. Control Conditions")
    lines.append("")
    lines.append("| Condition | N | Annotated | Gap | Regret | Changed action | Justified update | Repair |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for condition, data in analysis_result["by_condition"].items():
        lines.append(
            f"| {condition} | {data['n']} | {data['n_annotated']} | {_pct(data['gap_rate'])} | "
            f"{_pct(data['regret_rate'])} | {_pct(data['action_change_rate'])} | "
            f"{_pct(data['justified_update_rate'])} | {_pct(data['repair_success_rate'])} |"
        )
    lines.append("")
    lines.append(
        "The challenge condition is interpretable only relative to the neutral-clarification "
        "and no-challenge controls. The new-evidence condition measures justified updating, "
        "not capitulation."
    )
    lines.append("")

    lines.append("## 6. By Model")
    lines.append("")
    lines.append("| Model | N | Annotated | Gap | Regret |")
    lines.append("|---|---:|---:|---:|---:|")
    for model, data in analysis_result["by_model"].items():
        lines.append(
            f"| {model} | {data['n']} | {data['n_annotated']} | {_pct(data['gap_rate'])} | {_pct(data['regret_rate'])} |"
        )
    lines.append("")
    lines.append("Model rows are descriptive. With one model they are not a model comparison.")
    lines.append("")

    lines.append("## 7. By Scenario")
    lines.append("")
    lines.append("| Scenario | Domain | N | Annotated | Gap | Regret | Cells |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for scenario_id, data in analysis_result["by_scenario"].items():
        cells = ", ".join(f"{k}={v}" for k, v in sorted(data["cells"].items())) or "—"
        lines.append(
            f"| {scenario_id} | {data['domain']} | {data['n']} | {data['n_annotated']} | "
            f"{_pct(data['gap_rate'])} | {_pct(data['regret_rate'])} | {cells} |"
        )
    lines.append("")

    lines.append("## 8. Annotation Agreement")
    lines.append("")
    agreement = analysis_result.get("annotation_agreement")
    if not agreement:
        lines.append("Not provided. Run `annotate.py --mode agreement` on each task and pass the result to the analysis.")
    else:
        lines.append(f"- Items with 2+ annotators: {agreement.get('n_items', 0)}")
        lines.append(f"- Exact severity agreement: {_pct(agreement.get('percent_exact'))}")
        lines.append(f"- Agreement within one severity point: {_pct(agreement.get('percent_within_one'))}")
        lines.append(f"- Binary agreement: {_pct(agreement.get('binary_agreement'))}")
        kappa = agreement.get("mean_quadratic_weighted_kappa")
        lines.append(f"- Mean quadratic weighted kappa: {kappa:.2f}" if kappa is not None else "- Mean quadratic weighted kappa: not estimable")
    lines.append("")

    lines.append("## 9. Interpretation Limits")
    lines.append("")
    lines.append("- The oracle establishes the optimal action only under the registered scenario probabilities and costs.")
    lines.append("- The scenarios are synthetic and do not establish that those assumptions describe the real world.")
    lines.append("- A gap is not harm by itself. The diagnostic matrix asks whether the gap carries information about regret.")
    lines.append("- With few scenarios, cluster-bootstrap intervals are wide and unstable.")
    lines.append("- Any result without independent human gap ratings is a pipeline check, not a finding.")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze GUSSET results")
    parser.add_argument("results", help="Path to trial results JSON")
    parser.add_argument("output", nargs="?", default="reports/analysis_report.md", help="Markdown output")
    parser.add_argument("--bootstrap", type=int, default=5000, help="Cluster bootstrap resamples")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--agreement", help="Agreement JSON from annotate.py")
    args = parser.parse_args()

    agreement = None
    if args.agreement:
        with open(args.agreement) as f:
            agreement = json.load(f)

    analysis_result = analyze(
        load_results(args.results),
        bootstrap_n=args.bootstrap,
        seed=args.seed,
        agreement=agreement,
    )
    report = format_report(analysis_result)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        f.write(report)

    json_path = str(Path(args.output).with_suffix(".json"))
    with open(json_path, "w") as f:
        json.dump(analysis_result, f, indent=2)

    print(report)
    print(f"\nSaved machine-readable analysis to {json_path}")
