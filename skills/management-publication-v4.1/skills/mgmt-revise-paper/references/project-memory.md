# Project Memory Protocol

This skill can run statelessly for a narrow one-off task. For a continuing research project, use the project memory files as the working single source of truth.

## Required behavior

1. Read `PAPER_STATE.md` before changing the research architecture.
2. Read only the ledgers relevant to the current task; do not load every project file mechanically.
3. Preserve fields marked frozen. If evidence requires a change, issue `RESET_REQUEST` before modifying the frozen state.
4. Record the run after completing a substantive project task.
5. Record a failure only when it represents a reusable workflow failure, not every disagreement or null result.
6. Project failures may change future behavior inside that project immediately, but they do **not** automatically rewrite global Skill rules.
7. Global rule promotion requires recurrence across independent projects or a severity-P0 failure, followed by regression testing.

## Files

- `PAPER_STATE.md`: frozen research identity and current publication state.
- `CONCEPT_LEDGER.md`: construct definitions, allowed meanings, forbidden overclaims.
- `LITERATURE_LEDGER.md`: verified literature/anchor records and collision checks.
- `EVIDENCE_LEDGER.md`: study claims linked to actual tables, figures, models, files, or verified sources.
- `FAILURE_MEMORY.md` / `FAILURES.jsonl`: reusable failure patterns.
- `runs/`: one execution record per substantive run.

## RESET_REQUEST

Use:

```text
RESET_REQUEST
Field:
Old value:
New evidence:
Proposed value:
Consequences:
```

Do not silently modify a frozen field.
