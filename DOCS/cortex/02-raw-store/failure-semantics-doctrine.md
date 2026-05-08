# Phase 02 Failure Semantics Doctrine

## Purpose
Define how Phase 02 represents and communicates trust degradation.

## Failure Classes
- corruption (payload/provenance/replay/index/archive),
- partial replay completion,
- provider mutation drift against previously observed payload classes,
- missing-history gaps (never observed or deleted before capture),
- lineage discontinuity,
- unverifiable evidence ranges.

## Required Failure Representation
Every failure must include:
- affected tenant/connector/time scope,
- failure class,
- trust impact state:
  - replay-safe (if still valid),
  - degraded,
  - partially reconstructable,
  - unverifiable,
  - replay-diverged,
  - continuity-broken,
  - lineage-incomplete,
  - corrupted,
- recovery status and last validation timestamp.

## Operator Handling Model
- degraded scopes remain queryable with trust-state markers,
- replay publication is blocked for corrupted/unverifiable scopes when policy requires,
- recovery actions must emit post-recovery proof of continuity status.

## Anti-Silence Rule
Phase 02 must never silently convert unknown/degraded states into "healthy."

## Recoverability Classes
- recoverable: deterministic recovery procedure exists and validated.
- conditionally recoverable: recovery depends on external artifact/availability.
- non-recoverable: preserved evidence unavailable; scope remains permanently reconstruction-limited.
