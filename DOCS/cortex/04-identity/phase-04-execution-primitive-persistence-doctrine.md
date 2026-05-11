# Phase 04 — Execution primitive persistence (P04-12)

**Status:** normative persistence spine for Phase **3.5** execution primitive **envelopes** under Phase **04** org identity.  
**Role:** bind sparse, evidence-first **execution primitives** to **`cortex_org_entities`** so Phase **05** consumes **org-shaped** continuity artifacts — not provider-native graph rows.

---

## 1) Data model — `cortex_org_primitive_instances`

| Column | Meaning |
| ------ | ------- |
| **`tenant_id`** | Tenant scope (CASCADE delete with tenant). |
| **`org_entity_id`** | Org handle this primitive is anchored to (`cortex_org_entities`, RESTRICT). |
| **`primitive_kind`** | Closed string from Phase 3.5 `ExecutionPrimitiveKind` (`work_episode`, …). |
| **`primitive_key`** | Deterministic **64-hex** digest (`derive_primitive_key`) — unique per **`(tenant_id, primitive_key)`**. |
| **`envelope_json`** | Full `ExecutionPrimitiveEnvelope` JSON (must include non-empty **`evidence_raw_record_ids`**). |
| **`lifecycle_state`** | `active` / `superseded` / `revoked`. |

**CHECK:** `jsonb_array_length(envelope_json->'evidence_raw_record_ids') > 0` (Postgres).

---

## 2) Append contract (`append_org_primitive_instance`)

- Org entity must exist and belong to the tenant.
- Envelope must include **`kind`**, **`primitive_key`** (64-char hex), and **`evidence_raw_record_ids`** (JSON array of **positive integers**).
- Runtime rejects empty / invalid evidence lists (**G-P04-PRIM-01** static validation path).

---

## 3) Verification

| Gate | Meaning |
| ---- | ------- |
| **G-P04-09** | Static: primitive key **determinism** + evidence id list validation rules (empty rejected). |
| **G-P04-PRIM-01** | Static evidence contract + persisted scan for rows missing valid evidence (defense if CHECK bypassed). |

---

## 4) Admin

- `GET /admin/tenants/{tenant_id}/cortex/identity/primitive-instances` — list  
- `GET /admin/tenants/{tenant_id}/cortex/identity/primitive-instances/{instance_id}` — detail  
- `POST /admin/tenants/{tenant_id}/cortex/identity/primitive-instances` — append  

Ontology pointer keys: `execution_primitive_persistence_surface_version`, `org_primitive_instances_*_route`, `execution_primitive_persistence_doctrine_anchors`.

---

## 5) Normative references

- Phase 3.5: `DOCS/cortex/03-canonical/phase-35-organizational-continuity-foundation.md`, `vector.domains.cortex.continuity.execution_primitives`  
- Program: `phase-04-implementation-plan.md` — Stage P04-12  
