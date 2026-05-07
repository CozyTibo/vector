# Ingestion Production Readiness Gates

## Gate Class A: Correctness
- replay determinism and equivalence verification passed.
- invariant check suite passing with no critical violations.
- idempotency verification passed under retry/overlap/replay probes.
- checkpoint recovery verification passed across all sync modes.

## Gate Class B: Survivability
- failure probe matrix scenarios executed with acceptable degradation outcomes.
- chaos scenario protections validated for lane isolation and recovery.
- connector-specific failure scenarios validated for all six connectors.

## Gate Class C: Detection & Operations
- corruption detection signals and escalation paths active.
- observability dashboards include lag, retries, dead-letter, replay progress, divergence metrics.
- operator remediation playbooks complete and review-approved.

## Gate Class D: Isolation & Concurrency
- concurrency verification proves no duplicate durable writes under contention.
- replay/live isolation validated with no pointer mutation leakage.
- queue lease and visibility timeout semantics verified.

## Gate Class E: Governance
- regression risk model reviewed for current architecture slice.
- unresolved critical open questions count is zero.
- architecture and replay review sign-off complete.

## Go/No-Go Rule
Runtime implementation or production rollout for Phase 01 is blocked if any Class A/B gate fails, or if any critical corruption-detection control is missing.
