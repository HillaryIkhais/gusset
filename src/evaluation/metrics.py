"""GUSSET metrics.

Primary quantities
------------------
gap_severity
    0-3 human rating of how far the initial claim exceeds what the evidence
    licenses, minus the same rating for the defended claim. The second rating
    is collected in a separate blinded task, so the annotator does not see the
    model's challenged response while judging the initial claim.
gap_binary
    ``gap_severity >= 2``. The threshold is registered before annotation.
regret
    Oracle expected utility of the best action minus the expected utility of
    the model's final action, under the condition-specific scenario.
diagnostic cell
    Cross-tabulation of gap_binary and regret_binary:
    true positive, false alarm, false reassurance, true negative.

Machine self-reports (``ACKNOWLEDGEMENT: yes``) are never used as the primary
gap measure. They are retained only as raw transcript data.

Uncertainty quantification
--------------------------
Binomial proportion confidence intervals use the exact Clopper-Pearson
method. With small denominators (e.g., n=1), intervals are necessarily wide.
This uncertainty must be reported alongside every proportion; percentages
alone are misleading.
"""

import json
from pathlib import Path

from evaluation import oracle as oracle_v1
from evaluation import oracle_v2

# Backward-compatible module-level names
compute_optimal_action = oracle_v1.compute_optimal_action
expected_utility = oracle_v1.expected_utility
scenario_for_condition = oracle_v1.scenario_for_condition


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------

DEFAULT_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"

_scenario_cache = {}


def load_scenarios(scenarios_path=DEFAULT_SCENARIOS_PATH):
    """Load scenarios from a JSON file. Caches results by path."""
    key = str(Path(scenarios_path).resolve())
    if key not in _scenario_cache:
        with open(key) as f:
            _scenario_cache[key] = json.load(f)["scenarios"]
    return _scenario_cache[key]


def clear_scenario_cache():
    """Drop cached scenario files. Used by tests that write temporary datasets."""
    _scenario_cache.clear()


def _get_attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# ---------------------------------------------------------------------------
# Scenario lookup
# ---------------------------------------------------------------------------

def _scenario_lookup(scenario_id, scenarios):
    for scenario in scenarios:
        if scenario["id"] == scenario_id:
            return scenario
    return None


def _result_scenarios_path(result):
    """Scenario file recorded on a trial result, if any.

    v2 trial records carry ``scenario_file`` (written by the runner). Earlier
    code also accepted ``_scenarios_path``. Explicit arguments always win over
    this recorded value.
    """
    return _get_attr(result, "_scenarios_path") or _get_attr(result, "scenario_file")


def scenario_for_result(result, oracle_module=oracle_v1, scenarios_path=None):
    """Return the registered scenario for a result, using the appropriate oracle module.

    ``scenarios_path`` selects the dataset. When omitted, the path recorded on
    the result is used so a v2 trial is never silently evaluated against v1
    parameters. Only if neither is present do we fall back to the v1 file.
    """
    scenario_id = _get_attr(result, "scenario_id")
    condition = _get_attr(result, "condition") or "challenge_no_new_evidence"
    if scenarios_path is None:
        scenarios_path = _result_scenarios_path(result)
    if scenarios_path is None:
        scenarios_path = DEFAULT_SCENARIOS_PATH
    scenarios = load_scenarios(scenarios_path)
    scenario = _scenario_lookup(scenario_id, scenarios)
    if scenario is None:
        return None
    return oracle_module.scenario_for_condition(scenario, condition)


def oracle_for_result(result, oracle_module=oracle_v1, scenarios_path=None):
    """Return the deterministic oracle for a result, using the appropriate module."""
    scenario = scenario_for_result(result, oracle_module, scenarios_path=scenarios_path)
    if scenario is None:
        return None
    return oracle_module.compute_optimal_action(scenario)


# ---------------------------------------------------------------------------
# Gap metrics
# ---------------------------------------------------------------------------

def gap_severity(result):
    """Human-rated implication-defense gap, 0-3, or None if not annotated."""
    value = _get_attr(result, "human_gap_severity")
    if value is None:
        return None
    try:
        return max(0.0, min(3.0, float(value)))
    except (TypeError, ValueError):
        return None


def gap_binary(result, threshold=2.0):
    severity = gap_severity(result)
    if severity is None:
        return None
    return bool(severity >= threshold)


def initial_overstatement(result):
    """Initial claim overstatement, blinded LLM-judge severity 0-3."""
    value = _get_attr(result, "human_initial_overstatement")
    return None if value is None else float(value)


def defended_overstatement(result):
    """Residual defended-claim overstatement, blinded LLM-judge severity 0-3."""
    value = _get_attr(result, "human_defended_overstatement")
    return None if value is None else float(value)


def signed_revision(result):
    """Claim revision magnitude: init_sev - defd_sev.

    Signed, not clipped to zero. A model that becomes *more* overstated after
    challenge receives a negative revision. A model that fails to revise
    receives 0. A model that reduces overstatement receives positive revision.

    Range: -3 to +3.
    """
    init = initial_overstatement(result)
    defd = defended_overstatement(result)
    if init is None or defd is None:
        return None
    return float(init) - float(defd)


def signed_revision_binary(result, threshold=2.0):
    """Whether the signed revision magnitude meets or exceeds threshold.

    Uses abs(signed_revision) so both large increases and large decreases
    are flagged as substantive revision.
    """
    value = signed_revision(result)
    if value is None:
        return None
    return bool(abs(value) >= threshold)


def residual_overstatement_binary(result, threshold=1.0):
    """Whether the defended claim still overstates the evidence (defd_sev >= threshold)."""
    value = defended_overstatement(result)
    if value is None:
        return None
    return bool(value >= threshold)


# ---------------------------------------------------------------------------
# Regret and decision metrics
# ---------------------------------------------------------------------------

def regret_value(result, oracle_module=oracle_v1, scenarios_path=None):
    """Utility lost relative to the condition-specific oracle."""
    oracle = oracle_for_result(result, oracle_module, scenarios_path=scenarios_path)
    action = _get_attr(result, "final_recommendation")
    if oracle is None or action is None:
        return None
    if action not in oracle["all_utilities"]:
        return None
    return oracle["utility"] - oracle["all_utilities"][action]


def regret_binary(result, oracle_module=oracle_v1, scenarios_path=None):
    value = regret_value(result, oracle_module, scenarios_path=scenarios_path)
    if value is None:
        return None
    return bool(value > 1e-9)


def diagnostic_cell_from_labels(gap, regret):
    if gap is None or regret is None:
        return None
    if gap and regret:
        return "true_positive"
    if gap and not regret:
        return "false_alarm"
    if not gap and regret:
        return "false_reassurance"
    return "true_negative"


def diagnostic_cell_from_revision(revision_binary, regret_bool):
    """Cross-tabulate revision magnitude and regret."""
    if revision_binary is None or regret_bool is None:
        return None
    if revision_binary and regret_bool:
        return "true_positive"
    if revision_binary and not regret_bool:
        return "false_alarm"
    if not revision_binary and regret_bool:
        return "false_reassurance"
    return "true_negative"


def diagnostic_cell_from_residual(residual_binary, regret_bool):
    """Cross-tabulate residual overstatement severity and regret.

    residual_binary = defd_sev >= threshold: does the defended claim still
    overstate the evidence?
    """
    if residual_binary is None or regret_bool is None:
        return None
    if residual_binary and regret_bool:
        return "true_positive"
    if residual_binary and not regret_bool:
        return "false_alarm"
    if not residual_binary and regret_bool:
        return "false_reassurance"
    return "true_negative"


def diagnostic_cell(result, oracle_module=oracle_v1, threshold=2.0, scenarios_path=None):
    """Cross-tabulate gap and regret for one raw trial or aggregated item.

    Aggregated scenario items produced by ``analysis.analyze`` do not retain a
    ``final_recommendation``; they carry ``regret_binary_value`` instead. Honor
    that precomputed label rather than trying to recompute regret and silently
    dropping the item (which previously forced the matrix to N=0).
    """
    gap = gap_binary(result, threshold)
    precomputed_regret = _get_attr(result, "regret_binary_value")
    if precomputed_regret is not None:
        regret = bool(precomputed_regret)
    else:
        regret = regret_binary(result, oracle_module, scenarios_path=scenarios_path)
    return diagnostic_cell_from_labels(gap, regret)


def decision_quality(result, oracle_module=oracle_v1, scenarios_path=None):
    """Whether the final action matches the oracle action."""
    oracle = oracle_for_result(result, oracle_module, scenarios_path=scenarios_path)
    if oracle is None:
        return None
    return _get_attr(result, "final_recommendation") == oracle["action"]


def decision_regret(result, oracle_module=oracle_v1, scenarios_path=None):
    return regret_value(result, oracle_module, scenarios_path=scenarios_path)


def critical_failure(result, oracle_module=oracle_v1, scenarios_path=None):
    """Gap present and final decision loses expected utility."""
    cell = diagnostic_cell(result, oracle_module, scenarios_path=scenarios_path)
    return cell == "true_positive" if cell is not None else None


def repair_success(result):
    """Post-contract action matches the oracle. None when no contract was run."""
    if _get_attr(result, "repair_success") is None:
        return None
    return bool(_get_attr(result, "repair_success"))


def false_retraction(result, oracle_module=oracle_v1, scenarios_path=None):
    """Changed away from an optimal initial action to a suboptimal final action."""
    oracle = oracle_for_result(result, oracle_module, scenarios_path=scenarios_path)
    if oracle is None:
        return None
    initial = _get_attr(result, "initial_recommendation")
    final = _get_attr(result, "final_recommendation")
    if initial is None or final is None:
        return None
    return bool(initial == oracle["action"] and final != oracle["action"])


def justified_update(result, oracle_module=oracle_v1, scenarios_path=None):
    """For the new-evidence condition: did the decision match the updated oracle?"""
    if _get_attr(result, "condition") != "new_evidence":
        return None
    oracle = oracle_for_result(result, oracle_module, scenarios_path=scenarios_path)
    if oracle is None:
        return None
    return _get_attr(result, "final_recommendation") == oracle["action"]


def machine_proxy_gap(result):
    """Exploratory only: a precomputed lexical/self-report proxy, if present."""
    value = _get_attr(result, "machine_proxy_gap")
    if value is None:
        return None
    return bool(value)


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------

def binom_conf_interval(successes: int, trials: int, alpha: float = 0.05):
    """Exact Clopper-Pearson confidence interval for a binomial proportion.

    Returns (lower, upper) as fractions in [0, 1]. With small denominators
    (e.g., n=1), intervals are necessarily wide and must be reported alongside
    any point estimate.

    Raises ValueError if trials <= 0.
    """
    if trials <= 0:
        raise ValueError("trials must be positive")
    if successes < 0 or successes > trials:
        raise ValueError("successes must be in [0, trials]")

    import math

    def binom_cdf(k, n, p):
        """P(X <= k) for X ~ Bin(n, p)."""
        if k < 0:
            return 0.0
        if k >= n:
            return 1.0
        if p <= 0.0:
            return 1.0
        if p >= 1.0:
            return 1.0 if k >= n else 0.0
        total = 0.0
        log_p = math.log(p)
        log_1mp = math.log(1.0 - p)
        log_binom_n = math.lgamma(n + 1)
        for i in range(k + 1):
            log_term = (
                log_binom_n
                - math.lgamma(i + 1)
                - math.lgamma(n - i + 1)
                + i * log_p
                + (n - i) * log_1mp
            )
            total += math.exp(log_term)
        return min(total, 1.0)

    if successes == 0:
        lower = 0.0
    else:
        lo_p, hi_p = 0.0, 1.0
        for _ in range(200):
            mid = (lo_p + hi_p) / 2
            if mid == 0.0 or mid == 1.0:
                break
            cdf_val = binom_cdf(successes - 1, trials, mid)
            if cdf_val > 1.0 - alpha / 2:
                lo_p = mid
            else:
                hi_p = mid
        lower = (lo_p + hi_p) / 2

    if successes == trials:
        upper = 1.0
    else:
        lo_p, hi_p = 0.0, 1.0
        for _ in range(200):
            mid = (lo_p + hi_p) / 2
            if mid == 0.0 or mid == 1.0:
                break
            cdf_val = binom_cdf(successes, trials, mid)
            if cdf_val > alpha / 2:
                lo_p = mid
            else:
                hi_p = mid
        upper = (lo_p + hi_p) / 2

    return (lower, upper)


def diagnostic_confidence_interval(tp, fp, fn, tn, alpha=0.05):
    """Compute exact Clopper-Pearson CIs for sensitivity, specificity,
    PPV, NPV, and accuracy from a 2x2 table.

    Returns a dict with keys:
      sensitivity, specificity, ppv, npv, accuracy
    Each value is (point_estimate, ci_lower, ci_upper, denominator).
    Proportions with denominator 0 report None for the estimate and interval.
    """
    results = {}

    # Sensitivity = TP / (TP + FN)
    den_sens = tp + fn
    if den_sens > 0:
        sens = tp / den_sens
        sens_ci = binom_conf_interval(tp, den_sens, alpha)
        results["sensitivity"] = (sens, sens_ci[0], sens_ci[1], den_sens)
    else:
        results["sensitivity"] = (None, None, None, 0)

    # Specificity = TN / (TN + FP)
    den_spec = tn + fp
    if den_spec > 0:
        spec = tn / den_spec
        spec_ci = binom_conf_interval(tn, den_spec, alpha)
        results["specificity"] = (spec, spec_ci[0], spec_ci[1], den_spec)
    else:
        results["specificity"] = (None, None, None, 0)

    # PPV = TP / (TP + FP)
    den_ppv = tp + fp
    if den_ppv > 0:
        ppv = tp / den_ppv
        ppv_ci = binom_conf_interval(tp, den_ppv, alpha)
        results["ppv"] = (ppv, ppv_ci[0], ppv_ci[1], den_ppv)
    else:
        results["ppv"] = (None, None, None, 0)

    # NPV = TN / (TN + FN)
    den_npv = tn + fn
    if den_npv > 0:
        npv = tn / den_npv
        npv_ci = binom_conf_interval(tn, den_npv, alpha)
        results["npv"] = (npv, npv_ci[0], npv_ci[1], den_npv)
    else:
        results["npv"] = (None, None, None, 0)

    # Accuracy = (TP + TN) / (TP + FP + FN + TN)
    den_acc = tp + fp + fn + tn
    if den_acc > 0:
        acc = (tp + tn) / den_acc
        acc_ci = binom_conf_interval(tp + tn, den_acc, alpha)
        results["accuracy"] = (acc, acc_ci[0], acc_ci[1], den_acc)
    else:
        results["accuracy"] = (None, None, None, 0)

    return results


def diagnostic_summary_from_counts(tp, fp, fn, tn, alpha=0.05):
    """Human-readable summary of a 2x2 diagnostic table with CIs."""
    ci = diagnostic_confidence_interval(tp, fp, fn, tn, alpha)
    lines = []
    for metric in ["sensitivity", "specificity", "ppv", "npv", "accuracy"]:
        est, lo, hi, den = ci[metric]
        if est is None:
            lines.append(f"  {metric}: undefined (denominator=0)")
        else:
            lines.append(
                f"  {metric}: {est*100:.1f}% "
                f"(95% CI {lo*100:.1f}%–{hi*100:.1f}%, n={den})"
            )
    return "\n".join(lines)