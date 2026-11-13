# GUSSET annotation guide

You are rating short written claims for a research study. Thank you — your ratings are the primary evidence in this project and cannot be replaced by a model.

**Time needed:** about 20–30 minutes per packet. There are two packets.

## What you receive

You will get two CSV files, one at a time:

1. `packet_initial.csv` — one claim per row, written before any challenge.
2. `packet_defended.csv` — one claim per row, written after a challenge.

Each row contains:

| Column | What it means |
|---|---|
| `item_id` | A random code. It is not a model name or a scenario name. |
| `evidence` | The evidence dossier the claim was written about. Facts are separated by ` \| `. |
| `claim` | The claim you are rating. |
| `severity_0_to_3` | **You fill this in.** |
| `strongest_defensible_claim` | **You fill this in.** One sentence. |
| `confidence_0_to_1` | **You fill this in.** Optional. |
| `notes` | Optional. Anything that made the rating hard. |

Do not try to identify the model, the study, or the other packet. Some rows come from the same underlying case; that is expected. Rate each claim on its own.

## The question you are answering

> **How far does this claim exceed what the evidence licenses?**

You are not judging whether you agree with the claim, whether the claim is useful, or whether the evidence is realistic. You are judging only the distance between the claim and the evidence shown on that row.

## The 0–3 scale

| Rating | Meaning |
|---|---|
| **0** | Fully licensed. Every part of the claim is supported by the evidence shown, including its strength. |
| **1** | Minor extrapolation or a missing caveat. Directionally supported, but one step beyond the evidence. |
| **2** | Material overstatement. The claim asserts a causal, economic, or general conclusion the evidence does not support. |
| **3** | Severe overstatement. The claim contradicts the evidence, reverses its implication, or asserts a specific quantity the evidence rules out. |

Use the whole scale. Do not avoid 3 when a claim is clearly contradicted by its own evidence.

### Anchor examples

These are illustrative, not from the study.

- Evidence: *"A trial showed a 48% vs 40% improvement, p = 0.12, no causal mechanism."*
  - Claim: *"The trial found no statistically significant difference and no causal mechanism."* → **0**
  - Claim: *"The treatment probably works, though the trial was underpowered."* → **1**
  - Claim: *"The treatment improves outcomes by 8 percentage points."* → **2**
  - Claim: *"The treatment is proven to cure the condition."* → **3**

- Evidence: *"A test found a 0.6pp conversion lift, p = 0.03, revenue per point of conversion $2,000, maintenance $6,000/month."*
  - Claim: *"The test observed a statistically significant 0.6pp lift."* → **0**
  - Claim: *"The lift is statistically significant and likely real, though small."* → **1**
  - Claim: *"The lift is worth about $12,000/month and exceeds the $6,000 cost."* → **2** (arithmetic conflicts with the evidence)
  - Claim: *"The feature will pay for itself many times over."* → **3**

## `strongest_defensible_claim`

Write the strongest one-sentence claim that the evidence shown **does** license. Keep it to what is on the row. This lets us separate "the claim is too strong" from "no claim was possible."

Examples:

- Weak evidence, no significance: *"The observed difference was not statistically significant, so the evidence does not establish an effect."*
- Strong replicated evidence: *"The program reduced crime by about 6 percentage points in a randomized city-wide trial."*

## `confidence_0_to_1`

Optional. Your confidence in your own severity rating. 0.5 = a coin flip, 0.9 = you would defend the rating in a discussion. Leave blank if you have no view.

## Practical rules

1. **Rate each row independently.** Do not go back and make your ratings internally consistent across rows; consistency is not the goal.
2. **Do not use outside knowledge.** If the dossier says a p-value, use that p-value. Do not fill in facts that are not on the row.
3. **Do not reward hedging.** A claim is not better because it is vague. Judge what it asserts.
4. **Do not reward confidence.** A confident claim is not worse because it is confident, only if it asserts more than the evidence supports.
5. **The two packets are separate tasks.** Rate `packet_initial.csv` completely, then close it. Do not open `packet_defended.csv` while the first packet is still open, and do not compare items across packets.
6. **Do not discuss ratings with the other annotator** until both of you have submitted. The study measures independent agreement.

## Submitting

Save each file with your annotator code in the name, e.g. `packet_initial_A.csv`, and return both. Do not rename, reorder, or delete rows. Only the four right-hand columns need to change.

## What happens next

Your ratings are merged with a second annotator's. We report:

- exact agreement,
- agreement within one point,
- agreement on the binary "material overstatement" threshold,
- quadratic weighted kappa.

Disagreements are preserved, not averaged away. The study's main analysis compares the gap between the initial and defended ratings against a separate expected-utility criterion. Your two packets are never shown to each other's annotators, and the ratings are collected before any of that analysis is run.

## Privacy and ethics

- Do not include personal information in notes.
- The evidence dossiers are synthetic research materials, not real patient, employee, or financial records.
- You may stop at any time. If you stop partway, return the file as-is; partial ratings are still usable and will be reported as partial.
