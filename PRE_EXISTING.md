# Pre-existing work disclosure

**Disclosure date:** 2026-11-12, before the November 13–15 sprint kickoff.

Apart Research allows building on existing work but requires disclosure of what was already built. This file separates pre-existing implementation from sprint-time work.

## Existed before the sprint

- `data/scenarios/scenarios.json` — ten controlled decision scenarios with evidence dossiers, actions, probabilities, costs, and declared optima.
- `src/evaluation/oracle.py` — deterministic expected-utility oracle.
- `src/experiment/runner.py` — multi-turn experiment runner and raw transcript preservation.
- `src/experiment/model_clients.py` — provider clients, including the NVIDIA streaming client.
- `src/experiment/run_cli.py` — command-line entry point.
- `scripts/run_live.py` — live-run helper that loads the key from `.env`.
- `src/annotation/annotate.py` — annotation tool skeleton.
- `src/analysis/analyze.py` — analysis skeleton with exact confidence intervals.
- `src/receipts/` — Decision Receipt builder, generator, and verifier.
- `src/reports/pdf_report.py` and `src/reports/generate_report.py` — report generators.
- `demo/decoupling_demo.py` — single-scenario demonstration.
- `README.md` — project description.
- `PREREGISTRATION.md`, `SCENARIO_AUDIT.md`, and `tests/test_pipeline.py` — analysis plan, oracle audit, and tests added before kickoff.

The original headline was: *when a model retreats from its evidence, does its recommendation retreat with it?*

## Built on 2026-11-12, before kickoff

These changes are also pre-existing for disclosure purposes:

- Reframed the research question from recommendation persistence to **outcome validity**: does a human-rated implication–defense gap predict decision regret?
- Added four conditions: `no_challenge`, `neutral_clarification`, `challenge_no_new_evidence`, and `new_evidence`.
- Added registered new-evidence variants and condition-specific oracle recomputation.
- Replaced the leading challenge prompt with a neutral challenge that does not ask for a yes/no acknowledgment.
- Replaced the self-reported "claim narrowed" proxy with separate blinded human ratings of the initial and defended claims.
- Added the 2×2 diagnostic-validity matrix, cluster bootstrap by scenario, and condition breakdowns.
- Added Decision Receipts and an independent verifier that recomputes utilities from the registered scenario.
- Added the `PRE_EXISTING.md` manifest and `SPRINT_LOG.md`.

## Expected sprint-time work

- Live model runs under the registered conditions.
- Independent blinded human annotation by at least two annotators per task.
- Agreement analysis and adjudication.
- Analysis of real annotated records.
- Receipt generation from real runs.
- Research report, walkthrough, and submission materials.

## Integrity notes

- `reports/live_run.json` contains earlier mock outputs and must not be presented as live evidence.
- `reports/annotations.json` contains simulated annotations and must not be presented as human evidence.
- The oracle establishes optimality only under the registered synthetic assumptions.
- The exposed NVIDIA key from earlier development must be revoked and replaced. It must not appear in the repository or the report.

## Manifest

`pre_existing_manifest.json` contains SHA-256 hashes for the pre-sprint source tree. Generated reports, live data, and receipts are excluded because they are outputs, not pre-existing implementation.
