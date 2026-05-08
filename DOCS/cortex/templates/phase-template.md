# Phase Document Template

## Required Files
- overview.md
- goals.md
- architecture.md
- data-flow.md
- implementation-plan.md
- technical-decisions.md
- risks.md
- open-questions.md
- future-evolution.md

## Authoring Standard
Each file should include explicit constraints, lineage expectations, dependency references, and testability assumptions.

## Phase completion (implementation-plan.md)
Each phase’s `implementation-plan.md` **must** document, under exit criteria or a dedicated subsection, how the phase’s **terminal tracker step** delivers the **admin & operator closure** gate defined in `DOCS/cortex/MASTER_TRACKER.md` (**Terminal step — admin & operator closure**): what operators will **see**, what they can **trigger**, and how they **verify** the phase is healthy. **Phase 01:** substrate closure = Step **6**; **phase closure** = Step **14** (organizational exhaust). Phases **02–10:** terminal step = Step **6**.
