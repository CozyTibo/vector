# Temporal Modeling

## Time Axes
- Event-time: when source event actually occurred.
- Observation-time: when connector saw the event.
- Processing-time: when Cortex transformed the event.
- Inference-time: when inference artifacts were generated.

## Canonical Timestamp Fields
- `occurred_at`: source event chronology anchor.
- `observed_at`: ingestion chronology anchor.
- `processed_at`: deterministic stage processing time.
- `inferred_at`: inference generation time.
- `created_at`: storage creation time for current record version.

## Temporal Objects
- Event timeline: ordered canonical events with provenance.
- State transition record: explicit before/after status evolution.
- Ownership evolution record: assignment and accountability changes.
- Decision evolution record: proposed -> accepted -> superseded chains.
- Concern lifecycle: raised -> discussed -> mitigated/resolved/reopened.

## Historical Reconstruction
Reconstruct historical views by evaluating entities, relations, and statuses at a requested timepoint using effective ranges (`effective_from`, `effective_to`).

## Ordering Semantics
- Primary ordering for organizational chronology uses `occurred_at`.
- Ties or missing event-time fall back to `observed_at`, then `processed_at`.
- Replay must not reinterpret chronology based solely on `created_at`.

## Conflicting Timelines
When sources disagree:
- preserve each event with source provenance,
- mark timeline conflict artifact,
- avoid forced merge until resolution rule applies.

## Revision Handling
Edits do not erase prior states. Revisions produce superseding records with explicit links to superseded records.

## Replay And Temporal Integrity
- Replays may regenerate derived/inferred timestamps (`processed_at`, `inferred_at`, `created_at`) while preserving source chronology (`occurred_at`, `observed_at`).
- Superseding records must maintain temporal lineage links to replaced records.
