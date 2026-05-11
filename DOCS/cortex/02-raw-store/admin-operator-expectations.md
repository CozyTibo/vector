# Phase 02 Admin / Operator Expectations

## Objective
Phase 02 admin is an operational memory control plane, not a maturity dashboard.

## Required Surfaces
- raw memory browser (tenant/connector/time/revision scoped evidence retrieval),
- provenance explorer (source/run/replay lineage tracing),
- replay inspector (job scope, boundaries, drift/degradation signals),
- temporal reconstruction explorer ("as-of" evidence slices with trust labels),
- corruption and continuity-gap visibility,
- recovery status and proof view.

### Memory Health Overview (runtime truth, not theater)
Must expose:
- replay safety state,
- reconstruction coverage state,
- corruption state,
- lineage continuity state,
- replay drift state,
- degraded memory regions,
- unverifiable evidence regions,
- continuity gaps,
- revision churn indicators.

Required trust-state vocabulary:
- trusted,
- partial,
- degraded,
- replay-safe,
- unverifiable,
- corrupted,
- reconstruction-limited.

No synthetic "all healthy" maturity signaling is acceptable when trust is partial.

## Required Operator Actions
- scoped replay trigger with boundary preview,
- scoped integrity validation,
- scoped recovery workflows,
- safe quarantine/unquarantine for degraded scopes.
- scoped continuity verification,
- scoped reconstruction verification,
- scoped corruption scans,
- scoped provenance validation.

## Required Verification Checklist
Operators must be able to verify:
- replay trust status,
- provenance continuity status,
- revision continuity status,
- reconstruction trust status,
- corruption/recovery status,
- queryability availability status.

Checklist outputs must expose proof quality:
- measured,
- inferred,
- stale,
- partially-validated,
- unverifiable.

## What Operators Must Be Warned About
- unverifiable evidence ranges,
- continuity-broken scopes,
- replay-diverged scopes,
- reconstruction-limited windows,
- lineage-incomplete slices.
- simulated enforcement outcomes (`would_block`) versus active enforcement (`blocked`).

## What Operators Must Never Assume
- that "healthy" implies semantic truth,
- that replay-safe implies replay-complete omniscience,
- that reconstructed means complete historical reality,
- that absent evidence implies absent real-world event.

## UX Doctrine
Prioritize trust-state clarity:
- trustworthy,
- partial,
- degraded,
- unverifiable.

Avoid generic "green health" signals that hide continuity/replay uncertainty.

## Runtime Memory Control Plane Doctrine
Admin in Phase 02 is:
- operational memory truth,
- replay truth,
- provenance/lineage truth,
- corruption truth,
- reconstruction truth.

Admin in Phase 02 is not:
- analytics dashboard,
- AI insights center,
- semantic graph explorer,
- reasoning UI.

## Information Architecture Alignment (Phase 02)
Phase 02 admin expectations map onto:
- Cortex Overview: runtime memory truth summary and trust-state rollups,
- Cortex Ingestion / Memory: replay-aware raw memory explorer + lineage + temporal inspection,
- Cortex Verification: trust-gate checklist and continuity/corruption/replay proofs.

Future graph/reasoning/cognition tabs remain out of Phase 02 scope.

## Anti-Goal Guardrails
Phase 02 admin surfaces must not introduce:
- semantic conclusions,
- graph/causal reasoning workflows,
- organizational intelligence claims,
- AI interpretation of raw evidence.

## Step 11/14 Calibration Requirements
- Enforcement readiness must be visible as policy state, not hidden behavior.
- Operator actions must show trust risk and enforcement impact before execution.
- Trust cards must include verification freshness and proof-quality annotations.
