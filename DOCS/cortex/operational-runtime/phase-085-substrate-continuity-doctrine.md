# Phase 08.5 — Substrate continuity doctrine

**Status:** normative.  
**Implements:** Steps 5–6 · **G-P085-CONT-01**, **G-P085-PROG-01**.

---

## Continuation state machine

```
CREATED → WAITING → RESUMED → COMPLETED
              ↓         ↑
           STALLED → RECOVERING
              ↓
           FAILED (terminal, operator)
```

| State | Meaning |
| ----- | ------- |
| **WAITING** | Phase completed enqueue; async dependency outstanding |
| **RESUMED** | Resume receipt accepted; downstream phase enqueued |
| **STALLED** | Heartbeat exceeded `T_stall` |
| **RECOVERING** | Watchdog or operator recovery in flight |
| **COMPLETED** | Phase 07+ chain satisfied for this wait point |
| **FAILED** | Unrecoverable; requires operator |

---

## Waiting kinds (closed enum)

| `waiting_on` | Async dependency |
| ------------ | ---------------- |
| `TCRE_COMPLETION` | `CortexTcreReconstructionJob` |
| `TRAVERSAL_COMPLETION` | OCTS walk batch (future) |
| `INDEX_PUBLISH` | Retrieval epoch publish barrier (future) |

---

## Durable model

**Table:** `cortex_pipeline_continuation_states` (one row per `substrate_pipeline_run_id`).

**Required fields:** tenant_id, current_phase, waiting_on, async_job_id, continuation_status, continuation_nonce, resume_identity_digest, resume_receipt_hash, last_heartbeat_at, retry_count, recovery_required.

---

## Autonomous progression law (**G-P085-PROG-01**)

After post-ingestion refresh enqueues phase 02:

1. Phases **02–05** chain synchronously via `chain_after_phase_v1`.
2. Phase **06** MUST persist continuation `WAITING` / `TCRE_COMPLETION` — **MUST NOT** silently return without durable wait state.
3. TCRE completion MUST call `resume_pipeline_after_tcre_completion_v1` (not ad-hoc enqueue only).
4. Phase **07** completion MUST call `on_retrieval_publish_completed_for_pipeline_v1`.
5. Phase **08** completion MUST `mark_continuation_completed_v1`.

**PIPE-085-01:** `chain_after_phase_v1` returning `None` after TCRE is **not** an error if continuation row exists.

---

## Heartbeat

- Updated on: wait create, TCRE callback, watchdog tick, recovery attempt.
- `T_stall` default **1800s** (`CORTEX_SUBSTRATE_CONTINUATION_STALL_SECONDS`).

---

## Idempotency

- `resume_identity_digest = H(tenant, pipeline_run, async_job_id, waiting_on)`
- `resume_receipt_hash = H(resume_identity_digest, continuation_nonce, async_status)`
- Duplicate receipt: no second phase-07 enqueue.

---

## Operational metrics

| Metric | Type |
| ------ | ---- |
| `substrate_continuation_waiting_gauge` | gauge by tenant |
| `substrate_continuation_stall_total` | counter |
| `substrate_resume_duplicate_total` | counter |
| `substrate_phase_07_enqueue_total` | counter |
