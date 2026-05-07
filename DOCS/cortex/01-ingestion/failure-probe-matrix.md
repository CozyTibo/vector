# Failure Probe Matrix

## Purpose
Define mandatory failure probes and expected preservation behavior.

## Probe Entries
- Connector auth expiration
  - behavior: transition connector to `AUTH_FAILED`, halt affected runs only.
  - invariants: tenant/connector isolation preserved.
  - observability: auth failure alerts and lag growth signal.
  - recovery: credential refresh + recovery sync.
  - replay impact: replay lane for connector paused, others unaffected.
  - degradation: localized ingestion pause.

- Partial pagination failure
  - behavior: retain persisted pages, retry failed page token.
  - invariants: no checkpoint regression, no duplicate durable writes.
  - observability: page failure counters and retry metrics.
  - recovery: resume from last stable checkpoint.
  - replay impact: replay checkpoint continuity maintained.
  - degradation: reduced throughput.

- Rate-limit exhaustion
  - behavior: enter `THROTTLED`, honor retry-after.
  - invariants: no data mutation or checkpoint corruption.
  - observability: throttle duration and budget metrics.
  - recovery: adaptive backoff.
  - replay impact: replay throttled independently.
  - degradation: lag increase within bounded policy.

- Duplicate payload delivery
  - behavior: dedupe no-op on duplicate idempotency key.
  - invariants: idempotency law preserved.
  - observability: duplicate suppression counters.
  - recovery: none required.
  - replay impact: replay equivalence unaffected.
  - degradation: none.

- Malformed payload
  - behavior: quarantine malformed object, continue run.
  - invariants: checkpoint progression safe.
  - observability: quarantine queue growth and payload error classes.
  - recovery: operator remediation + targeted sync.
  - replay impact: malformed payload remains traceable.
  - degradation: localized data gap.

- Replay interruption
  - behavior: replay run enters `FAILED`/`RETRYING` with checkpoint retention.
  - invariants: live/replay isolation preserved.
  - observability: stalled replay alerts.
  - recovery: resumable replay from checkpoint.
  - replay impact: divergence report delayed.
  - degradation: replay SLA breach, live unaffected.

- Checkpoint corruption
  - behavior: detect anomaly, revert to previous stable checkpoint.
  - invariants: monotonic progression restored.
  - observability: critical integrity alert.
  - recovery: controlled resumption and incident annotation.
  - replay impact: bounded replay backtrack possible.
  - degradation: temporary re-fetch overhead.

- Queue visibility timeout failure
  - behavior: re-lease job; idempotent processing prevents duplication.
  - invariants: no duplicate durable writes.
  - observability: lease timeout counters.
  - recovery: automatic retry.
  - replay impact: replay jobs follow same lease semantics.
  - degradation: latency increase.

- Worker crash during persistence
  - behavior: unacked job retried; dedupe and checkpoint sequencing preserve correctness.
  - invariants: transaction boundary laws preserved.
  - observability: worker crash + retry burst metrics.
  - recovery: automatic with bounded retries.
  - replay impact: replay progress delay only.
  - degradation: transient backlog growth.

- Replay overlap conflict
  - behavior: reject or serialize conflicting replay scopes.
  - invariants: replay isolation preserved.
  - observability: replay conflict event logs.
  - recovery: rerun with non-overlapping scope.
  - replay impact: avoids non-deterministic overlap.
  - degradation: replay queue delay.

- Connector starvation
  - behavior: fairness scheduler rebalances lane quotas.
  - invariants: connector isolation and liveliness targets.
  - observability: lag skew and starvation indicators.
  - recovery: quota rebalance and priority tuning.
  - replay impact: replay budget reduced before live starvation.
  - degradation: bounded lag skew.

- Dead-letter buildup
  - behavior: alert + throttle inflow + remediation workflow.
  - invariants: failed tasks remain auditable and isolated.
  - observability: dead-letter growth alarms.
  - recovery: replay/recovery jobs after remediation.
  - replay impact: dead-letter replay path required.
  - degradation: partial ingestion coverage.

- Partial transaction persistence
  - behavior: maintain durable writes, retry missing stages idempotently.
  - invariants: no rollback of committed raw writes.
  - observability: partial-transaction anomaly counters.
  - recovery: stage-specific retries.
  - replay impact: replay can verify consistency.
  - degradation: temporary checkpoint/run status mismatch.

- Source ordering drift
  - behavior: preserve source metadata and ordering hints; reconcile with precedence rules.
  - invariants: chronology policy remains explicit.
  - observability: ordering anomaly counters.
  - recovery: overlap fetch and reconciliation.
  - replay impact: replay ordering validation required.
  - degradation: potential temporary chronology ambiguity.
