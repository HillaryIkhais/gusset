# Sprint log

**Sprint:** Apart Research AI x Epistemics, November 13–15, 2026
**Deadline:** November 15, 11:59 PM AoE (November 16, 12:59 PM Nigeria)

This log records what is new during the sprint. Anything not listed here is
covered by `PRE_EXISTING.md`.

## 2026-11-13 — Sprint day 1

- [x] Confirm model access and rate limits.
- [x] Run live pilot under challenge condition (10 scenarios, 1 run each).
- [ ] Run no-challenge, neutral-clarification, and new-evidence controls (rate-limited; not completed).
- [x] Freeze annotation packet and register the analysis plan.
- [ ] Recruit two independent annotators (not completed; see Amendment A).
- [x] Complete blinded initial-claim ratings via LLM judge (`reports/llm_judge_initial.json`).
- [x] Complete blinded defended-claim ratings via LLM judge (`reports/llm_judge_defended.json`).
- [x] Merge initial + defended ratings (`reports/annotations_merged.json`).
- [x] Apply ratings to trial records (`reports/annotated.json`).
- [x] Run primary analysis (`reports/analysis.json`, `reports/analysis.md`).
- [x] Generate receipts for every reported trial (`reports/receipts/`).
- [x] Verify receipts independently (10/10 pass).
- [x] Check every number in the report against the analysis JSON.
- [x] Write limitations and ethics/dual-use section.
- [x] Rewrite report as win-oriented research paper (4 pages).
- [x] Submit (project ready; date to be recorded upon actual upload to Apart Research page).

## 2026-11-14 — Sprint day 2

- [ ] Complete blinded initial-claim annotations by human annotators (not completed; LLM judge substituted on day 1).
- [ ] Complete blinded defended-claim annotations by human annotators (not completed; LLM judge substituted on day 1).
- [ ] Compute inter-annotator agreement (not completed; requires two human annotators).
- [x] Fix Bottom line to scope result to nine-case pilot, not universal claim.

## 2026-11-14 — Sprint day 2

- [x] Replace universal headline with pilot-bound headline ('A nine-case pilot found two failure modes').
- [x] Clarify protocol: four conditions listed as designed vs executed; only `challenge_no_new_evidence` completed.
- [x] Bottom line: Sensitivity 0.0% pilot result, not a general conclusion about honesty evaluations.
- [x] Publish evidence/nine_item_records.json so reviewers can recompute the 2x2 matrix from the nine annotated records.
- [x] Fix README above-the-fold to match new headline and claim boundary.

## 2026-11-15 — Sprint day 3

- [x] Submit (project ready; date to be recorded upon actual upload to Apart Research page).
- [x] P0: Exact binomial confidence intervals for all diagnostic metrics (sensitivity, specificity, PPV, NPV, accuracy).
- [x] P0: Signed revision metric added (init_sev − defd_sev, not clipped to zero).
- [x] P0: Three-measurement framework documented (init_sev, defd_sev, gap_severity, regret).
- [x] P0: Uncertainty explicitly stated — nine-case pilot, single regret-positive observation.

## Data status

| Asset | Status | Notes |
|---|---|---|
| Mock pipeline | working | not evidence |
| Live NVIDIA pilot | complete | 10/10 scenarios, challenge condition |
| Human initial ratings | not completed | LLM judge substituted on day 1 (see Amendment A) |
| Human defended ratings | not completed | LLM judge substituted on day 1 (see Amendment A) |
| LLM-judge initial ratings | complete | `reports/llm_judge_initial.json` |
| LLM-judge defended ratings | complete | `reports/llm_judge_defended.json` |
| Receipts from live data | complete | 10/10 verified |
| Final report | complete | 4 pages, `reports/GUSSET_report.pdf` |
| Submission | pending | date to be recorded upon submission |
| Public demo fixtures | committed | `demo/fixtures/` — runs from clean clone |
| Evidence file | committed | `evidence/headline_results.json` |
| V1 evidence (committed) | `evidence/v1/` | annotated.json, llm_judge_*.json, analysis.json, annotation_ratings.json |
| V2 scenario set | committed | `data/scenarios/scenarios_v2.json` + `evidence/v2/SHA256SUMS` |
| V2 oracle | committed | `src/evaluation/oracle_v2.py` (corrected reference frames) |
| Scenario/oracle audit | committed | `evidence/scenario_oracle_audit.csv` |

## V2 Experiment Status

- V2 scenario definitions: committed (10 scenarios, corrected probabilities/costs)
- V2 oracle: committed (`src/evaluation/oracle_v2.py`, incremental reference frames)
- V2 receipts: not yet generated (requires live model runs)
- V2 annotation: not yet generated (requires human or LLM judge ratings)
- V2 analysis: not yet generated (requires V2 trial records)
- V2 experiment runnable via CLI: `PYTHONPATH=src python3 src/experiment/run_cli.py --scenario-file data/scenarios/scenarios_v2.json --conditions challenge_no_new_evidence`

## Methodological deviations

Human annotation was not completed within the sprint timeline. The submitted analysis uses a blinded LLM judge (`nvidia/nemotron-3.5-super-vl-120b-a12b`, same model family as the evaluated model) with one rating per item per task instead of two independent human annotators per task. This deviation is documented in `PREREGISTRATION.md` (Amendment A, 2026-11-13). Resulting judge-based diagnostic findings are classified as exploratory.

## Critical sample-size limitation (P0)

The pilot contains exactly **one regret-positive scenario** among nine annotated items (software_deployment_b). All sensitivity, PPV, and related proportions therefore have a denominator of 1, producing extremely wide confidence intervals (e.g., sensitivity 0.0% with 95% CI [0.0%–97.5%]). The residual-overstatement diagnostic (defd_sev >= 1) identifies the regret case with 100% sensitivity, but this is 1/1 and cannot be interpreted as evidence of predictive validity. All results from this pilot must be read as preliminary and hypothesis-generating only.

Thresholds (>=1, >=2, >=3) were preregistered and not selected post-hoc based on results. No threshold should be interpreted as validated on this sample size.

All nine scenarios are retained in the analysis; none are excluded or filtered for convenience.

## Methodological deviations

Human annotation was not completed within the sprint timeline. The submitted analysis uses a blinded LLM judge (`nvidia/nemotron-3.5-super-vl-120b-a12b`, same model family as the evaluated model) with one rating per item per task instead of two independent human annotators per task. This deviation is documented in `PREREGISTRATION.md` (Amendment A, 2026-11-13). Resulting judge-based diagnostic findings are classified as exploratory.

## Critical sample-size limitation (P0)

The pilot contains exactly **one regret-positive scenario** among nine annotated items (software_deployment_b). All sensitivity, PPV, and related proportions therefore have a denominator of 1, producing extremely wide confidence intervals (e.g., sensitivity 0.0% with 95% CI [0.0%–97.5%]). The residual-overstatement diagnostic (defd_sev >= 1) identifies the regret case with 100% sensitivity, but this is 1/1 and cannot be interpreted as evidence of predictive validity. All results from this pilot must be read as preliminary and hypothesis-generating only.

Thresholds (>=1, >=2, >=3) were preregistered and not selected post-hoc based on results. No threshold should be interpreted as validated on this sample size.

All nine scenarios are retained in the analysis; none are excluded or filtered for convenience.
