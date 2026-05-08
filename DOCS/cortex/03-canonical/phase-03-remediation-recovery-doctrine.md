# Phase 03 — Remediation & Recovery Doctrine (Operational Runtime)

**Status:** normative companion to `phase-03-failure-degradation-doctrine.md` (taxonomy). This doc covers **what operators/runtime do** after failure classification.

## Principles

- Recovery actions must be **scoped**, **policy-gated**, and **auditable**—no silent global rewinds.
- Remediation never introduces **semantic truth**—only structural fixes (re-run transforms, re-pin bundles, rebuild slices).

## Recovery classes

| Class | Example actions |
| ----- | ---------------- |
| **Scoped rebuild** | Recompute canonical rows for tenant+connector window under pinned bundle |
| **Bundle rollback pin** | Temporary pin to prior active bundle with explicit divergence expectation |
| **Partial remap** | Apply mapping delta pack without touching unaffected scopes |
| **Lineage repair job** | Backfill missing provenance edges when corruption detected—halt if ambiguity unresolved |
| **Ambiguity triage** | Operator acknowledges unresolved mapping backlog (does not resolve semantics—schedules mapping bump) |

## Forbidden remediation

- Manual edits to canonical facts without raw evidence references.
- ML labeling to “clean up” ambiguity.
- Deleting ambiguity records without superseding lifecycle event.

## Coordination with Phase 02 trust

If Phase 02 trust gates demand halt, remediation MUST NOT override—surface blocked state (`phase-03-failure-degradation-doctrine.md`).

## References

- Failure taxonomy: `phase-03-failure-degradation-doctrine.md`
- Verification outputs: `phase-03-verification-engine-doctrine.md`
- Recovery operator surfaces (**§H**): `phase-03-canonical-control-plane-doctrine.md`
