---
name: mgmt-reverse-engineer-paper
description: Deep-read and reverse-engineer a verified management paper as an anchor for a new study. Use when the user provides or identifies a strong paper and wants to understand exactly how its problem, theory, constructs, data, design, evidence sequence, and contribution work; compare it with the user's project; or identify the smallest defensible novelty delta. Also use when an unpositioned project has found a candidate substantive Anchor Paper that must be understood before freezing the research question.
---

# Reverse-Engineer the Anchor Paper

Do not summarize the paper chapter by chapter. Reconstruct its research logic.

## Verify first

Read [references/source-honesty.md](references/source-honesty.md).

Use the actual paper or verified scholarly record. If you cannot access enough of the paper to support a claim, mark it `UNVERIFIED` rather than filling the gap.

## Classify the anchor role

Read [references/anchor-ledger.md](references/anchor-ledger.md).

State whether the paper is:
- SUBSTANTIVE
- THEORY
- METHOD
- STYLE

Only a substantive anchor establishes the closest academic market.

## Reconstruct Paper DNA

Read [references/paper-dna.md](references/paper-dna.md).

Extract:
1. Big problem
2. Baseline belief before the paper
3. Exact unresolved issue
4. Why prior work could not resolve it
5. Theory provenance and mechanism
6. Constructs
7. Data-generating process
8. Operational variables
9. Unit of analysis
10. Design / identification / inferential logic
11. Evidence sequence
12. Belief update after the paper
13. Primary contribution
14. Remaining limitations that matter for our project

## Compare with the user's project

Do not mechanically replace X and Y.

Specify:
- what logic can be retained;
- what must change;
- what cannot be assumed to transfer;
- one primary novelty delta.

## Collision check

Before declaring the delta novel, search the recent frontier around the proposed extension or pass the delta back to `$mgmt-ground-question` for a collision scan.

## Publication decision

Return one:
- KEEP extension
- PIVOT extension
- USE AS THEORY/METHOD ONLY
- REJECT AS ANCHOR

## Shared state

If the paper becomes the substantive anchor, update `PAPER_STATE.md` explicitly. Never silently replace a frozen anchor.

## Project memory integration

For a continuing research project, read [references/project-memory.md](references/project-memory.md).

**Read:** `PAPER_STATE.md`; `LITERATURE_LEDGER.md`.

**Write/update:** `LITERATURE_LEDGER.md (anchor role, verified finding, transfer limits)`; `RUN_LOG`; `PAPER_STATE.md only if the substantive anchor is explicitly adopted`.

**Constraint:** Do not invent missing paper content or promote a method/style paper into a substantive anchor.
