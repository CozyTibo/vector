# Phase 02 Binary Gate Tolerance Semantics

## Purpose
Specify hard-fail vs soft-fail behavior for closure gates.

## Gate Decision Classes
- `hard_fail`: immediately blocks phase closure.
- `soft_fail`: does not close gate now; may be tolerated operationally with explicit caveat.
- `warn_only`: does not block closure by itself but must be visible.

## Tolerance Doctrine

| Gate | hard_fail conditions | soft_fail conditions | warn_only conditions |
| ---- | -------------------- | ------------------- | -------------------- |
| G1 Reconstruction invariants | unverifiable/corrupted/continuity-broken range in declared required scope | bounded partial windows with explicit markers | non-critical latency-only issues |
| G2 Replay invariants | forbidden divergence, replay isolation breach | acceptable divergence class with complete annotation | expected provider-mutation drift within class |
| G3 Provenance continuity | unresolved lineage break | lineage incomplete in non-required scope | delayed non-critical provenance enrichment |
| G4 Temporal continuity | ordering determinism failure in required scope | bounded precedence ambiguity with fallback trace | stale but deterministic retrieval |
| G5 Corruption coverage | corruption checks absent or failing | partial check coverage with remediation plan | low-severity anomaly under investigation |
| G6 Recovery validation | recovery flow unvalidated for critical class | validation pending for non-critical class | drill overdue but no active incident |
| G7 Query conformance | unsupported semantic query leakage | one supported query class not yet benchmark-stable | degraded performance within documented limits |
| G8 Control-plane operability | required inspection/action surface missing | one non-critical operator flow pending | cosmetic UX issues only |
| G9 Trust-state transitions | transition logic non-deterministic/untested | threshold tuning pending but deterministic logic present | informational transition noise |
| G10 Replay-safe boundary proof | boundary messaging absent/contradictory | one surface missing explicit wording | wording inconsistency with no behavioral mismatch |

## Closure Rule
Phase closure requires:
- zero `hard_fail`,
- zero unresolved `soft_fail` in required scopes,
- `warn_only` items acknowledged with owner and ETA.
