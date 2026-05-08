# Phase 02 Binary Closure Gates

## Rule
Phase 02 is complete only if all required gates pass.
Gate status values: PASS / FAIL (no narrative-only closure).

## Baseline Gate Set (Step 10 runtime)

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

## Stabilization Gate Set (Steps 11-16)

| Gate ID | Gate | PASS Criteria |
| ------- | ---- | ------------- |
| G11 | Progressive enforcement readiness | Trust-state-aware enforcement policy is runtime-active with `would_block`/`blocked` semantics and catastrophic-only hard blocking. |
| G12 | Unified verification truth | Closure/trust/control-plane/aggregate verification derive from one canonical computation path with deterministic precedence. |
| G13 | Replay proof depth | D0-D5 matrix and forbidden-divergence denial paths are runtime-tested and reproducible. |
| G14 | Trust-signal proof quality | Operator trust surfaces distinguish measured/inferred/stale/unverifiable/partial states. |
| G15 | Critical integrity strength | Reconstruction-critical continuity pointers and revision/lineage integrity checks are verifiable and trust-impacting. |
| G16 | Operational trust proof pass | Adversarial runtime trust proof suite passes (replay/corruption/reconstruction/temporal/stale/denial/recovery). |

## Calibrated Enforcement Rule
Phase 02 uses progressive enforcement while stabilizing:
- catastrophic trust failures may hard-block operations,
- degraded/unverifiable states remain operational with explicit warning/risk semantics,
- `would_block` decisions must be surfaced before universal fail-closed rollout.

If any required gate FAILs, Phase 02 remains open.
Partial PASS may be reported operationally but cannot close phase status.

## Tolerance Reference
See `gate-tolerance-semantics.md` for hard-fail / soft-fail / warn-only interpretation per gate.
