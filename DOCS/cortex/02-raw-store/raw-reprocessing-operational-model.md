# Raw Reprocessing Operational Model

## Purpose
Define how large-scale raw-driven reprocessing runs in practice, not only in architectural intent.

## Reprocessing Triggers
- extraction logic upgrades,
- ontology/canonical mapping changes,
- bugfix re-derivation requirements,
- replay consistency corrections.

## Reprocessing Modes
| Mode | Scope | Use |
| ---- | ----- | --- |
| Tenant-scoped | Single tenant, bounded window | Default corrective flow. |
| Phase-scoped | Subset of downstream phases | Minimize blast radius. |
| Broad historical | Large historical range | Exceptional, budget-gated. |

## Operational Realities
- reprocessing competes with ingestion and replay for resources,
- queue pressure rises with wide-scope historical jobs,
- canonical downstream fanout can multiply total work cost,
- operator visibility is mandatory to prevent black-box backlog growth.

## Blast Radius Controls
1. Scope-first planning and dry-run estimates.
2. Priority lanes for urgent trust-restoration jobs.
3. Job budget ceilings (time, rows, hydration volume).
4. Progressive rollout (slice windows before full range).
5. Pause/resume controls with deterministic checkpoints.

## Required Operator Visibility
- queued/running/completed by scope,
- estimated vs actual scan and hydration volume,
- downstream phase lag impact,
- failure and retry reason classes.
