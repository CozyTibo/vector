# Ingestion Operational Readiness

## Operational Readiness Definition
Ingestion is operationally ready only when reliability verification demonstrates invariant preservation under normal, degraded, and replay conditions.

## Readiness Criteria
- replay verification complete and trusted.
- invariant checks continuously passing.
- idempotency probes passed under retries and overlap.
- checkpoint recovery probes passed across all sync modes.
- concurrency probes show no duplicate durable writes or checkpoint regression.
- corruption detection signals wired and actionable.
- observability dashboards and alerts cover all critical failure classes.
- operator remediation playbooks documented.

## Non-Readiness Conditions
- inability to classify replay divergence.
- missing provenance continuity signals.
- unresolved dead-letter growth behavior.
- unverified replay/live isolation behavior.

## Readiness Evidence Package
- verification report bundle:
  - invariant pass report,
  - failure probe matrix results,
  - replay trust report,
  - readiness gate checklist with approvals.
