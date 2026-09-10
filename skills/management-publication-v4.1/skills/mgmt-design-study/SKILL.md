---
name: mgmt-design-study
description: Convert a positioned management-paper thesis into a publishable study design. Use when the user needs theory, mechanism, hypotheses/propositions, construct definitions, data and unit choices, variables, text measurement, causal or descriptive identification, QCA/NCA logic, longitudinal process/case design, or a frozen empirical research contract. Do not use merely to add a fashionable method to an ungrounded topic.
---

# Design the Study

Read `PAPER_STATE.md` first when present. Do not redesign a frozen paper silently.

## Step 1 — Identify the paper archetype

Read [references/paper-archetypes.md](references/paper-archetypes.md).

Select the dominant archetype before choosing the method:
- theory-testing quantitative;
- causal-identification;
- phenomenon-driven;
- text-measurement/substantive;
- configurational;
- longitudinal process/case;
- stylized-fact/dynamic;
- formal/decision/optimization.

Hybrid papers are allowed, but one archetype should dominate the evidence logic.

## Step 2 — Establish theory provenance

Read [references/theory-provenance.md](references/theory-provenance.md).

Every central mechanism must be labeled:
- `ESTABLISHED`
- `EXTENSION`
- `INDUCTIVE`

Bind established/extended mechanisms to verified scholarly sources. Do not present model-generated reasoning as an established theory.

## Step 3 — Write theory in actor-action form

Use:
`Actor → condition/incentive/information → action → intermediate process → outcome → boundary`

For process/case research, use:
`Actors → events/turning points → sequence → mechanism → outcome/path`.

For descriptive/stylized-fact papers, theory can specify competing expectations rather than directional hypotheses.

Do not force hypotheses onto every archetype.

## Step 4 — Define constructs and data meaning

For each construct:
`construct → definition → observable implication → variable/proxy → data → assumption`.

Read [references/text-as-data.md](references/text-as-data.md) for document/LLM/embedding studies.

Clarify the data-generating process:
- who produces the record;
- why it enters;
- what is omitted;
- whether selection changes across time/units.

## Step 5 — Choose method from the relation and archetype

Examples:
- average association → regression/SEM as appropriate;
- causal effect → credible identification/counterfactual;
- necessary + sufficient configuration → NCA/fsQCA only if theory truly asks these relations;
- transition/adoption → event history/survival;
- process mechanism → longitudinal case/process tracing/temporal bracketing;
- text construct → validated text measurement plus substantive analysis;
- stylized fact → transparent descriptive design with theory-facing contrasts.

Complexity is not depth.

## Step 6 — Freeze the empirical contract

Read [references/research-contract.md](references/research-contract.md).

Specify:
- primary evidence;
- process/mechanism evidence if needed;
- boundary/heterogeneity if theoretically important;
- robustness against actual threats;
- evidence that would falsify or force a reset.

## Step 7 — Prevent post-hoc redesign

State before execution:
- what result supports the paper thesis;
- what null/opposite result would mean;
- which exploratory analyses may be run but cannot silently redefine the thesis.

## Shared state

Update `PAPER_STATE.md` only after explicit agreement. If a frozen RQ/construct/delta must change, issue `RESET_REQUEST`.

## Deliverable

Produce a concise Research Contract that can be executed, not a generic methods menu.

## Project memory integration

For a continuing research project, read [references/project-memory.md](references/project-memory.md).

**Read:** `PAPER_STATE.md`; `CONCEPT_LEDGER.md`; `LITERATURE_LEDGER.md`; `FAILURE_MEMORY.md`.

**Write/update:** `CONCEPT_LEDGER.md`; `PAPER_STATE.md design fields after freeze`; `RUN_LOG`; `FAILURE_MEMORY.md for method-first or construct-data mismatch`.

**Constraint:** Do not change a frozen Core RQ just because a preferred method fits a different question.
