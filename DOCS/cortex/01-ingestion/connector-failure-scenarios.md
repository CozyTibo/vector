# Connector Failure Scenarios

## Slack
- realistic failures:
  - cursor invalidation, channel access revocation, thread pagination truncation.
- expected handling:
  - scope-local auth/error transitions, overlap polling recovery.
- failure probes:
  - duplicate message delivery, delayed edit events, missing thread page.

## GitHub
- realistic failures:
  - secondary rate limits, webhook/poll mismatch, force-push revision shifts.
- expected handling:
  - throttle-aware pacing, overlap windows, revision-aware dedupe.
- failure probes:
  - updated_at drift, pagination cursor expiry, duplicate issue events.

## Linear
- realistic failures:
  - GraphQL cursor invalidation, partial connection page failures.
- expected handling:
  - checkpointed cursor fallback and scoped recovery sync.
- failure probes:
  - state-transition bursts with overlapping updated_at windows.

## Notion
- realistic failures:
  - nested block traversal failures, delayed `last_edited_time` propagation.
- expected handling:
  - hierarchical rescan windows and targeted page retries.
- failure probes:
  - relation graph drift and duplicate block snapshots.

## Google Docs
- realistic failures:
  - change token invalidation, revision fetch race conditions.
- expected handling:
  - token reset workflow + bounded historical reconciliation.
- failure probes:
  - missing revision segment and comment pagination mismatch.

## Meeting Transcripts
- realistic failures:
  - late transcript corrections, segment reindexing, payload-size truncation errors.
- expected handling:
  - session rescan windows and segment-revision-aware dedupe.
- failure probes:
  - corrected segment replay overlap and out-of-order segment arrival.

## Cross-Connector Common Scenarios
- delayed consistency,
- deleted objects with tombstone gaps,
- duplicate delivery under retry storms,
- historical backfill gaps.
