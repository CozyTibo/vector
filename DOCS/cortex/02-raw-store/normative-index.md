# Phase 02 Normative Index (Authoritative Map)

## Purpose
Single constitutional index for Phase 02 doctrine ownership and precedence.

## Precedence Rules
1. `normative-index.md` (this file) defines ownership and conflict resolution.
2. Concept-specific doctrine files listed below are normative for their concept.
3. `MASTER_TRACKER.md` is normative for phase step structure and closure sequencing.
4. If docs conflict, concept-specific doctrine wins over generic overview text.

## Authoritative Ownership Map

| Concept | Authoritative File |
| ------- | ------------------ |
| Trust boundary (guarantees vs non-guarantees) | `trust-boundaries.md` |
| Trust states and transitions | `trust-state-taxonomy.md`, `trust-state-transition-semantics.md` |
| Replay equivalence/divergence | `replay-equivalence-doctrine.md`, `replay-divergence-severity-model.md` |
| Reconstruction semantics | `reconstruction-semantics-doctrine.md` |
| Temporal continuity ordering | `temporal-continuity-doctrine.md` |
| Failure/degradation semantics | `failure-semantics-doctrine.md` |
| Continuity-gap representation | `continuity-gap-representation-doctrine.md` |
| Trust-state API annotation doctrine | `trust-state-api-contract-doctrine.md` |
| Query model + anti-goals | `raw-memory-query-model.md`, `raw-storage-boundaries.md` |
| Storage/retention doctrine | `storage-retention-doctrine.md`, `raw-memory-retention.md` |
| Binary closure gates and tolerances | `binary-closure-gates.md`, `gate-tolerance-semantics.md` |
| Unified verification semantics | `verification-semantics-doctrine.md`, `trust-state-api-contract-doctrine.md` |
| Progressive enforcement readiness semantics | `trust-state-taxonomy.md`, `admin-operator-expectations.md`, `binary-closure-gates.md` |
| Operator decision model | `admin-operator-expectations.md`, `operator-decision-guidance-doctrine.md` |
| Ambiguity governance | `ambiguity-audit.md`, `runtime-vs-doctrine-ambiguity-register.md` |
| Phase sequencing / closure step ownership | `../MASTER_TRACKER.md`, `../implementation/phased-roadmap.md` |

## Implementation Ownership
- Runtime contract implementation follows doctrine files above.
- Any proposed deviation requires explicit doc update in the owning file and tracker note.

## Closure Ownership
Phase 02 closure authority is `binary-closure-gates.md` + `MASTER_TRACKER.md` Phase 02 Steps 10-16.
