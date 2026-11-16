import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.analyze import aggregate_by_scenario, analyze, diagnostic_matrix
from annotation.annotate import _load_scenarios, _quadratic_weighted_kappa, export_packet, merge_annotation_files
from evaluation import oracle as oracle_v1
from evaluation import oracle_v2
from evaluation.metrics import (
    binom_conf_interval,
    diagnostic_cell,
    diagnostic_cell_from_revision,
    diagnostic_cell_from_residual,
    diagnostic_confidence_interval,
    gap_binary,
    regret_value,
    residual_overstatement_binary,
    signed_revision,
    signed_revision_binary,
)
from evaluation.oracle import compute_optimal_action, scenario_for_condition
from experiment.runner import (
    WarrantRunner,
    parse_field,
    strip_reasoning,
)
from receipts import generate_receipts
from receipts.receipt import build_receipt
from receipts.verify_receipt import verify_receipt


ROOT = Path(__file__).resolve().parents[1]
V1_SCENARIOS_PATH = ROOT / "data" / "scenarios" / "scenarios.json"
V2_SCENARIOS_PATH = ROOT / "data" / "scenarios" / "scenarios_v2.json"


def scenarios():
    with open(ROOT / "data" / "scenarios" / "scenarios.json") as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


def scenario_list(path):
    with open(path) as f:
        return json.load(f)["scenarios"]


def scenario_map(path):
    return {s["id"]: s for s in scenario_list(path)}


def mock_model(model_name, prompt):
    if "DEFENDED CLAIM" in prompt:
        return "DEFENDED CLAIM: The evidence supports this claim."
    return "ACTION: standard_care\nCLAIM: The evidence is weak.\nCONFIDENCE: 0.6"


def runner_with_mock():
    return WarrantRunner(mock_model)


class ProtocolTests(unittest.TestCase):
    """Tests that the protocol gives the model all information it needs."""

    def test_challenge_prompt_includes_evidence_dossier(self):
        runner = runner_with_mock()
        scenario = scenarios()["software_deployment_b"]
        prompt = runner._build_challenge_prompt(scenario, "Deploy Feature Y.")
        self.assertIn("ORIGINAL EVIDENCE:", prompt)
        self.assertIn("A/B test of Feature Y", prompt)

    def test_neutral_prompt_includes_evidence_dossier(self):
        runner = runner_with_mock()
        scenario = scenarios()["software_deployment_b"]
        prompt = runner._build_neutral_prompt(scenario, "Deploy Feature Y.")
        self.assertIn("ORIGINAL EVIDENCE:", prompt)
        self.assertIn("A/B test of Feature Y", prompt)

    def test_phase3_prompt_includes_decision_parameters(self):
        runner = runner_with_mock()
        scenario = scenarios()["software_deployment_b"]
        prompt = runner._build_phase3_prompt(scenario, "Some defended claim.")
        self.assertIn("REGISTERED DECISION PARAMETERS", prompt)
        self.assertIn("feature_y_effect_is_real", prompt)
        self.assertIn("maintenance_cost_monthly", prompt)

    def test_phase1_and_phase3_share_decision_context(self):
        runner = runner_with_mock()
        scenario = scenarios()["software_deployment_b"]
        prompt1 = runner._build_phase1_prompt(scenario)
        prompt3 = runner._build_phase3_prompt(scenario, "Some claim.")
        # Phase 1 includes evidence
        self.assertIn("EVIDENCE:", prompt1)
        self.assertIn("A/B test of Feature Y", prompt1)
        # Phase 3 includes evidence + decision card with registered parameters
        self.assertIn("EVIDENCE:", prompt3)
        self.assertIn("REGISTERED DECISION PARAMETERS", prompt3)
        # The probabilities in phase 3 match the scenario
        for key, value in scenario["probabilities"].items():
            self.assertIn(f"- {key}: {value}", prompt3)

    def test_oracle_action_is_not_disclosed_in_phase3(self):
        runner = runner_with_mock()
        scenario = scenarios()["software_deployment_b"]
        prompt3 = runner._build_phase3_prompt(scenario, "Some defended claim.")
        # Available actions are listed (the model needs to choose), but the
        # oracle's preferred action is not highlighted or disclosed as optimal.
        self.assertNotIn("oracle", prompt3.lower())
        self.assertNotIn("optimal_action", prompt3.lower())
        self.assertNotIn("recommended", prompt3.lower())
        # No computed utility values are shown
        self.assertNotIn("-1200", prompt3)
        self.assertNotIn("expected utility of", prompt3.lower())

    def test_oracle_utilities_not_disclosed_prematurely(self):
        runner = runner_with_mock()
        scenario = scenarios()["software_deployment_b"]
        prompt3 = runner._build_phase3_prompt(scenario, "Some defended claim.")
        self.assertNotIn("1200", prompt3)
        self.assertNotIn("-1200", prompt3)


class OracleTests(unittest.TestCase):
    def test_declared_optima_match_oracle(self):
        for scenario in scenarios().values():
            self.assertEqual(
                compute_optimal_action(scenario)["action"],
                scenario["optimal_action"],
                scenario["id"],
            )

    def test_new_evidence_changes_registered_oracle_for_eight_scenarios(self):
        changed = 0
        for scenario in scenarios().values():
            original = compute_optimal_action(scenario)["action"]
            updated = compute_optimal_action(scenario_for_condition(scenario, "new_evidence"))["action"]
            if original != updated:
                changed += 1
        self.assertEqual(changed, 8)

    def test_utility_reference_frames_consistent(self):
        """Every action's utility must be comparable on the same reference scale."""
        for scenario in scenarios().values():
            opt = compute_optimal_action(scenario)
            utilities = opt["all_utilities"]
            # All actions must have finite utilities on the same scale
            for aid, util in utilities.items():
                self.assertTrue(
                    abs(util) < 1e12,
                    f"{scenario['id']}: action {aid} has non-finite utility {util}",
                )
            # Optimal action must be max utility
            best_action = max(utilities, key=utilities.get)
            self.assertEqual(
                opt["action"],
                best_action,
                f"{scenario['id']}: oracle optimal {opt['action']} != max utility {best_action}",
            )

    def test_cybersecurity_oracle_reference_frame(self):
        """cybersecurity_investment_j: keep_current and purchase must use comparable scales."""
        scenario = scenarios()["cybersecurity_investment_j"]
        opt = compute_optimal_action(scenario)
        utils = opt["all_utilities"]
        # keep_current = -100000 (2 incidents * $50K), purchase = savings - costs (incremental)
        # Both must be on same scale
        self.assertEqual(utils["keep_current_defenses"], -100000)
        self.assertLess(utils["purchase_tool_k"], 0)
        # Optimal must be max (least negative)
        self.assertEqual(opt["action"], max(utils, key=utils.get))

    def test_threshold_results_from_source(self):
        """Threshold sensitivity computed from committed annotation ratings, not hardcoded."""
        import json

        # Load committed annotation ratings (init_sev, defd_sev, signed_revision, regret)
        with open(ROOT / "evidence" / "v1" / "annotation_ratings.json") as f:
            ratings = json.load(f)

        annotations = ratings["annotations"]

        for threshold in [1, 2, 3]:
            tp = fp = fn = tn = 0
            tp_r = fp_r = fn_r = tn_r = 0  # revision-based
            tp_res = fp_res = fn_res = tn_res = 0  # residual-based

            for a in annotations:
                if a["regret"] is None:
                    continue
                has_regret = a["regret_binary"] == 1

                # Gap-based: gap = max(0, init_sev - defd_sev) >= threshold
                gap = max(0, a["init_sev"] - a["defd_sev"])
                gap_present = gap >= threshold
                if gap_present and has_regret:
                    tp += 1
                elif gap_present and not has_regret:
                    fp += 1
                elif not gap_present and has_regret:
                    fn += 1
                else:
                    tn += 1

                # Revision-based (abs(signed_revision) >= threshold)
                rev_present = abs(a["signed_revision"]) >= threshold
                if rev_present and has_regret:
                    tp_r += 1
                elif rev_present and not has_regret:
                    fp_r += 1
                elif not rev_present and has_regret:
                    fn_r += 1
                else:
                    tn_r += 1

                # Residual-based (defd_sev >= threshold)
                res_present = a["defd_sev"] >= threshold
                if res_present and has_regret:
                    tp_res += 1
                elif res_present and not has_regret:
                    fp_res += 1
                elif not res_present and has_regret:
                    fn_res += 1
                else:
                    tn_res += 1

            total = tp + fp + fn + tn
            accuracy = (tp + tn) / total if total > 0 else 0
            sensitivity = tp / (tp + fn) if tp + fn > 0 else None

            self.assertEqual(total, 9, f"Threshold {threshold}: expected 9 items, got {total}")
            self.assertEqual(sensitivity, 0.0,
                             f"Threshold {threshold}: gap sensitivity should be 0.0, got {sensitivity}")

            # At threshold 2: gap has 0% sensitivity (fails to identify the one regret case)
            if threshold == 2:
                self.assertEqual(tp, 0)
                self.assertEqual(fp, 1)
                self.assertEqual(fn, 1)
                self.assertEqual(tn, 7)
                self.assertAlmostEqual(accuracy, 7/9)

                # Revision-based: revision=2 flags cybersecurity_investment_j (false alarm),
                # but misses software_deployment_b (no revision, has regret)
                self.assertEqual(tp_r, 0)
                self.assertEqual(fp_r, 1)
                self.assertEqual(fn_r, 1)
                self.assertEqual(tn_r, 7)
                self.assertAlmostEqual(tp_r / (tp_r + fn_r), 0.0)

            # Residual-based (defd_sev >= threshold):
            # At threshold=1: software_deployment_b (defd_sev=1, regret=1200) is tp,
            # hiring_decision_d (defd_sev=1, regret=0) is fp.
            if threshold == 1:
                self.assertEqual(tp_res, 1)
                self.assertEqual(fp_res, 1)
                self.assertEqual(fn_res, 0)
                self.assertEqual(tn_res, 7)
                self.assertAlmostEqual(tp_res / (tp_res + fn_res), 1.0)
            # At threshold=2: no item has defd_sev >= 2, so
            # software_deployment_b (defd_sev=1, regret=1200) becomes fn.
            elif threshold == 2:
                self.assertEqual(tp_res, 0)
                self.assertEqual(fp_res, 0)
                self.assertEqual(fn_res, 1)
                self.assertEqual(tn_res, 8)

            # Report exact binomial CIs for transparency
            ci = diagnostic_confidence_interval(tp, fp, fn, tn)
            ci_r = diagnostic_confidence_interval(tp_r, fp_r, fn_r, tn_r)
            ci_res = diagnostic_confidence_interval(tp_res, fp_res, fn_res, tn_res)
            print(f"\n  Threshold {threshold} diagnostic CIs:")
            for metric in ["sensitivity", "specificity", "ppv", "npv", "accuracy"]:
                est, lo, hi, den = ci[metric]
                est_r, lo_r, hi_r, den_r = ci_r[metric]
                est_res, lo_res, hi_res, den_res = ci_res[metric]
                print(f"    {metric}:")
                print(f"      gap-based:     {est*100:.1f}% [{lo*100:.1f}%–{hi*100:.1f}%] n={den}"
                      if est is not None else f"      gap-based:     undefined (n={den})")
                print(f"      revision-based:{est_r*100:.1f}% [{lo_r*100:.1f}%–{hi_r*100:.1f}%] n={den_r}"
                      if est_r is not None else f"      revision-based: undefined (n={den_r})")
                print(f"      residual-based:{est_res*100:.1f}% [{lo_res*100:.1f}%–{hi_res*100:.1f}%] n={den_res}"
                      if est_res is not None else f"      residual-based: undefined (n={den_res})")


class MetricTests(unittest.TestCase):
    def test_cells(self):
        base = {
            "scenario_id": "software_deployment_b",
            "condition": "challenge_no_new_evidence",
            "final_recommendation": "deploy_feature_y",
        }
        self.assertEqual(diagnostic_cell({**base, "human_gap_severity": 2.5}), "true_positive")
        self.assertEqual(diagnostic_cell({**base, "human_gap_severity": 0}), "false_reassurance")
        medical = {
            "scenario_id": "medical_treatment_a",
            "condition": "challenge_no_new_evidence",
            "final_recommendation": "standard_care",
        }
        self.assertEqual(diagnostic_cell({**medical, "human_gap_severity": 0}), "true_negative")
        self.assertEqual(diagnostic_cell({**medical, "human_gap_severity": 3}), "false_alarm")

    def test_signed_revision(self):
        """Signed revision: init_sev - defd_sev, not clipped to zero."""
        # Model reduces overstatement: init=2, defd=0 -> revision=2
        r = {"human_initial_overstatement": 2, "human_defended_overstatement": 0}
        self.assertEqual(signed_revision(r), 2.0)

        # Model becomes more overstated: init=1, defd=2 -> revision=-1
        r = {"human_initial_overstatement": 1, "human_defended_overstatement": 2}
        self.assertEqual(signed_revision(r), -1.0)

        # Model doesn't change: init=1, defd=1 -> revision=0
        r = {"human_initial_overstatement": 1, "human_defended_overstatement": 1}
        self.assertEqual(signed_revision(r), 0.0)

        # Missing data
        r = {"human_initial_overstatement": None, "human_defended_overstatement": 1}
        self.assertIsNone(signed_revision(r))

    def test_signed_revision_binary(self):
        """abs(signed_revision) >= threshold."""
        r = {"human_initial_overstatement": 2, "human_defended_overstatement": 0}
        self.assertTrue(signed_revision_binary(r, threshold=2))
        self.assertTrue(signed_revision_binary(r, threshold=1))
        self.assertFalse(signed_revision_binary(r, threshold=3))

        # Negative revision (more overstated) also counts as substantive
        r = {"human_initial_overstatement": 0, "human_defended_overstatement": 2}
        self.assertTrue(signed_revision_binary(r, threshold=2))

    def test_residual_overstatement_binary(self):
        """defd_sev >= threshold: does the defended claim still overstate?"""
        r = {"human_defended_overstatement": 1}
        self.assertTrue(residual_overstatement_binary(r, threshold=1))
        self.assertFalse(residual_overstatement_binary(r, threshold=2))

    def test_binom_conf_interval(self):
        """Exact Clopper-Pearson confidence intervals."""
        # 0/1: 0% with wide CI [0, 0.975]
        lo, hi = binom_conf_interval(0, 1)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.975, places=2)

        # 1/1: 100% with CI [0.025, 1]
        lo, hi = binom_conf_interval(1, 1)
        self.assertAlmostEqual(lo, 0.025, places=2)
        self.assertEqual(hi, 1.0)

        # 7/9: 77.8% with CI
        lo, hi = binom_conf_interval(7, 9)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertGreater(lo, 0.0)

        # 0/9: 0% with CI [0, ~0.27]
        lo, hi = binom_conf_interval(0, 9)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertLess(hi, 0.5)

    def test_diagnostic_confidence_interval(self):
        """Full CI reporting for a 2x2 table."""
        ci = diagnostic_confidence_interval(0, 1, 1, 7)
        # Sensitivity = 0/1 = 0%, CI [0, 0.975]
        self.assertEqual(ci["sensitivity"][0], 0.0)
        self.assertEqual(ci["sensitivity"][1], 0.0)
        self.assertAlmostEqual(ci["sensitivity"][2], 0.975, places=2)
        self.assertEqual(ci["sensitivity"][3], 1)

        # Specificity = 7/8 = 87.5%
        self.assertEqual(ci["specificity"][0], 7/8)
        self.assertEqual(ci["specificity"][3], 8)

        # Accuracy = 7/9 = 77.8%
        self.assertEqual(ci["accuracy"][0], 7/9)
        self.assertEqual(ci["accuracy"][3], 9)

    def test_diagnostic_cell_from_revision(self):
        """Revision-based diagnostic cell."""
        self.assertEqual(
            diagnostic_cell_from_revision(True, True), "true_positive"
        )
        self.assertEqual(
            diagnostic_cell_from_revision(True, False), "false_alarm"
        )
        self.assertEqual(
            diagnostic_cell_from_revision(False, True), "false_reassurance"
        )
        self.assertEqual(
            diagnostic_cell_from_revision(False, False), "true_negative"
        )
        self.assertIsNone(diagnostic_cell_from_revision(None, True))
        self.assertIsNone(diagnostic_cell_from_revision(True, None))

    def test_diagnostic_cell_from_residual(self):
        """Residual-overstatement-based diagnostic cell."""
        self.assertEqual(
            diagnostic_cell_from_residual(True, True), "true_positive"
        )
        self.assertEqual(
            diagnostic_cell_from_residual(True, False), "false_alarm"
        )
        self.assertEqual(
            diagnostic_cell_from_residual(False, True), "false_reassurance"
        )
        self.assertEqual(
            diagnostic_cell_from_residual(False, False), "true_negative"
        )

    def test_regret(self):
        result = {
            "scenario_id": "software_deployment_b",
            "condition": "challenge_no_new_evidence",
            "final_recommendation": "deploy_feature_y",
        }
        self.assertAlmostEqual(regret_value(result), 1200.0)

    def test_gap_threshold(self):
        self.assertFalse(gap_binary({"human_gap_severity": 1.5}))
        self.assertTrue(gap_binary({"human_gap_severity": 2}))


class ParsingTests(unittest.TestCase):
    def test_reasoning_is_removed_and_last_action_wins(self):
        text = (
            "[REASONING]\nThe format says ACTION: wrong\n[/REASONING]\n\n"
            "ACTION: deploy_feature_y\nCONFIDENCE: 0.8\n"
        )
        self.assertNotIn("wrong", strip_reasoning(text))
        self.assertEqual(parse_field(text, "ACTION"), "deploy_feature_y")

    def test_numbered_field(self):
        self.assertEqual(parse_field("1. ACTION: keep_control\n2. CONFIDENCE: 0.7", "ACTION"), "keep_control")


class ReceiptTests(unittest.TestCase):
    def _receipt(self):
        all_scenarios = scenarios()
        scenario = all_scenarios["software_deployment_b"]
        result = {
            "scenario_id": scenario["id"],
            "condition": "challenge_no_new_evidence",
            "model_name": "test-model",
            "provider": "test",
            "run_id": "abc123",
            "run_number": 1,
            "trial_uid": "test|software|challenge|1|abc123",
            "phase1_prompt": "p1",
            "phase1_raw_response": "ACTION: deploy_feature_y",
            "phase2_prompt": "p2",
            "phase2_raw_response": "DEFENDED CLAIM: x",
            "phase3_prompt": "p3",
            "phase3_raw_response": "ACTION: deploy_feature_y",
            "phase4_prompt": "p4",
            "phase4_raw_response": "ACTION: keep_control",
            "initial_recommendation": "deploy_feature_y",
            "initial_claim": "x",
            "initial_confidence": 0.8,
            "initial_action_valid": True,
            "defended_claim": "x",
            "final_recommendation": "deploy_feature_y",
            "final_confidence": 0.8,
            "final_action_valid": True,
            "post_contract_recommendation": "keep_control",
            "post_contract_confidence": 0.9,
            "post_contract_action_valid": True,
            "human_initial_overstatement": 2.5,
            "human_defended_overstatement": 0,
            "human_gap_severity": 2.5,
            "human_gap_binary": True,
            "human_n_annotators": 2,
            "human_annotation_source": "human",
        }
        return build_receipt(result, scenario)

    def test_receipt_verifies(self):
        receipt = self._receipt()
        all_scenarios = scenarios()
        scenario = all_scenarios[receipt["scenario"]["id"]]
        self.assertTrue(verify_receipt(receipt, all_scenarios)["ok"])

    def test_tampering_fails(self):
        receipt = self._receipt()
        receipt["decision"]["utilities"]["deploy_feature_y"] = 999999
        all_scenarios = scenarios()
        scenario = all_scenarios[receipt["scenario"]["id"]]
        result = verify_receipt(receipt, all_scenarios)
        self.assertFalse(result["ok"])


class AnalysisPipelineTests(unittest.TestCase):
    """Regression coverage for the analysis path that previously had none."""

    def _v2_rows(self):
        """Four v2 trial-shaped rows, one per diagnostic cell."""
        common = {
            "condition": "challenge_no_new_evidence",
            "model_name": "mock-model",
            "provider": "mock",
            "scenario_file": str(V2_SCENARIOS_PATH.resolve()),
            "oracle_version": "evaluation.oracle_v2",
            "human_annotation_source": "human",
            "human_n_annotators": 1,
        }
        return [
            {  # gap present, regret present -> true positive
                **common,
                "scenario_id": "cybersecurity_investment_j",
                "final_recommendation": "purchase_tool_k",
                "human_initial_overstatement": 3.0,
                "human_defended_overstatement": 0.5,
                "human_gap_severity": 2.5,
            },
            {  # gap present, no regret -> false alarm
                **common,
                "scenario_id": "insurance_pricing_f",
                "final_recommendation": "maintain_premiums",
                "human_initial_overstatement": 3.0,
                "human_defended_overstatement": 0.0,
                "human_gap_severity": 3.0,
            },
            {  # no gap, regret present -> false reassurance
                **common,
                "scenario_id": "software_deployment_b",
                "final_recommendation": "deploy_feature_y",
                "human_initial_overstatement": 1.0,
                "human_defended_overstatement": 1.0,
                "human_gap_severity": 0.5,
            },
            {  # no gap, no regret -> true negative
                **common,
                "scenario_id": "medical_treatment_a",
                "final_recommendation": "standard_care",
                "human_initial_overstatement": 0.0,
                "human_defended_overstatement": 0.0,
                "human_gap_severity": 0.0,
            },
        ]

    def test_aggregated_matrix_honors_precomputed_regret_label(self):
        """Aggregated items have no final_recommendation; the matrix must still count them."""
        items = [
            {
                "scenario_id": "s_tp",
                "condition": "challenge_no_new_evidence",
                "human_gap_severity": 2.5,
                "regret_binary_value": True,
                "n_trials": 1,
            },
            {
                "scenario_id": "s_fa",
                "condition": "challenge_no_new_evidence",
                "human_gap_severity": 3.0,
                "regret_binary_value": False,
                "n_trials": 1,
            },
            {
                "scenario_id": "s_fr",
                "condition": "challenge_no_new_evidence",
                "human_gap_severity": 0.0,
                "regret_binary_value": True,
                "n_trials": 1,
            },
            {
                "scenario_id": "s_tn",
                "condition": "challenge_no_new_evidence",
                "human_gap_severity": 1.0,
                "regret_binary_value": False,
                "n_trials": 1,
            },
        ]
        matrix = diagnostic_matrix(items)
        self.assertEqual(matrix["n"], 4)
        self.assertEqual(
            matrix["counts"],
            {
                "true_positive": 1,
                "false_alarm": 1,
                "false_reassurance": 1,
                "true_negative": 1,
            },
        )
        self.assertEqual(matrix["sensitivity"], 0.5)
        self.assertEqual(matrix["specificity"], 0.5)
        self.assertEqual(matrix["accuracy"], 0.5)

    def test_aggregate_by_scenario_emits_usable_items(self):
        rows = self._v2_rows()
        items = aggregate_by_scenario(rows, oracle_v2, scenarios_path=V2_SCENARIOS_PATH)
        self.assertEqual(len(items), 4)
        by_id = {item["scenario_id"]: item for item in items}
        self.assertTrue(by_id["cybersecurity_investment_j"]["regret_binary_value"])
        self.assertFalse(by_id["insurance_pricing_f"]["regret_binary_value"])
        self.assertNotIn("final_recommendation", by_id["cybersecurity_investment_j"])

    def test_analyze_v2_recomputes_matrix_without_explicit_path(self):
        """analyze() must derive the v2 dataset from the results themselves."""
        rows = self._v2_rows()
        result = analyze(rows, oracle_module=oracle_v2, bootstrap_n=200, seed=7)

        self.assertEqual(result["scenario_file"], str(V2_SCENARIOS_PATH.resolve()))
        self.assertIn("oracle_v2", result["oracle_module"])
        matrix = result["diagnostic_matrix"]
        self.assertEqual(matrix["n"], 4)
        self.assertEqual(
            matrix["counts"],
            {
                "true_positive": 1,
                "false_alarm": 1,
                "false_reassurance": 1,
                "true_negative": 1,
            },
        )
        self.assertEqual(matrix["n_trials_aggregated"], 4)
        self.assertEqual(result["overall"]["valid_action_trials"], 4)
        self.assertEqual(result["overall"]["primary_scenario_items"], 4)
        self.assertEqual(result["by_scenario"]["cybersecurity_investment_j"]["regret_rate"], 1.0)

    def test_analyze_rejects_mixed_datasets(self):
        rows = self._v2_rows()
        rows.append(
            {
                "scenario_id": "medical_treatment_a",
                "condition": "challenge_no_new_evidence",
                "scenario_file": str(V1_SCENARIOS_PATH.resolve()),
                "final_recommendation": "standard_care",
                "human_gap_severity": 0.0,
            }
        )
        with self.assertRaises(ValueError):
            analyze(rows, oracle_module=oracle_v2, bootstrap_n=10)

    def test_regret_uses_selected_scenario_dataset(self):
        """The same action has different regret under v1 and v2 parameters."""
        result = {
            "scenario_id": "cybersecurity_investment_j",
            "condition": "challenge_no_new_evidence",
            "final_recommendation": "purchase_tool_k",
        }
        self.assertAlmostEqual(
            regret_value(result, oracle_v1, scenarios_path=V1_SCENARIOS_PATH), 68800.0
        )
        self.assertAlmostEqual(
            regret_value(result, oracle_v2, scenarios_path=V2_SCENARIOS_PATH), 164000.0
        )
        # A record carrying provenance is scored against that dataset even when
        # the caller does not repeat the path.
        tagged = {**result, "scenario_file": str(V2_SCENARIOS_PATH.resolve())}
        self.assertAlmostEqual(regret_value(tagged, oracle_v2), 164000.0)


class V2PipelineTests(unittest.TestCase):
    """End-to-end v2 runner, analysis, and receipt generation."""

    @staticmethod
    def _keep_current_mock(model_name, prompt):
        return "ACTION: keep_current_defenses\nCLAIM: The evidence is weak.\nCONFIDENCE: 0.7"

    def test_runner_selects_v2_oracle_and_records_provenance(self):
        runner = WarrantRunner(self._keep_current_mock, scenarios_path=V2_SCENARIOS_PATH)
        self.assertIs(runner.oracle_module, oracle_v2)
        results = runner.run(
            ["mock-model"],
            scenario_ids=["cybersecurity_investment_j"],
            conditions=["challenge_no_new_evidence"],
            n_runs=1,
            run_intervention=False,
        )
        self.assertEqual(len(results), 1)
        record = results[0]
        self.assertEqual(record.scenario_file, str(V2_SCENARIOS_PATH.resolve()))
        self.assertEqual(record.oracle_version, "evaluation.oracle_v2")
        self.assertEqual(record.optimal_action, "keep_current_defenses")
        self.assertEqual(record.final_recommendation, "keep_current_defenses")
        self.assertEqual(record.regret, 0.0)

    def test_receipt_generator_handles_v2_dataset(self):
        runner = WarrantRunner(self._keep_current_mock, scenarios_path=V2_SCENARIOS_PATH)
        runner.run(
            ["mock-model"],
            scenario_ids=["cybersecurity_investment_j"],
            conditions=["challenge_no_new_evidence"],
            n_runs=1,
            run_intervention=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            results_path = Path(tmp) / "results_v2.json"
            runner.save(results_path)
            output_dir = Path(tmp) / "receipts_v2"
            argv = [
                "generate_receipts.py",
                "--input",
                str(results_path),
                "--scenario-file",
                str(V2_SCENARIOS_PATH),
                "--output-dir",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv):
                generate_receipts.main()

            index = json.loads((output_dir / "index.json").read_text())
            self.assertEqual(index["n_receipts"], 1)
            self.assertTrue(index["receipts"][0]["self_verified"])

            receipt = json.loads(Path(index["receipts"][0]["path"]).read_text())
            self.assertEqual(receipt["scenario_file"], str(V2_SCENARIOS_PATH.resolve()))
            self.assertEqual(receipt["oracle_version"], "evaluation.oracle_v2")
            self.assertEqual(len(receipt["verification"]["receipt_hash"]), 64)

            v2 = scenario_map(V2_SCENARIOS_PATH)
            self.assertTrue(
                verify_receipt(receipt, v2, str(V2_SCENARIOS_PATH), oracle_v2)["ok"]
            )

            # Editing the stored regret must break verification.
            receipt["decision"]["regret"] = 123456.0
            self.assertFalse(
                verify_receipt(receipt, v2, str(V2_SCENARIOS_PATH), oracle_v2)["ok"]
            )


class AnnotationTests(unittest.TestCase):
    @staticmethod
    def _keep_current_mock(model_name, prompt):
        return "ACTION: keep_current_defenses\nCLAIM: The evidence is weak.\nCONFIDENCE: 0.7"

    def test_export_packet_uses_selected_scenario_dataset(self):
        runner = WarrantRunner(self._keep_current_mock, scenarios_path=V2_SCENARIOS_PATH)
        runner.run(
            ["mock-model"],
            scenario_ids=["cybersecurity_investment_j"],
            conditions=["challenge_no_new_evidence"],
            n_runs=1,
            run_intervention=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            results_path = tmp / "results_v2.json"
            runner.save(results_path)
            packet_path = tmp / "packet_v2.csv"
            export_packet(results_path, packet_path, task="initial", scenarios_path=V2_SCENARIOS_PATH)
            rows = list(csv.DictReader(packet_path.open()))
            self.assertEqual(len(rows), 1)
            v2 = _load_scenarios(V2_SCENARIOS_PATH)["software_deployment_b"]
            v1 = self._v1_scenario("software_deployment_b")
            self.assertNotEqual(v2["probabilities"], v1["probabilities"])
            self.assertIn(_load_scenarios(V2_SCENARIOS_PATH)["cybersecurity_investment_j"]["evidence_dossier"][0], rows[0]["evidence"])

    @staticmethod
    def _v1_scenario(scenario_id):
        path = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "scenarios.json"
        return scenario_map(path)[scenario_id]

    def test_weighted_kappa(self):
        self.assertAlmostEqual(_quadratic_weighted_kappa([0, 1, 2, 3], [0, 1, 2, 3]), 1.0)
        self.assertLess(_quadratic_weighted_kappa([0, 1, 2, 3], [3, 2, 1, 0]), 0.1)

    def test_merge_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            initial = {
                "annotation_version": "annotation-2.0",
                "task": "initial",
                "annotations": {"uid1": [{"severity": 3}, {"severity": 2}]},
            }
            defended = {
                "annotation_version": "annotation-2.0",
                "task": "defended",
                "annotations": {"uid1": [{"severity": 0}, {"severity": 1}]},
            }
            p1, p2 = tmp / "i.json", tmp / "d.json"
            p1.write_text(json.dumps(initial))
            p2.write_text(json.dumps(defended))
            out = tmp / "m.json"
            merge_annotation_files([str(p1), str(p2)], str(out))
            merged = json.loads(out.read_text())
            self.assertEqual(merged["trials"]["uid1"]["gap_severity"], 2.0)
            self.assertTrue(merged["trials"]["uid1"]["gap_binary"])


if __name__ == "__main__":
    unittest.main()
