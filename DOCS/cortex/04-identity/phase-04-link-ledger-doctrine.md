# Phase 04 — Org Link Ledger Doctrine

**Status:** normative — **P04-04**.  
**Audience:** implementers, verification authors.  
**Runtime:** `vector.domains.cortex.identity.link_ledger`, table **`cortex_org_links`**.  
**Companion:** `phase-04-architecture-identity-linking-doctrine.md`, `phase-04-topology-vs-meaning-doctrine.md`, `phase-04-org-entity-and-handle-doctrine.md`.

---

## 1) Purpose

The **link ledger** stores **authoritative org-meaning links**: typed relations between **org entities** (handles) with **evidence or explicit rule provenance**, **temporal validity**, **confidence class**, and **supersession** metadata. It is **not** Phase 03 topology (materialization / structural edges) and **not** Phase 3.5 continuity edge contracts.

---

## 2) Row model (v1)

| Field | Meaning |
| ----- | ------- |
| **`id`** | Primary UUID for the link row (server-generated). |
| **`tenant_id`** | Tenant scope; all links are tenant-isolated. |
| **`link_type`** | Closed string discriminant for org-meaning relation (must **not** equal any `CanonicalStructuralEdgeKind` or `ContinuityEdgeKind` value — **G-P04-08** alignment). |
| **`source_entity_id`** | Org entity UUID (FK `cortex_org_entities`). |
| **`target_entity_id`** | Org entity UUID (FK `cortex_org_entities`). |
| **`evidence_raw_record_ids`** | JSON array of `raw_ingestion_records.id` integers; may be empty only when **`rule_id`** is set (**G-P04-LINK-01** / **G-P04-06**). |
| **`rule_id`** | Optional explicit linkage rule identifier (fixture / deterministic engine id). Non-empty `rule_id` satisfies evidence-or-rule when evidence list is empty. |
| **`confidence_class`** | Non-ranking structural confidence label (Phase 03-compatible string). |
| **`valid_from` / `valid_to`** | Half-open validity `[valid_from, valid_to)` in UTC; `NULL` **open** end per axis (implementation interprets as unbounded on that side). |
| **`revoked_at`** | When set, link is revoked (does not delete history). |
| **`supersedes_link_id`** | Optional self-FK: replacement / correction chain. |
| **`link_authority`** | `authoritative` (default in P04-04) — candidate links deferred to P04-05. |
| **`metadata_json`** | Bounded operator / provenance hints. |
| **`engine_build_ref`** | Writer version stamp. |

**DB constraint:** each row must satisfy **evidence OR rule**:  
`jsonb_array_length(evidence_raw_record_ids) > 0 OR (rule_id IS NOT NULL AND trim(rule_id) <> '')`.

---

## 3) Temporal overlap (authoritative)

For the **same** `(tenant_id, link_type, source_entity_id, target_entity_id)`, **non-revoked** authoritative rows with overlapping **active** validity intervals are **invalid** when both intervals are treated as half-open and “active now” is not the test — **verification** and **unit tests** enforce non-overlap for authoritative edges in v1 (strict interpretation: no two rows may have overlapping `[effective_start, effective_end)` where effective bounds substitute `NULL` with ±infinity for comparison).

---

## 4) Verification

- **G-P04-LINK-01** — Static contract: material passed to the ledger runtime must satisfy evidence-or-rule; exercised by fixtures (no DB).
- **G-P04-06** — Persisted rows for the tenant must satisfy the same predicate (DB scan).

---

## 5) Admin (read-only, P04-04)

- **List:** `GET /admin/tenants/{tenant_id}/cortex/identity/links`
- **Detail:** `GET /admin/tenants/{tenant_id}/cortex/identity/links/{link_id}`

Inspectors expose **raw evidence ids**, **`rule_id`**, and **confidence** per operator debug path.

---

## References

- `phase-04-implementation-plan.md` — Stage P04-04  
- `phase-04-normative-index.md`
