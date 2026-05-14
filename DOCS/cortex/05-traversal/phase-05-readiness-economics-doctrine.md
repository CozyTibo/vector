# Phase 05 — Readiness and economics doctrine

**Normative step:** **25**. **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-runtime-execution-model.md`, `phase-05-derived-index-contract-doctrine.md`, `phase-05-walk-api-contracts.md`.

---

## 1. Constitutional intent

Define **bounded probes** for worst-case degree, walk cost, storage growth — producing **numbers and thresholds**, not recommendations.

---

## 2. Explicit anti-goals

- “You should refactor X” output.  
- Unbounded probes on production tenants without explicit job mode.

---

## 3. Formal terminology

| Gate ID | Role |
| ------- | ---- |
| **G-P05-ECO-01** | Max out-degree observed in projection ≤ tenant `OCTS_MAX_OUT_DEGREE` (config int). |
| **G-P05-ECO-02** | Synthetic worst-case walk from hub ≤ `max_wall_ms` async budget. |
| **G-P05-ECO-03** | Derived index storage bytes per edge ≤ budget table. |

---

## 4. Deterministic semantics

Probes **MUST** use pinned fixtures or **explicit** `probe_tenant_id` allowlisted — no random tenant pick in CI.

---

## 5. Replay semantics

Economics job outputs `economics_receipt_hash` over sorted integer stats map — reproducible.

---

## 6. Temporal semantics

Probes use explicit anchor — default latest only in **non-CI** contexts.

---

## 7. Provenance semantics

Receipt links to `projection_content_hash` used for measurement.

---

## 8. Serialization contracts

Stats map keys sorted; values integers or **bignums as strings** without floats.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-ECO-01** | Probe modifies tenant data. |
| **FS-ECO-02** | Missing threshold table version in receipt. |

---

## 10. Verification implications

Gates listed in §3 — `hard_fail` for CI fixtures; `warn` for production monitoring optional.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Phase 09 | Use economics as “performance insight product” | Output is numeric receipt only; presentation outside OCTS. |

---

## 12. Negative examples

**ILLEGAL receipt field:** `"recommendation": "shard the graph"`

---

## 13. CI oracle expectations

Hostile hub fixture triggers threshold breach predictably.
