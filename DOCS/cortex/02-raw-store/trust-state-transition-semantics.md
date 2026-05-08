# Phase 02 Trust-State Transition Semantics

## Purpose
Define deterministic transition rules between trust states.

## Transition Inputs
- invariant results (raw/provenance/replay/temporal/corruption),
- continuity-gap markers,
- replay divergence classification,
- recovery validation status.

## Severity Levels
- `S0`: informational (no trust downgrade),
- `S1`: warning (partial/degraded),
- `S2`: blocking (unverifiable/replay-diverged/continuity-broken),
- `S3`: critical (corrupted).

## Transition Matrix (normative)

| From | Trigger | To | Severity | Replay Allowed | Reconstruction Allowed | Gate Impact |
| ---- | ------- | -- | -------- | -------------- | ---------------------- | ----------- |
| healthy | minor bounded coverage gap | partial | S1 | yes (scoped) | yes (with caveat) | non-blocking unless persistent |
| healthy/replay-safe | replay equivalence warning class | degraded | S1 | yes (scoped, caution) | yes (annotated) | non-blocking if within tolerance |
| any non-critical | required verification unavailable | unverifiable | S2 | no trusted publish | diagnostic only | blocks closure |
| replay-safe | forbidden divergence class | replay-diverged | S2 | no trusted publish | yes (diagnostic) | blocks closure |
| reconstruction-safe/partial | lineage break or ordering anchor break | continuity-broken | S2 | no trusted replay | partial diagnostic only | blocks closure |
| any | integrity corruption signal confirmed | corrupted | S3 | blocked | blocked except forensic diagnostic | blocks closure |
| degraded/partial | recovery + revalidation pass | reconstruction-safe or replay-safe | S0 | yes | yes | may unblock gates |
| unverifiable | missing verification evidence restored + pass | degraded or healthy | S0 | policy-based | policy-based | may unblock gates |

## Calibration Guidance (pre-runtime defaults)
- single transient warning in narrow scope -> `partial` (S1),
- repeated warning over >= 3 verification cycles -> `degraded` (S1/S2 boundary),
- any forbidden replay divergence -> `replay-diverged` (S2),
- any unresolved continuity break -> `continuity-broken` (S2),
- any confirmed hash/payload corruption -> `corrupted` (S3).

## Operator Implication
No transition to `healthy` is allowed without explicit revalidation evidence.
