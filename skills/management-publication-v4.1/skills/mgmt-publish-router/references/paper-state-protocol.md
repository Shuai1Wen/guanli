# Shared paper-state protocol

For a broad or multi-stage project, use a project-level `PAPER_STATE.md` as the single source of truth.

Read it before changing the research architecture. Preserve all fields marked `FROZEN`.

A downstream skill may refine prose around a frozen decision, but must not silently change:
- research object;
- primary literature;
- substantive anchor;
- paper archetype;
- core research question;
- primary novelty delta;
- core constructs;
- belief-before / belief-after;
- primary evidence.

If new evidence requires a change, issue a short `RESET_REQUEST` containing:
1. field to change;
2. evidence forcing the change;
3. old value;
4. proposed value;
5. consequences for analyses/manuscript.

For a narrow task on a frozen paper, do not force creation or reopening of `PAPER_STATE.md`.
