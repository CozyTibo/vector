# Phase 05 — Index build job doctrine

**Normative step:** **14**. **Freeze bundle:** **FF-4**.  
**Depends on:** `phase-05-derived-index-contract-doctrine.md`, `phase-05-idempotency-and-retry-doctrine.md` (cross).

---

## 1. Constitutional intent

Define **async**, **crash-safe**, **idempotent** index materialization with visible states — no silent partial publish.

---

## 2. Explicit anti-goals

- Reusing Celery task id as `index_epoch`.  
- Losing build progress without detectable `FAILED` state.  
- Concurrent publishes without serialization.

---

## 3. Formal terminology

| State | Meaning |
| ----- | ------- |
| `QUEUED` | Job accepted, idempotency key reserved. |
| `BUILDING` | Worker owns partition; writes to **shadow** storage. |
| `VALIDATING` | Hash + lineage checks running. |
| `PUBLISHING` | Atomic barrier in progress. |
| `COMMITTED` | New epoch visible. |
| `FAILED` | Terminal; no partial publish. |

---

## 4. Deterministic semantics

**RULE IBJ-01:** At most **one** `BUILDING` job per `index_partition_key` at a time — enforced by DB lease row.  
**RULE IBJ-02:** Idempotency key = `sha256(tenant_id + projection_content_hash + derivation_rule_id + target_schema_version)`.

---

## 5. Replay semantics

Re-running job with same idempotency key **MUST** yield same final `(index_epoch, index_content_hash)` or deterministic `FAILED` with error code.

---

## 6. Temporal semantics

Job **MUST** pin `projection_content_hash` and `materialized_for_anchor` at start.

---

## 7. Provenance semantics

Job receipt **MUST** list `input_projection_hash`, `output_index_hash`, `index_epoch`.

---

## 8. Serialization contracts

Job status API returns canonical sorted JSON per normative index.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-IBJ-01** | `COMMITTED` without `VALIDATING` success record. |
| **FS-IBJ-02** | Two `COMMITTED` with same `index_epoch` different hashes. |
| **FS-IBJ-03** | Shadow data readable as live without `BUILDING` gate. |

---

## 10. Verification implications

- **G-P05-JOB-01:** State machine illegal transition tests.  
- **G-P05-JOB-02:** Crash injection between VALIDATING and PUBLISHING.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Operator | Force publish via SQL | App-level barrier + CI read checks. |

---

## 12. Negative examples

**ILLEGAL:** status `COMMITTED` while shadow prefix still equals live prefix without swap record.

---

## 13. CI oracle expectations

Lease contention tests; kill -9 worker mid-build → recovery to `FAILED` or resume deterministic.

---

## 14. Reference implementation (runtime)

- **Module:** `vector.domains.cortex.traversal.index_build_job_contract` (re-exported from `vector.domains.cortex.traversal`).
- **FSM:** `validate_index_build_job_state_transition_v1`, `validate_index_build_job_state_sequence_v1`, `validate_index_build_completion_events_v1` (linear `to_state` chain plus **FS-IBJ-01** — successful `VALIDATING` before first `PUBLISHING` when terminal state is `COMMITTED`).
- **Idempotency:** `compute_index_build_idempotency_key_v1` (**RULE IBJ-02** — canonical JSON array over tenant UUID, projection hash, rule id, target schema version).
- **Leases:** `list_rule_ibj01_simultaneous_building_lease_violations` (**RULE IBJ-01**).
- **Epoch integrity:** `list_fs_ibj02_duplicate_committed_epoch_different_hash_violations` (**FS-IBJ-02**).
- **Shadow visibility:** `validate_fs_ibj03_shadow_store_visibility_v1` (**FS-IBJ-03**).
- **Receipts:** `validate_index_build_job_receipt_v1` (§7 — `input_projection_hash`, `output_index_hash`, `index_epoch`; hashes via `derived_index_contract.assert_index_content_hash_string_v1`).
- **Static gates:** **G-P05-JOB-01** (`verify_gp05_job01_index_build_fsm_illegal_transitions_static`), **G-P05-JOB-02** (`verify_gp05_job02_validating_publish_audit_static`).
- **Fixtures:** `backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/index_build_job/`.
- **Pytest:** `backend/tests/vector/domains/cortex/traversal/test_phase05_step14_index_build_job_contract.py`.
