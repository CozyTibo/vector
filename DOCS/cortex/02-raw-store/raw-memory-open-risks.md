# Raw Memory Open Risks

## Purpose
Honest ledger of remaining Phase 02 uncertainties after hardening.

## Open Risks (Known, Accepted, Tracked)
| Risk | Type | Current State |
| ---- | ---- | ------------- |
| Replay economics at extreme historical scope | Scalability | Theoretical model defined; runtime validation pending. |
| Archive rehydration under concurrent replay | Operational | Flow defined; throughput behavior not yet benchmarked. |
| Large-tenant replay concurrency fairness | Multi-tenant operations | Isolation controls defined; contention behavior untested in production. |
| Deep-window query plan stability | Queryability | Mitigation strategy defined; empirical plan tuning pending. |
| Transcript-heavy payload IO pressure | Storage/performance | Temperature model defined; exact thresholds pending live metrics. |

## Risk Classification
- These are **implementation-stage validation risks**.
- They are **not foundational architecture blockers** for Phase 02 start.

## Tracking Rule
Any risk moving from "modeled" to "observed incident pattern" must be promoted into implementation milestones with explicit mitigation ownership.
