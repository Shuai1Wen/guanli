# v3 vs v4 RC1 — Same-8-Case Regression Test

## Important validity note

This is a **frozen-oracle regression replay**, not an independent double-blind LLM evaluation.

The exact eight cases and oracle were created and exposed in the earlier v3 evaluation in this same conversation. Therefore it would be false to claim that the evaluator is blind to the oracle now.

To preserve comparability:
- the eight case prompts are copied byte-for-byte from the v3 test;
- the v3 scores are frozen from the prior run;
- the oracle is unchanged;
- v4 is scored on the same six 0–2 dimensions;
- a separate `skill-control` score asks whether the required behavior is explicitly encoded in the skill, rather than rescued by base-model knowledge.

A genuinely model-independent blind test still requires a fresh evaluator/model that has not seen the oracle.

## Aggregate results

| Metric | v3 | v4 RC1 | Change |
|---|---:|---:|---:|
| First-pass/replay match (/12) | 11.56 | 11.91 | +0.34 |
| Skill-control coverage (/12) | 9.19 | 11.72 | +2.53 |
| Skill-control coverage (%) | 76.6% | 97.7% | +21.1 pp |

Interpretation: raw answer quality had little headroom because v3 was already being rescued by the base model. The meaningful improvement is that v4 explicitly encodes the controls that were previously implicit.

## Per-case control coverage

| Case | v3 | v4 | Key v4 fix |
|---|---:|---:|---|
| C02 method-first QCA/NCA | 10.0 | 11.75 | object-first + substantive anchor + archetype |
| C05 longitudinal algorithm power | 8.0 | 11.75 | longitudinal process/case is first-class archetype |
| C10 mature psychological-safety chain | 8.5 | 11.50 | saturation review + PIVOT/EXIT |
| C08 standardization/local innovation | 9.5 | 11.75 | Research Object Card distinguishes variance from level |
| C06 frozen paper, writing only | 10.5 | 12.00 | narrower router trigger + direct writing |
| C03 anchor extension | 11.0 | 11.50 | anchor roles + mandatory collision scan |
| C09 saturated female executive–ESG | 9.0 | 11.50 | explicit EXIT/PIVOT |
| C04 null main / positive subgroup | 7.0 | 12.00 | Anti-HARKing + Analysis Ledger + RESET_REQUEST |

## Release decision

**RC status: CONDITIONAL PASS**

Reason:
- all 13 v3 failure modes have an explicit v4 implementation;
- same-case regression shows no loss on narrow writing and major improvement on C04/C05/C09;
- however this is not a model-independent blind evaluation.

Do not label v4 "final" until a fresh evaluator/model, unseen cases, or real project usage confirms the controls.
