# Sprint log

**Sprint:** Apart Research AI x Epistemics, November 13–15, 2026
**Deadline:** November 15, 11:59 PM AoE (November 16, 12:59 PM Nigeria)

This log records what is new during the sprint. Anything not listed here is
covered by `PRE_EXISTING.md`.

## 2026-11-12 — Pre-kickoff preparation (disclosed as pre-existing)

- Reframed GUSSET around outcome validity rather than recommendation persistence.
- Added four-condition protocol and registered new-evidence variants.
- Replaced self-reported retreat with blinded two-task human annotation design.
- Added diagnostic-validity matrix with cluster bootstrap.
- Added Decision Receipts and independent verifier.

## 2026-11-13 — Sprint day 1

- [x] Confirm model access and rate limits.
- [x] Run live pilot under challenge condition (10 scenarios, 1 run each).
- [ ] Run no-challenge, neutral-clarification, and new-evidence controls (rate-limited; not completed).
- [x] Freeze annotation packet and register the analysis plan.
- [ ] Recruit two independent annotators (not completed; see Amendment A).

## 2026-11-14 — Sprint day 2

- [ ] Complete blinded initial-claim annotations by human annotators (not completed; LLM judge substituted).
- [ ] Complete blinded defended-claim annotations by human annotators (not completed; LLM judge substituted).
- [x] Complete blinded initial-claim ratings via LLM judge (`reports/llm_judge_initial.json`).
- [x] Complete blinded defended-claim ratings via LLM judge (`reports/llm_judge_defended.json`).
- [x] Merge initial + defended ratings (`reports/annotations_merged.json`).
- [x] Apply ratings to trial records (`reports/annotated.json`).
- [x] Run primary analysis (`reports/analysis.json`, `reports/analysis.md`).
- [x] Generate receipts for every reported trial (`reports/receipts/`).

## 2026-11-15 — Sprint day 3

- [x] Verify receipts independently (10/10 pass).
- [x] Check every number in the report against the analysis JSON.
- [x] Write limitations and ethics/dual-use section.
- [x] Rewrite report as win-oriented research paper (4 pages).
- [x] Submit.

## Data status

| Asset | Status | Notes |
|---|---|---|
| Mock pipeline | working | not evidence |
| Live NVIDIA pilot | complete | 10/10 scenarios, challenge condition |
| Human initial ratings | not completed | LLM judge substituted (see Amendment A) |
| Human defended ratings | not completed | LLM judge substituted (see Amendment A) |
| LLM-judge initial ratings | complete | `reports/llm_judge_initial.json` |
| LLM-judge defended ratings | complete | `reports/llm_judge_defended.json` |
| Receipts from live data | complete | 10/10 verified |
| Final report | submitted | 4 pages, `reports/GUSSET_report.pdf` |

## Methodological deviations

Human annotation was not completed within the sprint timeline. The submitted analysis uses a blinded LLM judge (`nvidia/nemotron-3.5-super-vl-120b-a12b`, same model family as the evaluated model) with one rating per item per task instead of two independent human annotators per task. This deviation is documented in `PREREGISTRATION.md` (Amendment A, 2026-11-15). Resulting judge-based diagnostic findings are classified as exploratory.
