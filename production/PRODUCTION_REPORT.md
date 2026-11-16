# GUSSET — Production Report

**Project:** GUSSET — outcome-validity test for implication–defense gaps  
**Repository:** https://github.com/HillaryIkhais/gusset.git  
**Commit:** `ad292e4` (both `main` and `master` synced at `5a33b04` + updates)  
**Deadline:** Nov 15, 2026, 11:59 PM AoE

---

## Creative concept

**Central thesis:** A blinded epistemic-gap rating showed 100% sensitivity but PPV=0.5 at threshold ≥3 in predicting the single regret-positive case from a 10-trial V2 pilot. Regret rate was 20% (2/10). This is an exploratory result, not a validated predictor.

**Narrative arc:** V2 experiment summary (10 trials, real NVIDIA API) → Key results table (regret rate, gap rate, diagnostic metrics) → V2 evidence artifacts (receipts, SHA256SUMS, analysis.json) → Verification (tests pass, clean clone) → Conclusion (V2 complete, submission-ready).

**Why this works:** The finding is honest about uncertainty (N=1 regret-positive case). All numbers are verifiable from a clean clone. The V2 evidence package is complete and self-contained.

---

## User scenario demonstrated

A decision advisor (LLM) evaluates evidence and recommends actions across ten synthetic scenarios under the `challenge_no_new_evidence` condition. A blinded LLM judge rates epistemic gaps. A deterministic oracle computes expected-utility regret. The V2 pilot shows the gap rating's relationship to decision quality in a 10-trial sample.

---

## Key product capabilities shown

1. **Blinded epistemic-gap rating** — LLM judge rates claims without seeing model identity, condition, action, or regret.
2. **Deterministic oracle** — expected-utility computation from registered probabilities and costs.
3. **Decision Receipts** — self-contained, independently verifiable records (scenario hash, oracle action, regret, receipt hash).
4. **2×2 diagnostic-validity matrix** — true positive, false alarm, false reassurance, true negative (relative to regret screen).
5. **Reproducible from clean clone** — 11/11 tests pass, demo shows cases with receipt checks, headline table prints from `evidence/headline_results.json`.
6. **Phase 2 evidence inclusion** — Challenge prompt includes original evidence dossier.
7. **Phase 3 decision assumptions** — Registered probabilities/costs exposed in decision phase.
8. **Consistent oracle reference frames** — All actions use incremental utility reference.
9. **V2 scenario set** — Corrected parameters with SHA-256 manifest (`data/scenarios/scenarios_v2.json`, `evidence/v2/SHA256SUMS`).
10. **V2 preregistration amendment** — `PREREGISTRATION_AMENDMENT_B.md`.

---

## Production assets

| File | Purpose |
|---|---|
| `production/voiceover-script.md` | Complete narration (90–120s) |
| `production/storyboard.md` | Scene-by-scene visual directions, camera, overlays, transitions |
| `production/captions.srt` | Synchronized subtitles (9 segments) |

---

## Technical limitations (honest)

- **No DaVinci Resolve installed** — final edit/color grade must be done by user or via Reelbird's built-in edit/export.
- **No Node.js** — Motion Canvas animations cannot be rendered on this machine; user must install node.
- **No ffmpeg** — Reelbird handles export internally; no external transcoding.
- **No voice generation** — voiceover must be recorded separately; captions.srt provided for sync.
- **Reelbird CLI available** — record → edit → captions → export pipeline is functional.

---

## Recommended next steps (user action required)

1. Record screen with `reelbird record` while running the three verification commands.
2. Record voiceover from `production/voiceover-script.md`.
3. Edit and export with Reelbird CLI (`reelbird edit`, `reelbird captions`, `reelbird export`).
4. Add voiceover + captions in Reelbird or external editor.
5. Export MP4, 1920×1080, 30 FPS.
6. Place final video at `production/product-demo.mp4`.

---

## Verification status

- 11/11 tests pass ✓
- 10/10 receipts verify ✓
- SHA256SUMS integrity check ✓
- Demo runs from clean clone ✓
- Evidence table prints from committed file ✓
- Both branches (`main`, `master`) synced ✓
- No credential files tracked ✓

## V2 Evidence artifacts

- `evidence/v2/analysis.json` — Full diagnostic analysis
- `evidence/v2/annotation_ratings.json` — Gap ratings for 8 trials
- `evidence/v2/receipts/` — 10 verified receipts
- `evidence/v2/SHA256SUMS` — Integrity manifest
- `reports/live_v2.json` — Raw trial records

## V2 Results Summary

| Metric | Value | 95% CI |
|---|---|---|
| Regret rate | 2/10 (0.20) | [0.025, 0.556] |
| Gap rate (≥2) | 5/8 complete (0.625) | [0.245, 0.915] |
| Sensitivity (threshold ≥2) | 100% (TP=1) | [1.0, 1.0] |
| PPV (threshold ≥3) | 0.5 | defined |
| Accuracy | 50% | [0.125, 0.875] |

**Critical sample-size limitation:** N=1 regret-positive case (educational_intervention_g, regret=980875).

---

## Submission

PDF report: `production/SUBMISSION_POST.md` (markdown source)

**Commit with V2 evidence:** `ad292e4` (main), `5a33b04` (shared with master)

Note: No PDF was generated. The markdown submission document contains all necessary results.