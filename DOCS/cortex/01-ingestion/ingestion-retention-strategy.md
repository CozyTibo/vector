# Ingestion Retention & Archival Strategy

## Retention Objectives
- preserve replay-required history horizon,
- preserve provenance reconstructability,
- support tenant governance/deletion workflows.

## Raw Retention
- raw events are retained per policy tier:
  - hot operational horizon,
  - warm replay horizon,
  - archival horizon.
- retention policy must define minimum replay-supported window.

## Replay Retention
- replay job metadata retained longer than operational runs for auditability.
- replay checkpoints retained until replay audit and divergence windows close.

## Large Payload & Transcript Strategy
- large transcript and document payloads may transition to archival storage while keeping:
  - immutable payload reference,
  - integrity hash,
  - provenance and version metadata in Postgres.

## Deletion Assumptions
- tenant deletion workflows remove tenant-scoped rows according to governance policy.
- deletions must preserve allowed audit trails without exposing payload content.

## Archival Constraints
- archival cannot break replay for required retention horizon.
- archived payload access path must remain deterministic and auditable.
