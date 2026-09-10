---
name: mgmt-build-evidence
description: Build and discipline the empirical evidence chain of a management paper. Use when the user has or plans regressions, text-analysis outputs, tables, figures, subgroup results, robustness checks, mechanisms, or exploratory findings and needs to decide what is core, what must be rerun, how to avoid post-hoc story changes or selective reporting, and how each result updates the literature.
---

# Build Publishable Evidence

Read `PAPER_STATE.md` first when present. Evidence serves the frozen paper thesis; it does not silently create a new one.

## Step 1 — Maintain an Analysis Ledger

Read [references/analysis-ledger.md](references/analysis-ledger.md).

Label each analysis:
- `PRE-SPECIFIED`
- `THEORY-PLANNED`
- `POST-HOC EXPLORATORY`

Also label its role:
- CORE
- PROCESS/MECHANISM
- BOUNDARY
- VALIDATION
- APPENDIX
- SEPARATE PAPER
- DROP

## Step 2 — Anti-HARKing and selective-reporting rules

Read [references/anti-harking.md](references/anti-harking.md).

Hard rules:
- Do not hide a full-sample null because a subgroup is significant.
- "Significant in A, non-significant in B" is not itself evidence that A differs from B; test the difference/interactions where applicable.
- Alternative outcome definitions are measurement robustness, not a license to choose the one that tells the best story.
- Post-hoc analyses may motivate a boundary or new paper, but must be labeled and cannot silently replace the original core result.
- If results force a new RQ/theory/contribution, issue `RESET_REQUEST`.

## Step 3 — Use the shortest evidence ladder

Keep only what the thesis needs:
1. measurement/sample credibility;
2. fact establishing the puzzle;
3. main test;
4. mechanism/process;
5. boundary/heterogeneity;
6. alternative explanation;
7. targeted robustness;
8. substantive implication.

## Step 4 — Link every main result to prior knowledge

For each core result write:

`BELIEF_BEFORE → EVIDENCE → BELIEF_AFTER`

Classify the update:
- confirmation with stronger evidence;
- contradiction;
- boundary condition;
- distinction of previously conflated processes;
- process/dynamic pattern;
- measurement/identification improvement.

If the result produces no meaningful update, treat it as support, not contribution.

## Step 5 — Evidence provenance

Read [references/evidence-provenance.md](references/evidence-provenance.md).

Every major manuscript claim should point to:
- a table/figure/model/result produced by this study, or
- a verified scholarly source, or
- an explicit inference labeled as such.

Do not fill missing coefficients, effect sizes, sample sizes, or mechanisms.

## Step 6 — Explain tables before coefficients

Write:
`what is tested → why specifications change → result → magnitude/uncertainty → substantive meaning → what it establishes`

For qualitative/process evidence:
`phase/event → evidence from sources → process inference → rival explanation/negative evidence → mechanism`.

## Step 7 — Stop

When the frozen belief update is adequately supported and major threats are addressed, stop adding analyses.

## Deliverable

Return:
- Analysis Ledger
- Main evidence chain
- Main-text exhibits
- Appendix/separate-paper/drop list
- Missing decisive analysis
- Results-section outline
- Belief-update map
- RESET_REQUEST if required

## Project memory integration

For a continuing research project, read [references/project-memory.md](references/project-memory.md).

**Read:** `PAPER_STATE.md`; `CONCEPT_LEDGER.md`; `EVIDENCE_LEDGER.md`; `FAILURE_MEMORY.md`.

**Write/update:** `EVIDENCE_LEDGER.md`; `RUN_LOG`; `FAILURE_MEMORY.md for selective reporting / HARKing / claim inflation`; `RESET_REQUEST when evidence invalidates the frozen thesis`.

**Constraint:** Null or contradictory core results remain part of the evidence history.
