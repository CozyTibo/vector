# Temporal Dependency Matrix

## Purpose
This matrix maps temporal fields and temporal rules to the systems that depend on them.

## `occurred_at`
- Meaning: source event-time anchor.
- Used by:
  - canonical chronology,
  - graph event ordering,
  - historical reconstruction,
  - causal reasoning.
- Replay dependency:
  - must remain stable across replay.
- Failure if inconsistent:
  - timeline distortion and false causal ordering.

## `observed_at`
- Meaning: connector observation-time.
- Used by:
  - ingestion ordering diagnostics,
  - late-arrival detection,
  - replay window planning.
- Replay dependency:
  - preserved as ingestion chronology anchor.
- Failure if inconsistent:
  - desync diagnosis becomes unreliable.

## `processed_at`
- Meaning: deterministic stage processing timestamp.
- Used by:
  - operational tracing,
  - replay divergence analysis.
- Replay dependency:
  - may differ by replay run; must remain version-attributable.
- Failure if inconsistent:
  - auditability gaps in transformation lifecycle.

## `inferred_at`
- Meaning: inference artifact generation time.
- Used by:
  - inference comparison across model versions,
  - synthesis uncertainty framing.
- Replay dependency:
  - expected to change under inference replay.
- Failure if inconsistent:
  - inability to compare inference evolution.

## `effective_from` / `effective_to`
- Meaning: validity windows for entity/relation/state assertions.
- Used by:
  - ownership evolution,
  - decision supersession,
  - historical snapshots.
- Replay dependency:
  - superseding records must preserve valid temporal sequence.
- Failure if inconsistent:
  - broken point-in-time reconstruction.

## Replay Ordering Rule
- Ordering precedence: `occurred_at` -> `observed_at` -> `processed_at`.
- Dependency surface:
  - graph evolution,
  - memory derivation,
  - reasoning chronology,
  - synthesis timeline output.
- Failure if violated:
  - replay can fabricate chronological regressions.

## Superseded State
- Meaning: explicit replacement of prior assertion without deletion.
- Used by:
  - canonical correction lifecycle,
  - relation and decision evolution,
  - replay publication.
- Dependency surface:
  - historical reconstruction and governance audit.
- Failure if violated:
  - silent history rewrite and lineage corruption.
