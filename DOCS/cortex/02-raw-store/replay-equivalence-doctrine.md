# Phase 02 Replay Equivalence Doctrine

## Replay Equivalence Meaning
Replay equivalence means:
for a declared scope and boundary, replay reads the same preserved evidence set under deterministic ordering/filters.

Replay equivalence is evaluated against preserved evidence, not mutable upstream provider state.

## Acceptable Divergence Classes
- Explicitly declared schema-version projection differences with preserved source equivalence.
- Declared extractor-rule changes where replay lineage/versioning marks non-equivalence as expected.
- Policy-driven scope changes explicitly approved before execution.

## Forbidden Divergence Classes
- Cross-scope leakage (tenant/connector/boundary violation).
- Missing preserved evidence without declared gap/corruption marker.
- Non-deterministic ordering for same fixed scope/snapshot boundary.
- Silent mutation of historical raw evidence.

## Replay-Safe vs Replay-Complete
- replay-safe: deterministic, isolated reinterpretation over preserved evidence.
- replay-complete: total omniscient provider history recreation (not a Phase 02 guarantee).

## Determinism Boundaries
Replay determinism requires:
- fixed scope definition,
- fixed ordering precedence,
- fixed snapshot boundary semantics,
- fixed lineage/version context.

## Operational Drift Handling
When drift is detected (provider mutation, API drift, pagination drift, schema/extractor change):
- classify drift class,
- mark affected scope trust-state,
- block trusted replay publication where policy requires,
- retain diagnostics for operator inspection.

## Step 13 Replay Proof Obligations
Replay equivalence is not considered operationally trustworthy until:
- D0-D5 classification matrix is runtime-tested,
- forbidden divergence classes have explicit denial-path validation,
- classifier output is reproducible for fixed snapshots,
- replay trust-state degradation and recovery transitions are test-proven.
