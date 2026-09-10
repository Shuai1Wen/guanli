# Real Project Evaluation Protocol

A Skill version is not stable merely because packaging tests pass.

## For each real project run
Record:
1. project and Skill;
2. frozen PAPER_STATE hash before/after;
3. whether a frozen field changed;
4. whether the change used RESET_REQUEST;
5. whether a known Failure Memory trigger recurred;
6. whether the Skill prevented or repeated it;
7. whether the run produced the requested publication deliverable;
8. any new reusable failure pattern.

## Success criteria for v4.1
- No silent Core RQ / construct / claim drift across projects.
- No fabricated anchor, gap, coefficient, result, or journal rule.
- Method choice follows paper archetype and research relation.
- Null/contradictory core evidence is preserved.
- Narrow writing tasks remain direct and are not over-audited.
- Repeated project failures become promotion candidates, not automatic global edits.

## Promotion
Run:

```bash
python shared/runtime/promote_failures.py projects --output evaluations/failure_candidates.json
```

Global Skill changes require review plus regression testing before release.
