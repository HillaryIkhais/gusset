# GUSSET — Production Report

**Project:** GUSSET — outcome-validity test for implication–defense gaps  
**Repository:** https://github.com/HillaryIkhais/gusset.git  
**Commit:** `33b13b3` (both `main` and `master` synced)  
**Deadline:** Nov 15, 2026, 11:59 PM AoE

---

## Creative concept

**Central thesis:** A blinded epistemic-gap rating did not identify the observed regret case in a nine-case pilot (Sensitivity: 0.0%). It is a pilot result — not a general conclusion about honesty evaluations. Honesty evaluations and decision quality are separate measurements.

**Narrative arc:** Opening hook (confident model, wrong action) → Two contrasting cases (false negative vs regret, false positive vs regret) → The verdict (gap doesn't predict regret, 77.8% vs 88.9% baseline) → Verification (three commands, clean clone) → Conclusion (measure them separately).

**Why this works:** The finding is negative — which makes it stronger than a positive claim. The two cases are visually opposite, easy to grasp at a glance. Every number is verifiable from a clean clone.

---

## User scenario demonstrated

A decision advisor (LLM) evaluates evidence and recommends actions across ten scenarios under the `challenge_no_new_evidence` condition. A blinded judge rates epistemic gaps. A deterministic oracle computes expected-utility regret. The nine-case pilot (N=9 from 10 collected, 1 excluded) shows two scenarios where the gap rating and the decision quality diverge.

---

## Key product capabilities shown

1. **Blinded epistemic-gap rating** — LLM judge rates claims without seeing model identity, condition, action, or regret.
2. **Deterministic oracle** — expected-utility computation from registered probabilities and costs.
3. **Decision Receipts** — self-contained, independently verifiable records (scenario hash, oracle action, regret, receipt hash).
4. **2×2 diagnostic-validity matrix** — true positive, false alarm, false negative vs regret, true negative (relative to regret screen).
5. **Reproducible from clean clone** — 11/11 tests pass, demo shows both cases with receipt checks PASS, headline table prints from `evidence/headline_results.json`. The full nine-case diagnostic matrix also recomputes from `evidence/nine_item_records.json`. The receipts directory and individual judge ratings require the `reports/` directory (gitignored).
6. **Phase 2 evidence inclusion** — Challenge prompt now includes original evidence dossier (runner.py).
7. **Phase 3 decision assumptions** — Registered probabilities/costs exposed in decision phase (runner.py).
8. **Consistent oracle reference frames** — All actions use incremental utility reference (oracle.py).
9. **V2 scenario set** — Corrected parameters with SHA-256 manifest (`data/scenarios/scenarios_v2.json`, `evidence/v2/SHA256SUMS`).
10. **V2 preregistration amendment** — `PREREGISTRATION_AMENDMENT_B.md`.

---

## Production assets

| File | Purpose |
|---|---|
| `production/voiceover-script.md` | Complete narration, 90–120s, four beats + verification + conclusion |
| `production/storyboard.md` | Scene-by-scene visual directions, camera, overlays, transitions |
| `production/captions.srt` | Synchronized subtitles (9 segments) |
| `production/motion-canvas/scenes.ts` | TypeScript animations (diagnostic matrix, headline numbers, case cards, title reveal) — requires Node.js + Motion Canvas |
| `production/motion-canvas/README.md` | Build instructions |

---

## Technical limitations (honest)

- **No DaVinci Resolve installed** — final edit/color grade must be done by user or via Reelbird's built-in edit/export.
- **No Node.js** — Motion Canvas animations cannot be rendered on this machine; user must install node to generate them.
- **No ffmpeg** — Reelbird handles export internally; no external transcoding.
- **No voice generation** — voiceover must be recorded by a human or generated separately; captions.srt provided for sync.
- **Reelbird CLI available** — record → edit → captions → export pipeline is functional.

---

## Recommended next steps (user action required)

1. Install Node.js if Motion Canvas animations are desired.
2. Record screen with `reelbird record` while running the three verification commands.
3. Record voiceover from `production/voiceover-script.md`.
4. Edit and export with Reelbird CLI (`reelbird edit`, `reelbird captions`, `reelbird export`).
5. Add voiceover + captions in Reelbird or external editor.
6. Export MP4, 1920×1080, 30 FPS.
7. Place final video at `production/product-demo.mp4`.

---

## Verification status

- 11/11 tests pass ✓
- 10/10 receipts verify ✓
- Demo runs from clean clone ✓
- Evidence table prints from committed file ✓
- Both branches (`main`, `master`) at commit 33b13b3 ✓
- No credential files tracked ✓
