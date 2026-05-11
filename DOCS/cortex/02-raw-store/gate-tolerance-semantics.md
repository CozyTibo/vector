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
| G11 Progressive enforcement readiness | catastrophic conditions not blockable; policy engine missing runtime state awareness | `would_block` semantics incomplete on non-critical flows | warning copy/UX mismatches only |
| G12 Unified verification truth | contradictory pass/fail outcomes across surfaces for same snapshot | duplicate gate implementations with equivalent output but drift risk | non-impacting label mismatch |
| G13 Replay proof depth | forbidden divergence denial path untested or non-deterministic | partial D0-D5 matrix coverage | low-impact replay diagnostics gaps |
| G14 Trust-signal quality | stale/measured/inferred semantics absent causing false-green confidence | freshness SLA not yet calibrated | cosmetic signal wording issues |
| G15 Critical integrity hardening | reconstruction-critical continuity pointer validation absent where required | selective integrity constraints pending rollout plan | non-critical integrity warning backlog |
| G16 Operational trust proof pass | adversarial trust proof suite fails in required scenarios | one required proof scenario pending rerun | non-critical scenario backlog with clear owner |

## Closure Rule
Phase closure requires:
- zero `hard_fail`,
- zero unresolved `soft_fail` in required scopes,
- `warn_only` items acknowledged with owner and ETA.
