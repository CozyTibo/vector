# Ingestion Database Access Patterns

## Write Patterns (Hot Path)
- append-heavy inserts into `raw_event_envelopes`.
- frequent updates/inserts to checkpoints.
- frequent run status updates for active runs.
- queue lease/ack/failure updates.

## Read Patterns (Hot Path)
- latest checkpoint lookup by tenant+connector+scope.
- dedupe existence check by idempotency key.
- queue job fetch by lane+status+priority.
- connector runtime state lookup by tenant+connector.

## Replay Scan Patterns
- scan raw rows by tenant + connector + time window.
- scan replay-tagged rows by replay_job_id for progress and divergence.
- scan checkpoints by replay_job_id + checkpoint_seq desc.

## Tenant-Scoped Query Patterns
- run history by tenant+connector+started_at.
- failure hotspots by tenant+failure_code.
- lag diagnostics by tenant runtime state.

## Index Dependencies
- dedupe index is mandatory for write correctness.
- checkpoint latest index is mandatory for low-latency recovery.
- replay scan indexes are mandatory for bounded replay operations.

## Scaling Assumptions
- dominant write pressure on raw table.
- dominant read pressure on checkpoint and queue tables.
- replay introduces heavy read scans; must avoid starving live write path.
