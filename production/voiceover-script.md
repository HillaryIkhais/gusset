# GUSSET — Voiceover Script

**Target runtime:** 90–120 seconds  
**Tone:** Conversational, confident, natural. Intelligent person explaining something worth paying attention to. Not corporate, not AI-assistant, not advertisement.

---

## [0:00–0:12] — Opening hook

**Visual:** Terminal screen. A model's output scrolling. Then a hard cut to two numbers side by side.

**Narration:**
"A model can sound perfectly consistent. It can defend its claim, retreat gracefully, look honest. And still choose the wrong action."

---

## [0:12–0:25] — The V2 experiment

**Visual:** Two case cards slide in. Left: "educational_intervention_g — Gap=1, Regret=980875". Right: "cybersecurity_investment_j — Gap=2, Regret=0".

**Narration:**
"In our V2 experiment with 10 real trials, we found two contrasting outcomes. One scenario shows a gap under the threshold but massive regret — 980 thousand utility units. Another shows a flagged gap but zero regret. Same evaluator, same protocol, opposite outcomes."

---

## [0:25–0:38] — The question

**Visual:** The GUSSET logo mark (simple text treatment). The question fades in below it.

**Narration:**
"So does an honesty rating actually predict decision quality? GUSSET was built to answer that — not with an argument, but with an experiment."

---

## [0:38–0:55] — V2 results

**Visual:** Key results table fills in. Regret rate 20%, gap rate 62.5%, sensitivity 100%, PPV 0.5 at threshold >=3.

**Narration:**
"Across ten trials from the NVIDIA API, regret occurred in 20% of decisions. The gap measured 62.5% of cases. At threshold two and three, every regret case had a gap above the threshold — that's 100% sensitivity. But with only one regret-positive observation, PPV is limited to 0.5 at threshold three."

**On-screen text:** "Regret rate: 20% | Sensitivity: 100% | PPV: 0.5 | N=1 positive"

---

## [0:55–1:10] — Verification

**Visual:** Three commands run in sequence: tests, receipts, evidence table. All green.

**Narration:**
"Ten receipts verify with SHA256SUMS integrity check. Eleven tests pass. The evidence table prints straight from the committed analysis file. Clean clone. No setup. No secrets."

**On-screen text:** "tests pass | 10/10 receipts | evidence v2"

---

## [1:10–1:22] — Critical limitation

**Visual:** The N=1 regret-positive case highlighted.

**Narration:**
"With only one regret-positive observation, all confidence intervals are extremely wide. Sensitivity hits 100% because that single case was caught. But PPV at threshold three is 0.5 — half the flagged cases were false alarms. This is an exploratory pilot result."

**On-screen text:** "N=1 regret-positive | Cannot establish validation"

---

## [1:22–1:35] — Conclusion

**Visual:** The repo URL. V2 evidence artifacts listed: receipts, SHA256SUMS, analysis.json.

**Narration:**
"An honesty rating passing doesn't mean the decision is good. And a model flagged for an epistemic gap isn't necessarily making a bad decision. They're different measurements. Measure them separately."

**On-screen text:** "github.com/HillaryIkhais/gusset.git"

---

## [1:35–1:45] — End card

**Visual:** Fade to black. Repo URL remains.

*(Total target: ~105 seconds, within the 90–150 second range.)*

---

## Claim discipline for narration

| Statement | Evidence class |
|---|---|
| Tests pass, receipts verify, SHA256SUMS check | `enforced` |
| 10/10 receipts verified, 11/11 tests pass | `demonstrated` |
| Regret rate 20%, sensitivity 100%, PPV 0.5, N=1 positive | `measured` |
| Human-annotator validation, cross-family judge, repeated runs | `future work` — state "not done", never imply done |