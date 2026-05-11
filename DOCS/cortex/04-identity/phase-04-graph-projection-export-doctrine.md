# Phase 04 — OrgGraphProjectionV1 export (P04-13)

**Status:** normative **frozen export contract** for Phase **05** — derived from org tables, not from Phase 03 DAG.  
**Role:** deterministic **`OrgGraphProjectionV1`** JSON + **SHA-256** over a canonical serialization (**G-P04-EXP-01**).

---

## 1) Schema — `OrgGraphProjectionV1` (version 1)

Top-level object (the **`projection`** payload, without outer admin wrapper):

| Field | Type | Meaning |
| ----- | ---- | ------- |
| **`projection_schema_version`** | `int` | **1** for this doctrine revision. |
| **`tenant_id`** | `string` | UUID string. |
| **`engine_build_ref`** | `string` | Runtime build tag (`vector.domains.cortex.identity.projection_export`). |
| **`nodes`** | `array` | Sorted by **`id`** ascending (UUID string). |
| **`edges`** | `array` | Sorted by **`id`** ascending (UUID string). |

### 1.1 Node kinds

| **`kind`** | Required fields |
| ---------- | ---------------- |
| **`org_entity`** | `id`, `entity_kind`, `identity_key_fingerprint`, `lifecycle_state`, `tombstoned_at` (ISO8601 or `null`). |
| **`org_primitive`** | `id`, `org_entity_id`, `primitive_kind`, `primitive_key` (64 hex), `lifecycle_state`. |

Primitive nodes **must not** embed full Phase 3.5 envelopes in v1 (minimization); evidence remains on the persisted primitive row and is reachable via org admin inspectors.

### 1.2 Edge kinds

| **`kind`** | Meaning |
| ---------- | ------- |
| **`org_meaning_link`** | One authoritative ledger row: endpoints, `link_type`, `link_class`, `link_authority`, `confidence_class`, sorted **`evidence_raw_record_ids`**, optional `rule_id`, half-open validity (`valid_from` / `valid_to` ISO or `null`), `revoked_at`, `supersedes_link_id`, promotion pointers. |

Only rows with **`link_authority='authoritative'`** are exported.

---

## 2) Stable hash (**G-P04-EXP-01**)

- Serialize **`projection`** (the inner object above **without** any hash field) with **`json.dumps(..., sort_keys=True, separators=(',', ':'))`**, UTF-8.
- **`stable_hash_sha256`** = lowercase hex of **SHA-256** over those bytes.
- Rebuilding from the same persisted org rows **must** yield the **same** hash (**verification gate** recomputes twice per tenant).

---

## 3) Verification + admin

| Gate | Meaning |
| ---- | ------- |
| **G-P04-10** | Static: schema allowlists + forbidden topology / materialization token scan on canonical export JSON. |
| **G-P04-EXP-01** | Static fixture determinism + per-tenant: two builds → identical `stable_hash_sha256`. |

- `GET /admin/tenants/{tenant_id}/cortex/identity/graph-projection` — returns schema version, `projection`, and `stable_hash_sha256`.

Ontology pointer keys: `org_graph_projection_export_surface_version`, `org_graph_projection_export_route`, `org_graph_projection_export_doctrine_anchors`.

---

## 4) Normative references

- `phase-04-graph-boundary-doctrine.md` — boundary vs Phase 03/05.
- `phase-04-implementation-plan.md` — Stage P04-13, §18 P05 compatibility.
