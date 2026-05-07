# Replay Integrity Audit

## Scope
This audit validates replay assumptions across ingestion, raw store, canonical, entity resolution, graph, memory, reasoning, retrieval, and synthesis documentation.

## Replayable Surfaces
- Raw events: replay source-of-truth baseline.
- Deterministic transforms: replayable with version-pinned processors.
- Inference artifacts: replayable with `inference_version` and preserved provenance.
- Synthesis artifacts: regenerable from replayed context packs; non-authoritative.

## Immutability Assertions
- Raw payload records remain immutable.
- Canonical identity ids remain stable across replay unless explicit supersession contract applies.
- Provenance chain continuity remains mandatory.

## Version Pinning Assertions
- Deterministic stages pin `schema_version`, `extraction_version`, `processor_version`.
- Inference stages pin `inference_version`.
- Replay jobs pin `replay_version` and `replay_job_id`.

## Isolation Assertions
- Replay execution must be isolated from live writes.
- Replay publication must use superseding records, not in-place mutation.
- Divergence must be measurable and auditable before publication.

## Conflict Handling Assertions
- Replay conflicts are represented explicitly (open/resolved/superseded), never silently dropped.
- Low-confidence replayed inference remains uncertain; replay does not force confidence escalation.

## Integrity Verdict (Current Pass)
- No documentation-level contradictions remain in replay naming (`replay_version`, `replay_job_id`).
- Replay determinism semantics are consistent for deterministic stages.
- Inference replay evolution is consistently versioned and provenance-linked.
