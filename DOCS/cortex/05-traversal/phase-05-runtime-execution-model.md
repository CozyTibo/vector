# Phase 05 — Runtime execution model (traversal engine)

**Normative step:** **16**. **Freeze bundle:** **FF-5** (runtime design locks with doctrine).  
**Depends on:** `phase-05-multigraph-model-doctrine.md`, `phase-05-walk-policy-doctrine.md`, `phase-05-walk-diagnostics-doctrine.md`, `phase-05-hop-receipt-doctrine.md`, `phase-05-walk-execution-strategy-doctrine.md`.

---

## 1. Constitutional intent

Specify the **reference execution semantics** for the traversal engine: frontier representation, expansion order, memory bounds, concurrency model — **without** mandating a programming language.

---

## 2. Explicit anti-goals

- Non-deterministic parallelism that reorders neighbor expansion.  
- Unbounded frontier in sync mode.  
- Global mutable caches without tenant isolation keys.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **Frontier** | Ordered structure of `(node_id, depth, path_context_id)` per policy. |
| **path_context_id** | Opaque deterministic id derived from path fingerprint prefix — prevents accidental merge of distinct paths. |
| **Concurrency model** | Default **single-threaded per walk**; optional **partition-parallel build** for index jobs only with merge rules in index job doctrine. |

---

## 4. Deterministic semantics

**RULE REM-01:** Neighbor expansion **MUST** follow multigraph ordering **sequentially** within a hop.  
**RULE REM-02:** **Cycle semantics:** if `detect_cycles=true`, first re-entry edge that closes a cycle **MUST** set `termination_reason=cycle_cut` when policy says stop-on-cycle; else record diagnostic and skip edge per `skip_reason=deduped_revisit_forbidden`.

---

## 5. Replay semantics

Engine internal queues **MUST NOT** appear in artifacts; only emitted receipts and result matter.

---

## 6. Temporal semantics

Validity filter applied **before** enqueue neighbors.

---

## 7. Provenance semantics

Each dequeued expansion **MUST** emit receipt before child enqueue when `emit_receipt_before_expand=true` (default **true** for audit mode).

---

## 8. Serialization contracts

N/A at runtime level except emitted artifacts follow walk result contract.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-REM-01** | Parallel async tasks mutating shared walk state without serialization. |
| **FS-REM-02** | Exceeding `max_frontier` without termination. |

---

## 10. Verification implications

- **G-P05-RT-01:** Stress — deterministic output on 100 runs single-threaded.  
- **G-P05-RT-02:** Memory bound — synthetic graph hits cap with stable diagnostic.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Hostile tenant | Degenerate star graph DOS | Budget caps + wall_ms on sync. |

---

## 12. Negative examples

**ILLEGAL:** `Promise.all` on neighbors without ordering merge step.

---

## 13. CI oracle expectations

Large fixture graphs; property tests for cycle + budget interactions.
