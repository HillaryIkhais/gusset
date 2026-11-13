import json
import tempfile
import unittest
from pathlib import Path

from annotation.annotate import _quadratic_weighted_kappa, merge_annotation_files
from evaluation.metrics import diagnostic_cell, gap_binary, regret_value
from evaluation.oracle import compute_optimal_action, scenario_for_condition
from experiment.runner import parse_field, strip_reasoning
from receipts.receipt import build_receipt, verify_receipt


ROOT = Path(__file__).resolve().parents[1]


def scenarios():
    with open(ROOT / "data" / "scenarios" / "scenarios.json") as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


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
