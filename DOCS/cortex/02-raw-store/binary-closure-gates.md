# Phase 02 Binary Closure Gates

## Rule
Phase 02 is complete only if all gates pass.
Gate status values: PASS / FAIL (no narrative-only closure).

## Gate Set

| Gate ID | Gate | PASS Criteria |
| ------- | ---- | ------------- |
| G1 | Reconstruction invariants | As-of and latest-before retrieval invariants pass for declared test scopes. |
| G2 | Replay invariants | Replay determinism/isolation/equivalence checks pass for declared scopes. |
| G3 | Provenance continuity | Required provenance/lineage continuity checks pass; no unresolved lineage-broken scopes. |
| G4 | Temporal continuity | Revision/supersession/deletion visibility and ordering precedence checks pass. |
| G5 | Corruption coverage | Corruption detection checks are active and passing in validation suite. |
| G6 | Recovery validation | Recovery workflows validated for defined failure classes; post-recovery trust states correct. |
| G7 | Query model conformance | Supported query classes behave deterministically; anti-goal query classes blocked. |
| G8 | Control-plane operability | Runtime Memory Control Plane supports required inspection/actions/checklist. |
| G9 | Trust-state transitions | Trust-state taxonomy transitions are implemented, observable, and test-covered. |
| G10 | Replay-safe boundary proof | Replay-safe/non-omniscient boundary messaging enforced in operator surfaces and APIs. |

## Fail-Closed Rule
If any gate FAILs, Phase 02 remains open.
Partial PASS may be reported operationally but cannot close phase status.

## Tolerance Reference
See `gate-tolerance-semantics.md` for hard-fail / soft-fail / warn-only interpretation per gate.
