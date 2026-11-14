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
- [ ] Submit (pending; date to be recorded upon submission).

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

- [ ] Submit (date to be recorded upon submission).

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

## Methodological deviations

Human annotation was not completed within the sprint timeline. The submitted analysis uses a blinded LLM judge (`nvidia/nemotron-3.5-super-vl-120b-a12b`, same model family as the evaluated model) with one rating per item per task instead of two independent human annotators per task. This deviation is documented in `PREREGISTRATION.md` (Amendment A, 2026-11-13). Resulting judge-based diagnostic findings are classified as exploratory.
