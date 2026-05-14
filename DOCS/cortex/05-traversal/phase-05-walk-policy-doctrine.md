# Phase 05 — Walk policy doctrine

**Normative step:** **8**. **Freeze bundle:** **FF-2**.  
**Depends on:** `phase-05-multigraph-model-doctrine.md`, `phase-05-temporal-walk-doctrine.md`, `phase-05-normative-index.md`.

---

## 1. Constitutional intent

Define **budgets**, **allowed hop classes**, **filters**, and **deterministic tie-breaks** as a **versioned, hashable policy object** separate from engine code.

---

## 2. Explicit anti-goals

- Learned policies or per-tenant opaque “weights.”  
- Unlimited budgets on sync path.  
- Policy objects containing free-text fields (except optional **`human_label`** **TELEMETRY-EXCLUDED**).

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **walk_policy** | Canonical JSON object hashed to **`policy_hash`**. |
| **Budget fields** | `max_hops`, `max_frontier`, `max_wall_ms` (sync only), `max_edges_visited`. |
| **Hop class filter** | Closed set: e.g. `reports_to`, `contributed_to`, … — **MUST** match export `link_type_code` enum. |

---

## 4. Deterministic semantics

**RULE WP-01:** Tie-break order **MUST** be encoded in policy as explicit ordered list (e.g. `["fingerprint", "org_link_id"]`).  
**RULE WP-02:** Default policy is **tenant-configurable** only within **closed** bounds table (max caps) — see readiness doctrine.

---

## 5. Replay semantics

Walk replay **MUST** pin `policy_hash`; any policy drift **MUST** change hash and therefore **walk lineage**.

---

## 6. Temporal semantics

Policy **MAY** include `respect_validity: true` (default **true**); when false, **MUST** set `exploration_mode=true` OR `diagnostics_only=true` per exploration doctrine.

---

## 7. Provenance semantics

`policy_version` integer **MUST** increment on any semantic change to defaults registry.

---

## 8. Serialization contracts

`policy_hash = sha256(canonical_json(walk_policy))` per normative index.  
**FORBIDDEN** keys in hashed body: any `*_telemetry`, `human_label`.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-WP-01** | `max_hops` absent (strict mode). |
| **FS-WP-02** | Wildcard hop class `*` in production mode without exploration partition. |
| **FS-WP-03** | Floating point in policy body. |

---

## 10. Verification implications

- **G-P05-POL-01:** Policy schema validation + cap enforcement.  
- **G-P05-POL-02:** Sync API rejects policies exceeding sync limits.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Phase 07 | Encode ranking as weights in policy | Schema forbids floats; static analysis rejects score-like keys. |

---

## 12. Negative examples

**ILLEGAL:**

```json
{ "edge_weights": { "a": 0.7 } }
```

**LEGAL:**

```json
{ "hop_class_allowlist": ["reports_to"], "tie_break": ["fingerprint", "org_link_id"], "max_hops": 8 }
```

---

## 13. CI oracle expectations

Golden `policy_hash` vectors; mutation tests on tie-break order affecting expansion.
