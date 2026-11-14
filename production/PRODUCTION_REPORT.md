# GUSSET — Production Report

**Project:** GUSSET — outcome-validity test for implication–defense gaps  
**Repository:** https://github.com/HillaryIkhais/gusset.git  
**Commit:** 9b961b4 (both `main` and `master` synced)  
**Deadline:** Nov 15, 2026, 11:59 PM AoE

---

## Creative concept

**Central thesis:** Honesty evaluations and decision quality are not interchangeable. A model can pass an epistemic-gap check and still make a bad decision; another can be flagged for a gap and still make the right one.

**Narrative arc:** Opening hook (confident model, wrong action) → Two contrasting cases (false reassurance, false alarm) → The verdict (gap doesn't predict regret, 77.8% vs 88.9% baseline) → Verification (three commands, clean clone) → Conclusion (measure them separately).

**Why this works:** The finding is negative — which makes it stronger than a positive claim. The two cases are visually opposite, easy to grasp at a glance. Every number is verifiable from a clean clone.

---

## User scenario demonstrated

A decision advisor (LLM) evaluates evidence and recommends actions across ten scenarios. A blinded judge rates epistemic gaps. A deterministic oracle computes expected-utility regret. The video shows two specific scenarios where the gap rating and the decision quality diverge.

---

## Key product capabilities shown

1. **Blinded epistemic-gap rating** — LLM judge rates claims without seeing model identity, condition, action, or regret.
2. **Deterministic oracle** — expected-utility computation from registered probabilities and costs.
3. **Decision Receipts** — self-contained, independently verifiable records (scenario hash, oracle action, regret, receipt hash).
4. **2×2 diagnostic-validity matrix** — true positive, false alarm, false reassurance, true negative.
5. **Reproducible from clean clone** — tests, demo, evidence table all run with no setup.

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
- Both branches (`main`, `master`) at commit 9b961b4 ✓
- No credential files tracked ✓
