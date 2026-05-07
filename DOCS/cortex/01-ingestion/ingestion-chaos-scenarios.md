# Ingestion Chaos Scenarios

## Provider-Wide API Instability
- expected degradation: connector lanes enter throttled/retrying states.
- protections: adaptive backoff, retry budget, lane isolation.
- replay implications: replay suspended/throttled independently.
- recovery: gradual ramp-up after provider stabilization.
- isolation expectation: unaffected connectors continue.

## Replay Storm (many concurrent replay requests)
- expected degradation: replay backlog growth.
- protections: replay quota caps and prioritization below live ingestion.
- replay implications: completion latency increases but correctness preserved.
- recovery: queue shaping, staged replay admission.
- isolation expectation: live SLO protected.

## Massive Historical Backfill
- expected degradation: elevated storage and queue pressure.
- protections: backfill lane throttling and chunked windows.
- replay implications: replay scans may slow; isolation preserved.
- recovery: adaptive cadence and backlog drain.
- isolation expectation: no tenant starvation.

## Global Connector Auth Invalidation
- expected degradation: affected connector paused across tenants.
- protections: auth-failure isolation + explicit remediation workflow.
- replay implications: replay for affected connector paused.
- recovery: credential remediation + recovery sync.
- isolation expectation: other connectors unaffected.

## Dead-Letter Flooding
- expected degradation: unresolved ingestion gaps.
- protections: dead-letter alarms and controlled retries.
- replay implications: replay-based remediation pipeline required.
- recovery: batch remediation + targeted re-ingestion.
- isolation expectation: dead-lettered scope isolated.

## Worker Pool Starvation
- expected degradation: lag and retry delay increase.
- protections: per-lane quotas and lease timeout recovery.
- replay implications: replay lane throttled first.
- recovery: pool rebalance and queue prioritization.
- isolation expectation: critical live lanes retain capacity.

## Replay Backlog Explosion
- expected degradation: delayed replay completion.
- protections: admission controls and replay priority classes.
- replay implications: trust still maintained with checkpointed resumability.
- recovery: staged replay windows and operator scheduling.
- isolation expectation: no live cursor mutation.

## Source-Side Ordering Instability
- expected degradation: ordering anomaly rates rise.
- protections: overlap windows + precedence rules.
- replay implications: replay ordering verification required before trust.
- recovery: broader reconciliation windows.
- isolation expectation: anomaly localized to affected connector scopes.
