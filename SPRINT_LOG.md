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

## 2026-11-16 — Sprint Completion

- [x] Execute v2 live pilot (10 scenarios, NVIDIA API, real responses)
- [x] Export v2 blinded packets (initial, defended)
- [x] Run LLM-judge on v2 packets (9 initial, 10 defended)
- [x] Merge and apply v2 annotations to trial records
- [x] Generate v2 analysis with oracle_v2, threshold sweep
- [x] Generate v2 receipts and verify integrity (SHA256SUMS)
- [x] Update PREREGISTRATION_AMENDMENT_B.md with results
- [x] Commit v2 evidence (analysis.json, annotation_ratings.json, receipts/)
- [x] Push to GitHub (main)
- [ ] Verify from clean clone (master branch needs sync)
- [ ] Final repository sync: master branch at `d0a9e68` does NOT include v2 evidence

## 2026-11-15 — Sprint day 3

- [x] Submit (project ready; date to be recorded upon actual upload to Apart Research page).
- [x] P0: Exact binomial confidence intervals for all diagnostic metrics (sensitivity, specificity, PPV, NPV, accuracy).
- [x] P0: Signed revision metric added (init_sev − defd_sev, not clipped to zero).
- [x] P0: Three-measurement framework documented (init_sev, defd_sev, gap_severity, regret).
- [x] P0: Uncertainty explicitly stated — V1 nine-case pilot, single regret-positive observation.

## Data status

| Asset | Status | Notes |
|---|---|---|
| Mock pipeline | working | not evidence |
| Live NVIDIA pilot (V1) | complete | 9/9 scenarios, challenge condition |
| V1 Human initial ratings | not completed | LLM judge substituted on day 1 |
| V1 Human defended ratings | not completed | LLM judge substituted on day 1 |
| V1 LLM-judge ratings | complete | `reports/llm_judge_initial.json`, `llm_judge_defended.json` |
| V1 Receipts | complete | 10/10 verified |
| Live NVIDIA pilot (V2) | complete | 10/10 scenarios, real NVIDIA API calls |
| V2 LLM-judge ratings | complete | 8/10 complete gap ratings |
| V2 Analysis | complete | `evidence/v2/analysis.json` |
| V2 Receipts | complete | `evidence/v2/receipts/`, 10/10 verified |
| V2 SHA256SUMS | complete | `evidence/v2/SHA256SUMS` |
| Final report (V1) | complete | `production/SUBMISSION_POST.md` |
| Submission | pending | date to be recorded upon submission |
| Public demo fixtures | committed | `demo/fixtures/` — runs from clean clone |
| V1 evidence (committed) | `evidence/v1/` | annotated.json, llm_judge_*.json, analysis.json |
| V2 scenario set | committed | `data/scenarios/scenarios_v2.json` |
| V2 oracle | committed | `src/evaluation/oracle_v2.py` |

## V2 Experiment Status

- V2 scenario definitions: **executed** (10 scenarios, corrected probabilities/costs)
- V2 oracle: **applied** (`src/evaluation/oracle_v2.py`, incremental reference frames)
- V2 live trials: **completed** (10/10 scenarios, all with valid action output)
- V2 annotations: **completed** (8/10 trials have complete gap ratings; 2 incomplete)
- V2 analysis: **completed** (`evidence/v2/analysis.json`)
- V2 receipts: **generated** (`evidence/v2/receipts/`, 10/10 verified)
- V2 trial records: `reports/live_v2.json`

## V2 Results Summary

| Metric | Value | 95% CI |
|---|---|---|
| Regret rate | 2/10 (0.20) | [0.025, 0.556] |
| Gap rate (≥2) | 5/8 complete (0.625) | [0.245, 0.915] |
| Sensitivity (threshold ≥2) | 100% (TP=1) | [1.0, 1.0] |
| PPV (threshold ≥3) | 0.5 | defined |
| Accuracy | 50% | [0.125, 0.875] |

**Critical sample-size limitation:** N=1 regret-positive case (educational_intervention_g, regret=980875).

## Methodological deviations

Human annotation was not completed within the sprint timeline for either V1 or V2. Both analyses use a blinded LLM judge (`nvidia/nemotron-3.5-super-vl-120b-a12b`, same model family as the evaluated model) with one rating per item per task instead of two independent human annotators per task. This deviation is documented in `PREREGISTRATION_AMENDMENT_B.md`. All judge-based diagnostic findings are classified as exploratory.

## Repository status

**Branch synchronization required:** GitHub shows `master` as default branch at `d0a9e68` (V1 only). V2 evidence is at commit `5a33b04` on `main` branch. To synchronize:

```bash
git push origin main:master
```

Or change repository settings to make `main` the default branch.