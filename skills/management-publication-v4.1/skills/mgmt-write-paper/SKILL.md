---
name: mgmt-write-paper
description: Write or comprehensively revise a management research manuscript in mature Chinese academic style after the paper thesis and evidence are sufficiently stable. Use for titles, abstracts, introductions, theory, methods, results, discussion, conclusions, full-paper rewrites, sentence-level natural Chinese, removal of AI-like abstraction or English-translation syntax, and target-journal prose. For a narrow writing request on a frozen study, write directly rather than reopening the entire research design.
---

# Write the Management Paper

Produce manuscript prose. Do not substitute a diagnostic report for the requested writing.

## Read frozen state when relevant

If `PAPER_STATE.md` exists, preserve frozen:
- research object;
- core RQ;
- constructs;
- primary claim;
- belief update.

If no state is needed for a narrow frozen task, do not create one.

## Never fabricate content

Read [references/source-honesty.md](references/source-honesty.md).

Do not invent:
- coefficients;
- effect sizes;
- sample details;
- mechanisms;
- robustness results;
- citations;
- policy/institutional facts.

Use placeholders only when the user explicitly wants a template. Otherwise request/use the actual material.

## Core standard

> **重大问题说得大，具体过程说得清，概念说得准，句子说得自然。**

## Big-problem bridge

Read [references/big-problem-bridge.md](references/big-problem-bridge.md) before writing a new abstract/introduction.

A big opening must connect:
`important problem → mechanism → construct → evidence`.

If not, shrink the opening rather than adding policy slogans.

## Abstract

Default:
`重大现实/理论命题 → research design → one-line findings → belief update / real implication`

Do not open with a taxonomy unless the taxonomy is the contribution.

## Introduction

Use:
1. important problem;
2. established knowledge;
3. precise unresolved issue;
4. why unresolved issue matters;
5. why this study can answer;
6. final paragraph: question, design, main findings, contribution.

Use implicit problem progression; consolidate the paper only in the final paragraph.

Do not repeatedly announce first/second/third research questions.

## Theory

Each paragraph performs one task:
- define;
- distinguish;
- explain mechanism;
- derive expectation;
- state boundary.

Respect Theory Provenance. Do not turn inductive reasoning into an established theory.

## Methods

Explain:
- what the data represent;
- how constructs are measured;
- why the unit is correct;
- why the method matches the question/archetype.

Avoid algorithm-manual prose unless methodology is the contribution.

## Results

Open with analytical purpose, not "Table X reports".

Use:
`what is tested → specification logic → result → substantive meaning → belief update`.

Do not hide null main results.

## Discussion

Use:
`prior belief → present evidence → revised/bounded belief → mechanism/boundary → why it matters`.

Do not repeat the Results section.

## Conclusion

Return to the real management/policy problem.
Do not stop at "provides a new perspective" or "enriches the literature".

## Sentence pass

For every sentence ask:
1. Who is the subject?
2. What is its logical relation to the previous sentence?
3. Is it about the research object or about manuscript navigation?
4. Can abstract nouns become subject + action?

Avoid mechanical "进一步、因此、由此、与此同时".

Read [references/chinese-management-style.md](references/chinese-management-style.md) for section-level patterns.

## Project memory integration

For a continuing research project, read [references/project-memory.md](references/project-memory.md).

**Read:** `PAPER_STATE.md`; `CONCEPT_LEDGER.md`; `LITERATURE_LEDGER.md`; `EVIDENCE_LEDGER.md`.

**Write/update:** `RUN_LOG`; `manuscript text requested by the user; update ledgers only when new verified information is actually introduced`.

**Constraint:** Writing must not silently widen constructs, claims, or causal language beyond the ledgers.
