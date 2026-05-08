# Phase 02 Continuity-Gap Representation Doctrine

## Purpose
Define canonical representation of continuity gaps.

## Gap Types
- `missing_evidence_window` (never observed / not captured),
- `corrupted_evidence_window` (integrity failure),
- `lineage_break_window` (provenance/revision break),
- `replay_divergence_window` (equivalence failure),
- `reconstruction_limited_window` (known insufficiency for required reconstruction class).

## Required Gap Fields
- `gap_id`,
- `type`,
- `scope` (tenant/connector/object class),
- `window.from` / `window.to`,
- `source` (`ingestion`, `replay`, `integrity_scan`, `operator_validation`),
- `trust_state_impact`,
- `recoverability_class`.

## Boundary Semantics
- windows are half-open intervals `[from, to)` unless explicitly marked closed,
- overlapping gaps must be represented as separate records plus optional aggregate summary,
- replay-created gaps must reference replay job lineage.

## Distinction Rules
- unobserved history != corrupted evidence,
- corrupted evidence != replay divergence,
- replay divergence != reconstruction limitation,
- lineage break must never be silently coalesced into generic "partial".
