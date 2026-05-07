# Ingestion Regression Risk Model

## High-Risk Change Categories
- replay semantic changes (scope, isolation, version pinning),
- idempotency key derivation changes,
- cursor semantic changes,
- timestamp interpretation changes,
- transaction sequencing changes,
- checkpoint mutation rule changes,
- introducing AI into ingestion stage logic.

## Why These Changes Are Dangerous
- can silently break determinism and replay trust,
- can create duplicates or false dedupe,
- can corrupt chronology or checkpoint continuity,
- can invalidate downstream provenance assumptions.

## Regression Detection Expectations
- mandatory replay consistency verification rerun,
- invariant check deltas before/after change,
- targeted failure probe subset per changed component,
- blast-radius classification by connector/tenant/scope.

## Required Reviews
- schema review for contract-field changes,
- replay review for version/scope/ordering changes,
- temporal review for timestamp semantics changes,
- architecture review for boundary shifts,
- ADR for deterministic-boundary weakening proposals.
