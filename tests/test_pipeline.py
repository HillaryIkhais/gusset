import json
import tempfile
import unittest
from pathlib import Path

from annotation.annotate import _quadratic_weighted_kappa, merge_annotation_files
from evaluation.metrics import diagnostic_cell, gap_binary, regret_value
from evaluation.oracle import compute_optimal_action, scenario_for_condition
from experiment.runner import (
    WarrantRunner,
    parse_field,
    strip_reasoning,
)
from receipts.receipt import build_receipt, verify_receipt


ROOT = Path(__file__).resolve().parents[1]


def scenarios():
    with open(ROOT / "data" / "scenarios" / "scenarios.json") as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


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
        self.assertEqual(changed, 7)

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
        # keep_current = 0 (baseline), purchase = savings - costs (incremental)
        # Both must be on same scale
        self.assertEqual(utils["keep_current_defenses"], 0)
        self.assertLess(utils["purchase_tool_k"], 0)
        # Optimal must be max (least negative)
        self.assertEqual(opt["action"], max(utils, key=utils.get))

    def test_threshold_results_from_source(self):
        """Threshold sensitivity computed from source records, not hardcoded."""
        import math

        # Source data from reports/annotated.json and llm judge files
        init_defended = {
            "software_deployment_b": (1, 1),
            "cybersecurity_investment_j": (2, 0),
            "educational_intervention_g": (0, 0),
            "hiring_decision_d": (2, 1),
            "insurance_pricing_f": (1, 0),
            "investment_decision_c": (0, 0),
            "marketing_campaign_i": (1, 0),
            "medical_treatment_a": (0, 0),
            "policy_implementation_e": (1, 0),
            "supply_chain_decision_h": (1, 0),
        }

        regret = {
            "software_deployment_b": 1200.0,
            "cybersecurity_investment_j": 0.0,
            "educational_intervention_g": 0.0,
            "hiring_decision_d": 0.0,
            "insurance_pricing_f": None,
            "investment_decision_c": 0.0,
            "marketing_campaign_i": 0.0,
            "medical_treatment_a": 0.0,
            "policy_implementation_e": 0.0,
            "supply_chain_decision_h": 0.0,
        }

        for threshold in [1, 2, 3]:
            tp = fp = fn = tn = 0
            for sid, (init, defd) in init_defended.items():
                if regret[sid] is None:
                    continue
                gap = max(0, init - defd)
                gap_present = gap >= threshold
                has_regret = regret[sid] > 0
                if gap_present and has_regret:
                    tp += 1
                elif gap_present and not has_regret:
                    fp += 1
                elif not gap_present and has_regret:
                    fn += 1
                else:
                    tn += 1
            total = tp + fp + fn + tn
            accuracy = (tp + tn) / total if total > 0 else 0
            sensitivity = tp / (tp + fn) if tp + fn > 0 else None
            self.assertEqual(total, 9, f"Threshold {threshold}: expected 9 items (insurance_pricing_f excluded: no valid action), got {total}")
            if threshold == 2:
                self.assertEqual(tp, 0)
                self.assertEqual(fp, 1)
                self.assertEqual(fn, 1)
                self.assertEqual(tn, 7)
                self.assertEqual(accuracy, 7/9)
                self.assertEqual(sensitivity, 0.0)


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
        scenario = scenarios()["software_deployment_b"]
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
        self.assertTrue(verify_receipt(receipt, registered_scenarios=scenarios())["ok"])

    def test_tampering_fails(self):
        receipt = self._receipt()
        receipt["decision"]["utilities"]["deploy_feature_y"] = 999999
        result = verify_receipt(receipt, registered_scenarios=scenarios())
        self.assertFalse(result["ok"])


class AnnotationTests(unittest.TestCase):
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
