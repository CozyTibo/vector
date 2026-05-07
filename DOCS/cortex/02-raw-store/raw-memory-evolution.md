# Raw Memory Evolution

## Evolution Drivers
- source API schema drift,
- connector payload shape changes,
- ingestion envelope schema upgrades,
- replay model enhancements,
- archival tier changes.

## Safe Evolution Rules
- raw row immutability remains absolute.
- evolution is additive by versioned metadata and indexes.
- old payload formats remain readable for replay windows.
- schema evolution includes backward read strategy.

## Payload Evolution Handling
- new source fields are stored without semantic interpretation.
- removed source fields remain present in historical records.
- source revisions become lineage markers, not rewrite triggers.

## Storage Migration Assumptions
- migrations must preserve:
  - `raw_event_id`,
  - source identity fields,
  - provenance bootstrap fields,
  - replay metadata continuity.
