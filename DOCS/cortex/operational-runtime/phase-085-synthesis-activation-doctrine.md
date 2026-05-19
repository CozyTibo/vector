# Phase 08.5 — Synthesis activation maturity

**Status:** normative.  
**Implements:** Steps 24–26 · **G-P085-SYN-01..03**.

---

## Continuous activation (**G-P085-SYN-01**)

When `eligible_scopes > 0` after phase 07:

- Phase 08 MUST run (not skip) if `CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED`
- `materialize_synthesis_for_pipeline_v1` MUST persist **activation audit**
- Minimum jobs per pass: `min(eligible, max_scopes)` unless legality blocks

**Backoff:** if repeated `synthesis_forbidden`, escalate to operator panel — do not infinite retry.

---

## Idle vs starved (**G-P085-SYN-02**)

| Class | Condition | UI color |
| ----- | --------- | -------- |
| **healthy_idle** | `eligible = 0`, no upstream starvation | neutral green |
| **operational_starvation** | upstream has artifacts, `eligible = 0` | amber/red |
| **legality_blocked** | jobs fail `synthesis_forbidden` | red |
| **continuity_incomplete** | pipeline waiting/stalled | amber |
| **replay_unsafe** | replay divergence spike | red |

`explain_synthesis_eligibility_v1` MUST return `classification`.

**Forbidden:** synthesis stage `healthy` when `operational_starvation`.

---

## Throughput maturity (**G-P085-SYN-03**)

| Metric | Target |
| ------ | ------ |
| `synthesis_jobs_completed_per_day` | tenant policy floor |
| `synthesis_scope_coverage_percent` | ≥ 90% |
| `synthesis_activation_audit_empty_rate` | ≤ 5% when eligible > 0 |

**Audit table:** `cortex_synthesis_activation_audits` — scopes_generated, jobs_completed, empty_scope_reason.
