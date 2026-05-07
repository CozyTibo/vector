# Archival Operational Model

## Operational Definition
Archival means moving raw payload-heavy historical data to lower-cost storage while preserving deterministic replayability and evidence completeness.

## Archive Modes
| Mode | Behavior | Operational Expectation |
| ---- | -------- | ----------------------- |
| Replayable archive | Data remains replay-eligible | Slower than hot tier but policy-bounded. |
| Inspection archive | Data remains auditable by operators | Metadata-first lookup, payload hydration on demand. |

## Archive Lifecycle
1. Classify records by retention and activity profile.
2. Move eligible payload bodies to cold tier.
3. Keep metadata/index anchors in primary query path.
4. Validate integrity and pointer health post-move.
5. Support deterministic rehydration for replay/forensics.

## Replay-From-Archive Behavior
- replay planner resolves hot vs cold segments,
- cold segments trigger staged rehydration,
- replay stream preserves deterministic ordering after hydration,
- replay job exposes hydration lag as first-class metric.

## Operational Risks
- rehydration burst can saturate IO/transfer budgets,
- archive pointer drift can cause integrity incidents,
- operator workflows can degrade if archive lookups are opaque.

## Operational Controls
- archive rehydration concurrency caps,
- archive integrity check jobs,
- metadata-only preview before payload fetch,
- explicit archive SLOs for replay and forensic use.
