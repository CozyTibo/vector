# Phase 05 — Walk result contract

**Normative step:** **9**. **Freeze bundle:** **FF-3**.  
**Depends on:** `phase-05-traversal-vs-reasoning-doctrine.md`, `phase-05-walk-policy-doctrine.md`, `phase-05-observed-vs-derived-doctrine.md`, `phase-05-normative-index.md`.

---

## 1. Constitutional intent

Define the **canonical walk result** as a citeable **evidence object**: stable JSON, stable hashes, explicit termination, hop receipts, diagnostics — suitable for certification archives.

---

## 2. Explicit anti-goals

- Embedding raw projection blob in result.  
- Including wall-clock timings inside **`walk_result_hash`** input.  
- Variable schema by tenant without `schema_version` field.

---

## 3. Formal terminology

| Field | Role |
| ----- | ---- |
| `octs_schema_version` | UInt — **MUST** increment on breaking canonical change. |
| `walk_id` | UUIDv4 string lowercase. |
| `walk_result_hash` | SHA-256 over **hash_body** (defined below). |
| `hash_body` | Canonical JSON of object with **exact key set** per §8. |

---

## 4. Deterministic semantics

**RULE WR-01:** `hash_body` **MUST** include: `octs_schema_version`, `temporal_anchor`, `policy_hash`, `start_node_ids` (sorted), `termination_reason`, `hop_receipts` (sorted by `hop_sequence`), `execution_path_contains_derived`, `path_edge_fingerprints_ordered` (array in visit order).  
**RULE WR-02:** `hash_body` **MUST NOT** include: `telemetry`, `wall_ms`, `worker_hostname`, `human_label`, `request_trace_id`.

---

## 5. Replay semantics

**REPLAY REQUIREMENT WR-01:** Byte-identical `hash_body` ⇒ identical `walk_result_hash`.  
**REPLAY REQUIREMENT WR-02:** Telemetry may differ; verifier compares **hash_body** only.

---

## 6. Temporal semantics

`temporal_anchor` in `hash_body` **MUST** be the canonical object per `phase-05-temporal-walk-doctrine.md` §3.1 serialized under **`OCTS-CANON-1`** (`phase-05-canonicalization-profile.md`).

---

## 7. Provenance semantics

`hop_receipts` in hash_body are full canonical hop receipts per hop receipt doctrine (telemetry stripped).

---

## 8. Serialization contracts

**Omission normalization table (normative):**

| Condition | Serialization |
| --------- | --------------- |
| Optional false boolean | **Omit** key |
| Optional empty array | **Omit** key |
| Required empty array | Present as `[]` |

**Path multiset:** `path_edge_fingerprints_ordered` **MUST** list each traversed edge **once per visit** in order.

**Unicode:** NFC on all strings entering hash.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-WR-01** | `walk_result_hash` mismatch vs recompute from returned body. |
| **FS-WR-02** | Telemetry nested under non-telemetry key to smuggle into hash. |
| **FS-WR-03** | Duplicate `hop_sequence`. |

---

## 10. Verification implications

- **G-P05-HASH-01:** Recompute hash in CI from fixture JSON.  
- **G-P05-HASH-02:** Telemetry separation — inject huge telemetry, hash stable.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Cache layer | Strip receipts to save space | Hash requires receipts; gate fails. |

---

## 12. Negative examples

**ILLEGAL hash input:** nested `{"telemetry": {"wall_ms": 3}}` inside `hash_body`.  
**LEGAL:** sibling `telemetry` key outside `hash_body` at API root only.

---

## 13. CI oracle expectations

Golden files under `backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/walks/` with expected hashes; differential tests for omission rules.
