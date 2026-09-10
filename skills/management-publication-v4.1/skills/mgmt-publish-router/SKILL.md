---
name: mgmt-publish-router
description: Route broad, mixed-stage, or ambiguous management-publication requests to the smallest useful workflow. Use when a user has a combination of idea, data, results, draft, advisor feedback, and journal goals but it is unclear whether the next publication step is positioning, anchor-paper reconstruction, study design, evidence building, writing, targeting, or revision. Do not use for a narrow abstract rewrite, a single-paper deep read, a specific model-design question, or a reviewer-response task when a specialist skill clearly applies.
---

# Management Publication Router

Advance the project toward a publishable paper. Do not turn routing into a general audit.

## Publication doctrine

Use four standards throughout:

> **重大问题说得大，具体过程说得清，概念说得准，句子说得自然。**

"说得大" means connect the study to an important problem that the literature or management reality already recognizes. It never licenses inflated claims.

## Use the teacher-grounded spine

For a full research project, the default order is:

`Research Object → Academic Mountain → Substantive Anchor → Paper Archetype → Paper Thesis → Novelty Delta → Study Design → Evidence → Belief Update → Journal/Submission`

Do not skip from available data directly to a paper story.

## Choose the entry route

### A. Paper-first
Use when a strong substantive paper is already known:
`verified anchor → unresolved point → one main delta → design → evidence`.

### B. Practice-first
Use when the user starts from a real management puzzle:
`reality object → academic name/literature → substantive anchor → one paper`.

### C. Existing-data salvage
Use when extensive data/results already exist:
`neutral Fact Bank → research object → candidate mountains → substantive anchor → paper thesis`.

Existing results are reusable assets, not automatic research questions.

## Use one core question

A management paper normally carries one core problem. Additional analyses are evidence steps, not automatically separate RQs.

## Publication decisions include stopping

At positioning stage, allow one of:
- `KEEP` — current paper thesis is publishable enough to design.
- `PIVOT` — preserve assets but change the thesis/object/delta.
- `SPLIT` — evidence supports more than one distinct paper.
- `EXIT` — current idea is too saturated, mismeasured, or weak to justify more work.

"Help the user publish" does not mean rescuing every topic.

## Source honesty

Read [references/source-honesty.md](references/source-honesty.md) whenever specific literature, novelty, journal rules, or empirical facts must be stated.

## Shared state

For a broad/multi-stage project, read [references/paper-state-protocol.md](references/paper-state-protocol.md). If no state exists, initialize one only after the research object is stated.

Use `scripts/init_paper_state.py <path>` when a persistent project file is useful.

## Route to specialist workflows

- Question / field / viable paper story → `$mgmt-ground-question`
- One strong paper / closest predecessor → `$mgmt-reverse-engineer-paper`
- Theory / constructs / variables / design → `$mgmt-design-study`
- Results / tables / robustness / evidence ordering → `$mgmt-build-evidence`
- Manuscript prose → `$mgmt-write-paper`
- Journal / submission → `$mgmt-target-submit`
- Advisor/editor/reviewer feedback → `$mgmt-revise-paper`

Do not invoke all skills by default.

## Response contract

For broad requests, return only:

**当前发表状态：**  
**本轮唯一核心任务：**  
**本轮直接交付物：**  
**现有资产如何复用：**  
**建议决策：KEEP / PIVOT / SPLIT / EXIT（如已可判断）**

Then perform the next useful task.

## Project memory integration

For a continuing research project, read [references/project-memory.md](references/project-memory.md).

**Read:** `PAPER_STATE.md`; `FAILURE_MEMORY.md`; `runs/ (latest 3 entries when useful)`.

**Write/update:** `RUN_LOG`; `PAPER_STATE.md only after an explicit state decision`; `FAILURE_MEMORY.md when a recurring workflow failure is observed`.

**Constraint:** Do not create or edit manuscript evidence merely to make the project look complete.
