# Phase 04 — Org ambiguity + multiplicity (P04-14)

**Status:** normative **org-scoped** multiplicity / unresolved-actor receipts — **distinct** from Phase **03** `cortex_canonical_ambiguity_records` (mapping / canonicalization contest).  
**Role:** unresolved **organizational** multiplicity (e.g. persona collisions, unresolved handle sets) is **healthy state**; the system records it explicitly for operators and downstream **P08** triage — not silent drift.

---

## 1) Data model — `cortex_org_ambiguity_records`

| Column | Meaning |
| ------ | ------- |
| **`tenant_id`** | Tenant scope (`tenants`, CASCADE). |
| **`org_ambiguity_class`** | Closed class string (see §2). |
| **`subject_key`** | Stable operator-facing grouping key (≤512 chars); **unique per tenant among `status='open'`** rows. |
| **`status`** | `open` \| `acknowledged` \| `superseded` \| `void`. |
| **`involved_org_entity_ids`** | JSON array of **UUID strings** — **length ≥ 2** (multiplicity semantics). |
| **`evidence_json`** | Optional structured pointers (link ids, raw ids, notes) — **not** a second truth plane. |
| **`superseded_by_org_ambiguity_id`** | Optional self-FK for replacement rows. |
| **`operator_note`** | Optional short operator annotation. |

**CHECK:** `status` values only; `involved_org_entity_ids` is a JSON array with **at least two** elements.

---

## 2) Closed vocabularies

**`org_ambiguity_class` (v1):** `multiple_persona_unresolved`, `handle_collision_unresolved`, `cross_bundle_persona_gap`.

**`status`:** `open`, `acknowledged`, `superseded`, `void`.

---

## 3) Append rules (`append_org_ambiguity_record`)

- Every **`involved_org_entity_id`** must resolve to an existing **`cortex_org_entities`** row for the same **`tenant_id`**.
- **≥ 2** distinct org entities after de-duplication.
- **`subject_key`** non-empty; normalized strip-only in v1.

---

## 4) Verification

| Gate | Meaning |
| ---- | ------- |
| **G-P04-AMB-01** | Static allowlists + persisted scan: no row references missing / cross-tenant org entities; JSON shape valid. |
| **G-P04-12** | **Warn-only:** open org-ambiguity count ≥ **5000** (same pressure bar as Phase **03** G-P03-04 — explosion signal for operators). |

---

## 5) Admin

- `GET /admin/tenants/{tenant_id}/cortex/identity/org-ambiguities` — list (optional `status`, `org_ambiguity_class` filters).  
- `GET /admin/tenants/{tenant_id}/cortex/identity/org-ambiguities/{record_id}` — detail.  
- `POST /admin/tenants/{tenant_id}/cortex/identity/org-ambiguities` — append.

Ontology pointer keys: `org_ambiguity_runtime_surface_version`, `org_ambiguity_*_route`, `org_ambiguity_runtime_doctrine_anchors`.

---

## 6) Normative references

- Phase **03** ambiguity (canonical): `phase-03-ambiguity-confidence-doctrine.md` — **do not** conflate row types.  
- `phase-04-implementation-plan.md` — Stage P04-14, §12.1 **G-P04-12**.  
- `vector.domains.cortex.identity.org_ambiguity`.
