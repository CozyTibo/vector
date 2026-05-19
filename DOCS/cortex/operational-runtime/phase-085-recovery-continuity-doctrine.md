# Phase 08.5 — Recovery & self-healing doctrine

**Status:** normative.  
**Implements:** Steps 7–9 · **G-P085-DLQ-01**, **G-P085-REC-01**, **G-P085-WATCH-01**.

---

## Dead-letter semantics (**G-P085-DLQ-01**)

Async failures that block progression MUST land in a **recoverable dead-letter** record:

| Field | Purpose |
| ----- | ------- |
| `dead_letter_id` | uuid |
| `pipeline_run_id` | scope |
| `phase_id` | where blocked |
| `async_job_id` | TCRE / walk / etc. |
| `failure_class` | closed enum |
| `replay_safe` | bool |
| `recovery_actions` | ordered list |

**Failure classes:** `tcre_failed`, `tcre_missing_scope`, `celery_lost`, `continuation_missing`, `phase_enqueue_failed`.

**Rule:** DLQ entry MUST NOT auto-retry more than `N_max` times per `resume_receipt_hash`.

---

## Recovery receipts (**G-P085-REC-01**)

Every recovery attempt MUST persist:

```json
{
  "recovery_receipt_digest": "sha256...",
  "action": "resume_phase_07|rebind_tcre|replay_phase_06",
  "continuation_nonce": "...",
  "prior_resume_receipt_hash": "...",
  "outcome": "recovered|skipped|failed"
}
```

Append to `continuation.detail_json.recovery_receipts[]`.

---

## Watchdog (**G-P085-WATCH-01**)

**Task:** `vector.cortex.substrate_pipeline.continuity_watchdog`  
**Schedule:** default 600s beat.

**Algorithm:**

1. `list_stale_waiting_continuations_v1(T_stall)`
2. Mark `STALLED`, `recovery_required=true`
3. If `auto_recover`: `recover_stalled_pipeline_v1(action=auto)`
4. Emit audit log + metric

**Recovery order (auto):**

1. If phase 07 complete → mark continuation complete
2. If TCRE completed → `resume_pipeline_after_tcre_completion_v1`
3. Else rebind latest completed TCRE for tenant
4. Else re-enqueue phase 06 (bounded)
5. Else DLQ + operator alert

---

## Replay safety

Recovery MUST NOT:

- Publish retrieval epoch without materialization pass
- Run synthesis on stale unpublished index
- Duplicate jobs with same idempotency key

---

## Admin recovery actions

| Action | Semantics |
| ------ | --------- |
| `retry_continuation` | Re-run resume with new receipt |
| `rebind_tcre` | Attach latest completed TCRE job |
| `resume_phase_07` | Force enqueue 07 if lawful |
| `replay_callback` | Re-invoke TCRE completion handler |
| `mark_unrecoverable` | FAILED terminal |

See admin cockpit spec.
