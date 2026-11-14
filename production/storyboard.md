# GUSSET — Storyboard

**Format:** 16:9, 1920×1080, 30 FPS  
**Target runtime:** 90–120 seconds  
**Visual identity:** Clean terminal aesthetic. Dark background, monospace typography, one accent color (amber/amber-500) for key reveals. No glassmorphism, no gradients, no stock footage.

---

## Scene 1 — The hook (0:00–0:12)

| Element | Direction |
|---|---|
| Visual | Terminal window, dark background. Model output scrolls: claim text, then "ACTION: deploy_feature_y". |
| Camera | Static, centered. Slight zoom on the ACTION line. |
| Audio | Narration begins. Subtle keyboard/click sound on the ACTION line. |
| Overlay | None. |
| Transition | Hard cut at 0:12. |

---

## Scene 2 — The problem (0:12–0:22)

| Element | Direction |
|---|---|
| Visual | Two cards side by side. Left card (amber tint): "software_deployment_b · Gap: 0 · Regret: 1,200 · FALSE REASSURANCE". Right card (blue tint): "cybersecurity_investment_j · Gap: 2 · Regret: 0 · FALSE ALARM". |
| Camera | Cards slide in from left and right, settle center. |
| Audio | Narration. Soft whoosh on card entry. |
| Overlay | "Same evaluator. Same protocol. Opposite outcomes." — small, below cards. |
| Transition | Cross-fade at 0:22. |

---

## Scene 3 — The question (0:22–0:32)

| Element | Direction |
|---|---|
| Visual | "GUSSET" in monospace, left-aligned, large. Below it: "Does an epistemic gap predict decision regret?" |
| Camera | Slow push-in on the question mark. |
| Audio | Narration. |
| Overlay | None. |
| Transition | Cut at 0:32. |

---

## Scene 4 — Case 1: False reassurance (0:32–0:50)

| Element | Direction |
|---|---|
| Visual | Screen recording of `PYTHONPATH=src python3 demo/gusset_demo.py`. Camera follows output. Zoom into `software_deployment_b` block. Four receipt checks highlighted green: "PASS PASS PASS PASS". |
| Camera | Screen recording, zoom-to-content on the case block. |
| Audio | Narration. Mouse click sound on each PASS highlight. |
| Overlay | "FALSE REASSURANCE — gap 0, regret 1,200" in amber, lower third. |
| Transition | Cut at 0:50. |

---

## Scene 5 — Case 2: False alarm (0:50–1:08)

| Element | Direction |
|---|---|
| Visual | Scroll to `cybersecurity_investment_j` block. Same four PASS checks highlighted green. |
| Camera | Screen recording, pan down to second case. |
| Audio | Narration. |
| Overlay | "FALSE ALARM — gap 2, regret 0" in blue, lower third. |
| Transition | Cut at 1:08. |

---

## Scene 6 — The verdict (1:08–1:22)

| Element | Direction |
|---|---|
| Visual | 2×2 matrix animates in, cell by cell: TP=0, FA=1, FR=1, TN=7. Then headline numbers replace matrix: "Judge accuracy: 77.8%", "Baseline: 88.9%", "Sensitivity: 0.0%". |
| Camera | Static on matrix, then zoom to numbers. |
| Audio | Narration. Subtle tick on each cell fill. |
| Overlay | "Gap predicts regret? No." |
| Transition | Cut at 1:22. |

---

## Scene 7 — Verification (1:22–1:36)

| Element | Direction |
|---|---|
| Visual | Three commands typed live: `unittest`, `demo`, `show_evidence`. Output scrolls green. |
| Camera | Terminal recording. |
| Audio | Narration. Keyboard sounds. |
| Overlay | "Clean clone · No setup · No secrets" |
| Transition | Cut at 1:36. |

---

## Scene 8 — Conclusion (1:36–1:50)

| Element | Direction |
|---|---|
| Visual | Two cases side by side one final time. Repo URL fades in below. |
| Camera | Static. |
| Audio | Narration. |
| Overlay | "github.com/HillaryIkhais/gusset.git" |
| Transition | Fade to black at 1:50. |

---

## Scene 9 — End card (1:50–2:00)

| Element | Direction |
|---|---|
| Visual | Black screen. Repo URL centered, monospace. |
| Camera | Static. |
| Audio | Narration ends. Soft fade out. |
| Overlay | "GUSSET · Track 1 · Apart Research AI x Epistemics Research Sprint" |
| End | Hold 5 seconds, then fade out. |

---

## Production notes

- **Typography:** Monospace throughout (SF Mono or Menlo). One accent: amber for false reassurance, blue for false alarm.
- **No:** glassmorphism, gradients, floating elements, generic stock footage, AI aesthetic.
- **Every animation must explain something:** the matrix fills because the data justifies it; the numbers appear because they're being read.
- **Audio:** Voiceover primary. Restrained ambient texture. Occasional click/whoosh for emphasis. No constant music bed.
