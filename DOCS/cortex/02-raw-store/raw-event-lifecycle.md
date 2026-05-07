# Raw Event Lifecycle

## Lifecycle Stages
1. Ingestion acceptance:
   - receive validated envelope from Phase 01.
2. Persistence:
   - append immutable raw event row.
3. Index registration:
   - write replay, chronology, tenant, connector lookup entries.
4. Replay registration:
   - attach replay context metadata if replay run.
5. Active retrieval phase:
   - available for replay and reprocessing scans.
6. Archival transition:
   - payload may move to cold tier; index + integrity metadata stays queryable.
7. Reprocessing usage:
   - read for extraction/canonical/linking re-runs.
8. Retention evaluation:
   - checked against policy windows and governance constraints.
9. Deletion handling:
   - tenant/policy deletions apply controlled removal while preserving allowed audit metadata.
10. Replay rehydration:
   - archived payload rehydrated for replay when required.

## Never Changes
- source payload content for a given `raw_event_id`,
- source identity and source chronology anchors,
- immutable version markers attached at write time.

## Replay-Sensitive Fields
- replay context tags,
- retrieval location metadata (hot/cold),
- lineage indexes used for replay completeness checks.
