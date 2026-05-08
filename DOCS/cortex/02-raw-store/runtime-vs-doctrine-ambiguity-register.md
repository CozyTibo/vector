# Phase 02 Runtime-vs-Doctrine Ambiguity Register

## Purpose
Track where wording could overclaim trust beyond what runtime can prove.

## Current Ambiguities To Resolve Before Implementation

| Area | Ambiguity Risk | Required Clarification |
| ---- | -------------- | ---------------------- |
| Replay language | "Replayable" interpreted as omniscient recreation | Explicit replay-safe vs replay-complete distinction in all Phase 02 surfaces | resolved by `replay-equivalence-doctrine.md` |
| Reconstruction language | "Historical reconstruction" interpreted as perfect truth | Define reconstruction as preserved observed evidence only | resolved by `reconstruction-semantics-doctrine.md` |
| Query model | Raw queryability drifting into semantic querying | Lock anti-goal: no semantic/graph/intelligence queries in Phase 02 | resolved by `raw-memory-query-model.md` + `raw-storage-boundaries.md` |
| Health visibility | Generic health badges hiding trust damage | Require trust-state labels (partial/degraded/unverifiable) | resolved by `trust-state-taxonomy.md` + `raw-memory-observability.md` |
| Admin closure | Control-plane treated as optional UI polish | Make Runtime Memory Control Plane a dedicated implementation step before closure | resolved in tracker Step 6/7 |
| Provenance claims | Provenance continuity misread as semantic truth | Clarify provenance = chain-of-observation, not meaning correctness | resolved by `provenance-preservation.md` |
| Recovery claims | Recovery interpreted as full truth restoration | Clarify recovery restores preserved continuity, not unobserved history | resolved by `failure-semantics-doctrine.md` + `raw-memory-recovery.md` |
| Transition thresholds | state transitions interpreted inconsistently | define deterministic transition semantics and severity levels | resolved by `trust-state-transition-semantics.md` |
| Gate tolerances | hard/soft/warn interpretation inconsistent | define per-gate tolerance semantics | resolved by `gate-tolerance-semantics.md` |
| API trust annotation | runtime responses missing deterministic trust markers | define canonical machine-readable contract | resolved by `trust-state-api-contract-doctrine.md` |
| Continuity-gap shape | gaps represented inconsistently across surfaces | define canonical gap representation doctrine | resolved by `continuity-gap-representation-doctrine.md` |

## Residual Open Items
- production threshold numeric calibration values,
- final API enum/name freeze during implementation kickoff.
