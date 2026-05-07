# Replay Architecture

## Replay Triggers
- schema evolution affecting downstream interpretation,
- processor logic updates,
- connector bug corrections,
- inference model version changes,
- data quality remediation.

## Replay Scope Modes
- Full replay: raw -> synthesis.
- Layer replay: canonical onward, memory onward, or reasoning onward.
- Targeted replay: tenant/time-window/entity-specific replay.

## Deterministic Replay Expectations
For deterministic stages, identical inputs and versions must yield identical outputs. Divergence must be explainable by explicit version changes.

## Versioned Replay
Replay jobs must persist:
- replay_job_id,
- replay_version,
- input_scope,
- source snapshot references,
- schema/extraction/processor/inference versions,
- output comparison summary.

## Safety Guarantees
- Replay isolation from live writes.
- No in-place mutation of historical records.
- Superseding version strategy for changed outputs.
- Rollback path for failed replay publication.

## Replay Observability
Track throughput, lag, divergence rates, failure classes, and confidence distribution shifts after replay.

## Replay Integrity Rules
- Deterministic stages must remain output-stable for identical inputs and versions.
- Inference stages may evolve with `inference_version`, but must remain provenance-linked and comparable.
- Replay must never break provenance chain continuity.
