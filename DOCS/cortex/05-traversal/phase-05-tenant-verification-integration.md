# Phase 05 — Tenant verification integration

**Normative step:** **23**. **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-verification-gates-doctrine.md`, `phase-04-verification-gates-doctrine.md` (pattern).

---

## 1. Constitutional intent

Define the **`org_graph_traversal`** slice in tenant/admin verification aggregates so operators see **structural health** of OCTS without cognition tiles.

---

## 2. Explicit anti-goals

- Showing “graph insights” or semantic health scores.  
- Mixing Phase 03 verification failures into OCTS slice.

---

## 3. Formal terminology

| Field (sketch) | Meaning |
| -------------- | ------- |
| `octs_program_freeze_version` | Must match normative index. |
| `last_index_epoch` | Latest committed epoch. |
| `index_lag_epochs` | `latest_requested - committed` if applicable. |
| `walk_queue_depth` | Count of queued/running jobs. |
| `last_gate_bundle` | Hash of gate results file attached to run. |

---

## 4. Deterministic semantics

Aggregate JSON **MUST** sort keys; integers only for counts — no floats.

---

## 5. Replay semantics

Verification run **MUST** store `octs_slice_hash` covering aggregate sub-object for certification.

---

## 6. Temporal semantics

Timestamps in slice are **UTC** ISO strings — telemetry allowed outside hashed certification body per Phase 04 pattern.

---

## 7. Provenance semantics

Slice **MUST** reference `verification_run_id` and `tenant_id`.

---

## 8. Serialization contracts

Follow Phase 04 verification aggregate canonical rules where applicable; deltas documented in gap matrix.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-TV-01** | Slice includes free-text connector errors > 4KiB. |
| **FS-TV-02** | Missing `octs_program_freeze_version` when OCTS enabled. |

---

## 10. Verification implications

**G-P05-TVER-01:** Schema validation of slice in CI using golden tenant fixture.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| UI | Pretty narrative from slice enums | UI copy layer only; slice remains enums. |

---

## 12. Negative examples

**ILLEGAL:** `"insight": "walks healthy"` in slice JSON.

---

## 13. CI oracle expectations

Integration test: run tenant verification with OCTS disabled → slice absent; enabled → slice present with zeros.
