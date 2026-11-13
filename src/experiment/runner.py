"""GUSSET experiment runner.

Protocol
--------
The same scenario is run under four conditions:

1. ``no_challenge``           - initial decision, then a second decision with no challenge.
2. ``neutral_clarification``  - a reviewer asks for clarification, with no challenge.
3. ``challenge_no_new_evidence`` - a reviewer says the claim may exceed the evidence.
4. ``new_evidence``           - a genuine new fact is supplied and the oracle is
                                recomputed from the registered updated assumptions.

The initial claim and the defended claim are preserved verbatim. The
implication-defense gap is *not* inferred from the model's own yes/no
acknowledgment. It is measured later by blinded human annotation.

The intervention is a separate model call. It presents the registered
probabilities and costs and asks the model to recompute expected utility. The
runner never substitutes the oracle's answer for the model's answer.
"""

import copy
import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from evaluation.oracle import compute_optimal_action, expected_utility, scenario_for_condition


SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "scenarios.json"
OUTPUTS_PATH = Path(__file__).resolve().parents[2] / "reports"

CONDITIONS = [
    "no_challenge",
    "neutral_clarification",
    "challenge_no_new_evidence",
    "new_evidence",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def load_scenarios():
    with open(SCENARIOS_PATH) as f:
        return json.load(f)["scenarios"]


def strip_reasoning(text):
    """Remove a leading ``[REASONING]...[/REASONING]`` block, if present."""
    if not text:
        return ""
    return re.sub(r"\[REASONING\].*?\[/REASONING\]", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def _clean_line(line):
    line = line.strip()
    line = re.sub(r"^[-*]\s*", "", line)
    line = re.sub(r"^\d+[\.\)]\s*", "", line)
    return line.strip()


def parse_field(text, field):
    """Return the last value for ``FIELD: value`` outside a reasoning block.

    Models sometimes restate the requested format inside their reasoning. We
    strip the reasoning block and take the last match in the visible answer.
    """
    visible = strip_reasoning(text)
    pattern = re.compile(rf"^{re.escape(field)}\s*:\s*(.*)$", re.IGNORECASE)
    value = None
    for line in visible.splitlines():
        match = pattern.match(_clean_line(line))
        if match:
            value = match.group(1).strip().strip('"').strip("'").strip()
    return value


def parse_confidence(text):
    raw = parse_field(text, "CONFIDENCE")
    if raw is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    value = float(match.group(0))
    if value > 1.0 and value <= 100.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))


class TrialResult:
    """Container for one model x scenario x condition trial."""

    def __init__(self, scenario_id, model_name, run_id, provider=None, condition=None):
        self.scenario_id = scenario_id
        self.condition = condition
        self.model_name = model_name
        self.provider = provider
        self.run_id = run_id
        self.run_number = None
        self.timestamp = utc_now()
        self.scenario_hash = None
        self.trial_uid = None

        # Raw protocol data (preserved verbatim for reproducibility and receipts)
        self.phase1_prompt = None
        self.phase1_raw_response = None
        self.phase2_prompt = None
        self.phase2_raw_response = None
        self.phase3_prompt = None
        self.phase3_raw_response = None
        self.phase4_prompt = None
        self.phase4_raw_response = None

        # Phase 1: initial recommendation
        self.initial_recommendation = None
        self.initial_claim = None
        self.initial_confidence = None
        self.initial_action_valid = None

        # Phase 2: clarification / challenge / new evidence
        self.defended_claim = None
        self.defended_acknowledgement = None
        self.defended_action_valid = None

        # Phase 3: final recommendation after the condition
        self.final_recommendation = None
        self.final_confidence = None
        self.final_action_valid = None
        self.action_changed = None

        # Phase 4: decision contract (separate model call)
        self.intervention_applied = None
        self.intervention_required = None
        self.decisive_gusset = None
        self.gusset_threshold = None
        self.post_contract_recommendation = None
        self.post_contract_confidence = None
        self.post_contract_action_valid = None

        # Verification
        self.verified_recommendation = None
        self.repair_success = None

        # Registered oracle under this condition
        self.optimal_action = None
        self.optimal_utility = None
        self.all_utilities = None
        self.original_optimal_action = None
        self.original_optimal_utility = None
        self.regret = None
        self.expected_update = None
        self.justified_update = None

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class WarrantRunner:
    def __init__(self, model_interface, human_annotator=None):
        self.model_interface = model_interface
        self.human_annotator = human_annotator
        self.scenarios = load_scenarios()
        self.results = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        model_names,
        scenario_ids=None,
        output_path=None,
        n_runs=1,
        providers=None,
        conditions=None,
        save_every=1,
        run_intervention=True,
        request_delay=0.0,
        max_retries=4,
    ):
        """Run trials.

        ``conditions`` defaults to the challenge condition only. Pass
        ``CONDITIONS`` or ``"all"`` for the full control design.
        """
        scenario_ids = scenario_ids or [s["id"] for s in self.scenarios]
        scenario_map = {s["id"]: s for s in self.scenarios}
        providers = providers or {}
        if conditions is None:
            conditions = ["challenge_no_new_evidence"]
        elif conditions == "all":
            conditions = list(CONDITIONS)
        unknown = [c for c in conditions if c not in CONDITIONS]
        if unknown:
            raise ValueError(f"Unknown conditions: {unknown}. Choose from {CONDITIONS}")

        trial_count = 0
        for model_name in model_names:
            provider = providers.get(model_name)
            for sid in scenario_ids:
                scenario = scenario_map[sid]
                for condition in conditions:
                    for run_number in range(1, n_runs + 1):
                        if request_delay and trial_count:
                            time.sleep(request_delay)
                        result = self._run_with_retries(
                            model_name=model_name,
                            scenario=scenario,
                            provider=provider,
                            condition=condition,
                            run_number=run_number,
                            run_intervention=run_intervention,
                            max_retries=max_retries,
                        )
                        self.results.append(result)
                        trial_count += 1
                        if output_path and trial_count % save_every == 0:
                            self.save(output_path)

        if output_path:
            self.save(output_path)
        return self.results

    def _run_with_retries(self, model_name, scenario, provider, condition, run_number, run_intervention, max_retries):
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._run_trial(
                    model_name, scenario, provider, condition, run_number, run_intervention
                )
            except Exception as exc:
                last_error = exc
                if "429" in str(exc) or "Too Many Requests" in str(exc) or "rate limit" in str(exc).lower():
                    wait = 2 ** attempt
                    print(f"  Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    break
        return {
            "scenario_id": scenario["id"],
            "condition": condition,
            "model_name": model_name,
            "provider": provider,
            "run_number": run_number,
            "run_id": str(uuid.uuid4())[:8],
            "timestamp": utc_now(),
            "error": str(last_error),
            "error_type": type(last_error).__name__,
        }

    # ------------------------------------------------------------------
    # Trial
    # ------------------------------------------------------------------
    def _run_trial(self, model_name, scenario, provider, condition, run_number, run_intervention):
        run_id = str(uuid.uuid4())[:8]
        result = TrialResult(scenario["id"], model_name, run_id, provider, condition)
        result.run_number = run_number
        result.trial_uid = f"{model_name}|{scenario['id']}|{condition}|{run_number}|{run_id}"

        original_oracle = compute_optimal_action(scenario)
        result.original_optimal_action = original_oracle["action"]
        result.original_optimal_utility = original_oracle["utility"]

        condition_scenario = scenario_for_condition(scenario, condition)
        phase3_scenario = copy.deepcopy(condition_scenario)
        if condition == "new_evidence":
            phase3_scenario.setdefault("evidence_dossier", []).append(
                condition_scenario.get("new_evidence_applied", "")
            )
        oracle = compute_optimal_action(condition_scenario)
        result.optimal_action = oracle["action"]
        result.optimal_utility = oracle["utility"]
        result.all_utilities = oracle["all_utilities"]
        result.scenario_hash = sha256_obj(condition_scenario)
        result.expected_update = oracle["action"] if condition == "new_evidence" else None

        valid_actions = {a["id"] for a in condition_scenario["actions"]}

        # ---- Phase 1: initial recommendation ----
        prompt1 = self._build_phase1_prompt(condition_scenario)
        response1 = self.model_interface(model_name, prompt1)
        result.phase1_prompt = prompt1
        result.phase1_raw_response = response1
        result.initial_recommendation, result.initial_claim, result.initial_confidence, result.initial_action_valid = (
            self._parse_decision(response1, valid_actions)
        )

        # ---- Phase 2: condition ----
        result.defended_claim = result.initial_claim
        if condition == "no_challenge":
            result.phase2_prompt = None
            result.phase2_raw_response = None
        elif condition == "neutral_clarification":
            prompt2 = self._build_neutral_prompt(condition_scenario, result.initial_claim)
            response2 = self.model_interface(model_name, prompt2)
            result.phase2_prompt = prompt2
            result.phase2_raw_response = response2
            result.defended_claim = parse_field(response2, "DEFENDED CLAIM") or result.initial_claim
            result.defended_acknowledgement = parse_field(response2, "ACKNOWLEDGEMENT")
        elif condition == "challenge_no_new_evidence":
            prompt2 = self._build_challenge_prompt(condition_scenario, result.initial_claim)
            response2 = self.model_interface(model_name, prompt2)
            result.phase2_prompt = prompt2
            result.phase2_raw_response = response2
            result.defended_claim = parse_field(response2, "DEFENDED CLAIM") or result.initial_claim
            result.defended_acknowledgement = parse_field(response2, "ACKNOWLEDGEMENT")
        elif condition == "new_evidence":
            prompt2 = self._build_new_evidence_prompt(scenario, condition_scenario, result.initial_claim)
            response2 = self.model_interface(model_name, prompt2)
            result.phase2_prompt = prompt2
            result.phase2_raw_response = response2
            result.defended_claim = parse_field(response2, "DEFENDED CLAIM") or result.initial_claim
            result.defended_acknowledgement = parse_field(response2, "ACKNOWLEDGEMENT")
        else:
            raise ValueError(f"Unknown condition: {condition}")

        # ---- Phase 3: final recommendation ----
        prompt3 = self._build_phase3_prompt(phase3_scenario, result.defended_claim)
        response3 = self.model_interface(model_name, prompt3)
        result.phase3_prompt = prompt3
        result.phase3_raw_response = response3
        result.final_recommendation, _claim, result.final_confidence, result.final_action_valid = (
            self._parse_decision(response3, valid_actions)
        )
        result.action_changed = (
            result.initial_recommendation != result.final_recommendation
            if result.initial_recommendation and result.final_recommendation
            else None
        )
        if result.final_recommendation in oracle["all_utilities"]:
            result.regret = oracle["utility"] - oracle["all_utilities"][result.final_recommendation]
        result.justified_update = (
            result.final_recommendation == oracle["action"] if condition == "new_evidence" else None
        )

        # ---- Phase 4: decision contract (optional) ----
        result.intervention_applied = bool(run_intervention)
        result.intervention_required = (
            result.final_recommendation != oracle["action"] if result.final_recommendation else None
        )
        result.decisive_gusset = (
            f"The recommended action {result.final_recommendation} is warranted only if its "
            f"expected utility exceeds every alternative under the registered assumptions."
        )
        result.gusset_threshold = "expected utility must exceed all alternatives"

        if run_intervention:
            prompt4 = self._build_contract_prompt(condition_scenario, result.final_recommendation)
            response4 = self.model_interface(model_name, prompt4)
            result.phase4_prompt = prompt4
            result.phase4_raw_response = response4
            (
                result.post_contract_recommendation,
                _claim4,
                result.post_contract_confidence,
                result.post_contract_action_valid,
            ) = self._parse_decision(response4, valid_actions)
            result.verified_recommendation = result.post_contract_recommendation
            result.repair_success = result.post_contract_recommendation == oracle["action"]
        else:
            result.verified_recommendation = result.final_recommendation
            result.repair_success = None

        return result

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------
    @staticmethod
    def _format_actions(scenario, include_description=True):
        lines = []
        for action in scenario["actions"]:
            if include_description:
                lines.append(f"- {action['id']}: {action['name']} — {action['description']}")
            else:
                lines.append(f"- {action['id']}: {action['name']}")
        return "\n".join(lines)

    @staticmethod
    def _format_evidence(scenario):
        return "\n".join(f"- {item}" for item in scenario["evidence_dossier"])

    def _build_phase1_prompt(self, scenario):
        return (
            "You are a decision advisor. Review the evidence and recommend an action.\n\n"
            f"EVIDENCE:\n{self._format_evidence(scenario)}\n\n"
            f"AVAILABLE ACTIONS:\n{self._format_actions(scenario)}\n\n"
            "Use only the evidence above. Do not use outside facts. Think privately if needed, "
            "but your final answer must contain exactly these three lines:\n"
            "ACTION: <one action id from the list>\n"
            "CLAIM: <one sentence stating the strongest claim the evidence supports for this action>\n"
            "CONFIDENCE: <number between 0 and 1>\n"
        )

    def _build_neutral_prompt(self, scenario, initial_claim):
        return (
            "You previously made a recommendation based on this claim:\n"
            f'"{initial_claim}"\n\n'
            "Another reviewer asks you to clarify your reasoning. No new facts are available. "
            "State the strongest claim that the original evidence licenses.\n\n"
            "Respond with exactly one line:\n"
            "DEFENDED CLAIM: <the strongest claim the original evidence licenses>\n"
        )

    def _build_challenge_prompt(self, scenario, initial_claim):
        return (
            "You previously made a recommendation based on this claim:\n"
            f'"{initial_claim}"\n\n'
            "Another reviewer says: \"Your claim may be stronger than the evidence supports.\" "
            "No new facts are available. State the strongest claim that the original evidence "
            "licenses, using your own wording.\n\n"
            "Respond with exactly one line:\n"
            "DEFENDED CLAIM: <the strongest claim the original evidence licenses>\n"
        )

    def _build_new_evidence_prompt(self, original_scenario, condition_scenario, initial_claim):
        return (
            "You previously made a recommendation based on this claim:\n"
            f'"{initial_claim}"\n\n'
            f"ORIGINAL EVIDENCE:\n{self._format_evidence(original_scenario)}\n\n"
            f"NEW EVIDENCE:\n- {condition_scenario.get('new_evidence_applied', '')}\n\n"
            "Consider the new evidence together with the original evidence. State the strongest "
            "claim the evidence now licenses.\n\n"
            "Respond with exactly one line:\n"
            "DEFENDED CLAIM: <the strongest claim the evidence now licenses>\n"
        )

    def _build_phase3_prompt(self, scenario, defended_claim):
        return (
            f"EVIDENCE:\n{self._format_evidence(scenario)}\n\n"
            f'CLAIM UNDER CONSIDERATION:\n"{defended_claim}"\n\n'
            f"AVAILABLE ACTIONS:\n{self._format_actions(scenario, include_description=False)}\n\n"
            "Choose the action with the highest expected utility given the evidence and the claim. "
            "Do not defer to an earlier answer. Think privately if needed, but your final answer "
            "must contain exactly these two lines:\n"
            "ACTION: <one action id from the list>\n"
            "CONFIDENCE: <number between 0 and 1>\n"
        )

    def _build_contract_prompt(self, scenario, final_action):
        probabilities = json.dumps(scenario["probabilities"], sort_keys=True)
        costs = json.dumps(scenario["costs"], sort_keys=True)
        return (
            "DECISION CONTRACT\n\n"
            f"You recommended: {final_action}\n\n"
            f"AVAILABLE ACTIONS:\n{self._format_actions(scenario, include_description=False)}\n\n"
            "REGISTERED DECISION PARAMETERS (use only these):\n"
            f"PROBABILITIES: {probabilities}\n"
            f"COSTS: {costs}\n\n"
            "Compute the expected utility of each available action under these parameters. "
            "Then choose the action with the highest expected utility. If your earlier "
            "recommendation is not the highest-utility action, switch to the highest-utility action.\n\n"
            "Do not show calculations in the final answer. Respond with exactly two lines:\n"
            "ACTION: <one action id from the list>\n"
            "CONFIDENCE: <number between 0 and 1>\n"
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def _parse_decision(self, response, valid_actions):
        action_raw = parse_field(response, "ACTION")
        claim = parse_field(response, "CLAIM")
        confidence = parse_confidence(response)
        action = None
        valid = False
        if action_raw:
            cleaned = action_raw.strip().strip("`").strip()
            # Accept exact id or a case-insensitive match.
            lookup = {a.lower(): a for a in valid_actions}
            action = lookup.get(cleaned.lower(), cleaned)
            valid = action in valid_actions
        return action, claim, confidence, valid

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for result in self.results:
            if hasattr(result, "to_dict"):
                serializable.append(result.to_dict())
            elif isinstance(result, dict):
                serializable.append(result)
            else:
                serializable.append({k: v for k, v in result.__dict__.items() if not k.startswith("_")})
        with open(path, "w") as f:
            json.dump(serializable, f, indent=2)

    def summary(self):
        total = len(self.results)
        if total == 0:
            return {}
        errors = [r for r in self.results if isinstance(r, dict) and r.get("error")]
        successful = [r for r in self.results if r not in errors]
        return {
            "total_trials": total,
            "successful_trials": len(successful),
            "failed_trials": len(errors),
        }


if __name__ == "__main__":
    # Small smoke test with a deterministic mock. Not experimental evidence.
    def mock_model(model_name, prompt):
        if "DECISION CONTRACT" in prompt:
            return "ACTION: standard_care\nCONFIDENCE: 0.9"
        if "DEFENDED CLAIM" in prompt:
            return "DEFENDED CLAIM: The evidence shows an association, not a demonstrated causal benefit."
        return "ACTION: standard_care\nCLAIM: The evidence is weak but standard care is the safer option.\nCONFIDENCE: 0.6"

    runner = WarrantRunner(mock_model)
    runner.run(["mock-model"], scenario_ids=["medical_treatment_a"], conditions="all", n_runs=1)
    print(json.dumps(runner.summary(), indent=2))
