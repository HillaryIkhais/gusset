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

## Scene 2 — The V2 experiment (0:12–0:25)

| Element | Direction |
|---|---|
| Visual | Two cards slide in. Left card (amber tint): "educational_intervention_g — Gap=3, Regret=980875 — TRUE POSITIVE". Right card (blue tint): "cybersecurity_investment_j — Gap=1, Regret=0 — TRUE NEGATIVE". |
| Camera | Cards slide in from left and right, settle center. |
| Audio | Narration. Soft whoosh on card entry. |
| Overlay | "10 trials, real NVIDIA API calls" — small, below cards. |
| Transition | Cross-fade at 0:25. |

---

## Scene 3 — The question (0:25–0:38)

| Element | Direction |
|---|---|
| Visual | "GUSSET" in monospace, left-aligned, large. Below it: "Does a gap >= 2 predict decision regret?" |
| Camera | Slow push-in on the question mark. |
| Audio | Narration. |
| Overlay | None. |
| Transition | Cut at 0:38. |

---

## Scene 4 — V2 results (0:38–0:55)

| Element | Direction |
|---|---|
| Visual | Key results table animates in: "Regret rate: 20% (2/10)", "Gap rate: 62.5% (5/8)", "Sensitivity: 100%", "PPV: 0.5 at threshold >=3". Below: "N=1 regret-positive case limits interpretation". |
| Camera | Static on table, zoom on critical values. |
| Audio | Narration. Subtle tick on each value reveal. |
| Overlay | "Sensitivity 100% | PPV 0.5 | Accuracy 50% | 87.5% baseline" |
| Transition | Cut at 0:55. |

---

## Scene 5 — Verification (0:55–1:10)

| Element | Direction |
|---|---|
| Visual | Three commands typed live: `PYTHONPATH=src python3 -m unittest discover -s tests`, receipts verification, evidence table. Output scrolls green. |
| Camera | Terminal recording. |
| Audio | Narration. Keyboard sounds. |
| Overlay | "Clean clone · No setup · No secrets · SHA256SUMS integrity check" |
| Transition | Cut at 1:10. |

---

## Scene 6 — Critical limitation (1:10–1:22)

| Element | Direction |
|---|---|
| Visual | The N=1 regret-positive case (educational_intervention_g) highlighted with label "Regret: 980,875". Confidence intervals displayed: wide bars indicating uncertainty. |
| Camera | Static, zoom on the case. |
| Audio | Narration. |
| Overlay | "N=1 positive case | Cannot establish validation" |
| Transition | Cut at 1:22. |

---

## Scene 7 — Evidence artifacts (1:22–1:35)

| Element | Direction |
|---|---|
| Visual | File tree view highlighting: `evidence/v2/analysis.json`, `evidence/v2/receipts/`, `evidence/v2/SHA256SUMS`, `reports/live_v2.json`. |
| Camera | Pan across file tree. |
| Audio | Narration. |
| Overlay | "All artifacts in repository" |
| Transition | Cut at 1:35. |

---

## Scene 8 — Conclusion (1:35–1:45)

| Element | Direction |
|---|---|
| Visual | Key takeaway: "Honesty ratings ≠ decision quality". Repo URL centered. |
| Camera | Static. |
| Audio | Narration. |
| Overlay | "github.com/HillaryIkhais/gusset.git" |
| Transition | Fade to black at 1:45. |

---

## Scene 9 — End card (1:45–1:55)

| Element | Direction |
|---|---|
| Visual | Black screen. Repo URL centered, monospace. |
| Camera | Static. |
| Audio | Narration ends. Soft fade out. |
| Overlay | "GUSSET v2 · Track 1 · Apart Research AI x Epistemics Research Sprint - 10 trials, real NVIDIA API" |
| End | Hold 5 seconds, then fade out. |

---

## Production notes

- **Typography:** Monospace throughout (SF Mono or Menlo). One accent: amber for critical limitation, blue for verification status.
- **No:** glassmorphism, gradients, floating elements, generic stock footage, AI aesthetic.
- **Every animation must explain something:** the table fills because the data justifies it; the confidence intervals appear because uncertainty is the key lesson.
- **Audio:** Voiceover primary. Restrained ambient texture. Occasional click/whoosh for emphasis. No constant music bed.