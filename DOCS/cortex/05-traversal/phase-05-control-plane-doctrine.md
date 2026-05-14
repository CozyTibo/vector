# Phase 05 — Control plane doctrine (operator surfaces)

**Normative step:** **24**. **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-tenant-verification-integration.md`, `phase-04-control-plane-doctrine.md` (IA patterns).

---

## 1. Constitutional intent

Specify **operator/admin** surfaces for index lag, walk queue, abort-class breakdown, budget hit rate — **structural telemetry tables**, not intelligence dashboards.

---

## 2. Explicit anti-goals

- “Insight tiles,” trend narratives, anomaly ML.  
- Editing org truth via graph UI.

---

## 3. Formal terminology

| Surface | Data |
| ------- | ---- |
| **Traversal queue** | job ids, states, tenant, partition, ages. |
| **Abort classes** | Count by `termination_reason` / `error_code`. |
| **Budget histogram** | Buckets of `max_hops` hit rates — integers only. |

---

## 4. Deterministic semantics

Tables **MUST** default sort: `tenant_id`, then `updated_at` descending — documented; not hashed.

---

## 5. Replay semantics

Control plane reads **MUST NOT** mutate walk artifacts; actions (cancel, retry) go through APIs with idempotency.

---

## 6. Temporal semantics

Display `t_as_of` used by last walk per filter — not “current causality.”

---

## 7. Provenance semantics

Drill-down to walk shows **canonical JSON** view (pretty-printed) read-only.

---

## 8. Serialization contracts

API responses follow `phase-05-walk-api-contracts.md` for walk fetch; aggregate endpoints sorted keys.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-CP-01** | Mutation of `walk_result` via control plane without dedicated audited action. |
| **FS-CP-02** | Exploration walks visible without explicit operator toggle. |

---

## 10. Verification implications

**G-P05-CP-01:** RBAC matrix for routes.  
**G-P05-CP-02:** UI snapshot tests optional — API contract mandatory.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Operator | Export walks to external LLM | Out of scope; data classification policy external — OCTS still no narrative fields. |

---

## 12. Negative examples

**ILLEGAL endpoint:** `GET .../walks/summarize?prompt=...`

---

## 13. CI oracle expectations

Admin route registration tests; deny-by-default for non-admin roles.
