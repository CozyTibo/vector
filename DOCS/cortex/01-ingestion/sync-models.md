# Sync Models

## 1) Initial Historical Backfill
- Trigger: new connector enablement or tenant bootstrap.
- Ordering: oldest-to-newest where API supports historical ordering.
- Cursor: historical lower bound + pagination token.
- Idempotency: dedupe by source identity + payload fingerprint.
- Replay impact: creates baseline replay corpus.
- Throughput: throttled lane, lower priority than live.
- Failure semantics: resumable from checkpoint; partial completion allowed.

## 2) Incremental Sync
- Trigger: scheduled interval or operator action.
- Ordering: window-based by `updated_at`/cursor marker.
- Cursor: rolling high-watermark.
- Idempotency: strict duplicate suppression required.
- Replay impact: must preserve change history and edits.
- Throughput: high-priority live lane.
- Failure semantics: retry with bounded backoff, degrade to recovery mode on repeated failure.

## 3) Scheduled Polling Sync
- Trigger: scheduler cadence by connector policy.
- Ordering: bounded window batches; no cross-connector total ordering.
- Cursor: policy-driven polling cursor.
- Idempotency: page overlap tolerated by dedupe layer.
- Replay impact: polling metadata retained for deterministic reruns.
- Throughput: fairness scheduler across tenants.
- Failure semantics: throttled retries and health-state transition.

## 4) Future Webhook Sync (Hybrid)
- Trigger: provider webhook event.
- Ordering: webhook arrival order, reconciled against polling cursor.
- Cursor: webhook event id plus polling cursor reconciliation.
- Idempotency: webhook dedupe required.
- Replay impact: webhook envelopes replayable through same ingestion contract.
- Throughput: interrupt lane but bounded to avoid starvation.
- Failure semantics: fallback to polling reconciliation on webhook gaps.

## 5) Replay Sync
- Trigger: replay job registration.
- Ordering: replay scope ordering by source chronology.
- Cursor: replay-specific cursor namespace.
- Idempotency: replay-safe dedupe via replay context + source identity.
- Replay impact: foundational mode.
- Throughput: isolated replay lane.
- Failure semantics: checkpointed resumability mandatory.

## 6) Partial Replay Sync
- Trigger: schema/extraction bug remediation on bounded scope.
- Ordering: scope-local chronological order.
- Cursor: bounded cursor window.
- Idempotency: strict to avoid duplicate superseding artifacts.
- Replay impact: localized correction.
- Throughput: controlled to avoid live starvation.
- Failure semantics: resume from partial checkpoint.

## 7) Tenant-Wide Resync
- Trigger: operator emergency recovery.
- Ordering: connector-by-connector then object stream order.
- Cursor: reset + controlled historical traversal.
- Idempotency: full dedupe plus replay metadata required.
- Replay impact: high blast radius.
- Throughput: budgeted and approval-gated.
- Failure semantics: staged rollback/continuation policy.

## 8) Connector Recovery Sync
- Trigger: connector exits degraded/auth recovered state.
- Ordering: catch-up window then normal incremental.
- Cursor: last healthy checkpoint + overlap window.
- Idempotency: overlap-safe dedupe required.
- Replay impact: preserves continuity without full replay.
- Throughput: burst-limited.
- Failure semantics: returns to degraded on repeated failures.

## 9) Targeted Object Sync
- Trigger: operator request or remediation workflow.
- Ordering: object local revision chronology.
- Cursor: object-scoped cursor key.
- Idempotency: object identity + source version key.
- Replay impact: supports surgical correction.
- Throughput: low-cost lane.
- Failure semantics: isolate failures to object scope.
