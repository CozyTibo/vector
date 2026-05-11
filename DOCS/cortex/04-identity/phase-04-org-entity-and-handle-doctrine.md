# Phase 04 — Org Entity & Handle Doctrine

**Status:** normative — **P04-03**.  
**Audience:** implementers, verification authors.  
**Runtime:** `vector.domains.cortex.identity.org_entities`, table **`cortex_org_entities`**.  
**Companion:** `phase-04-architecture-identity-linking-doctrine.md`, `phase-04-normative-index.md`, Phase 03 `phase-03-identity-continuity-doctrine.md` (canonical anchor boundary).

---

## 1) Purpose

An **org entity** (org handle) is a **tenant-scoped** organizational identity carrier used for Phase 04 **linking**, **merge governance**, and **continuity** — **not** a Phase 03 canonical materialization row id and **not** interchangeable with `canonical_entity_id` except as **evidence** or **join hints** per future link-ledger doctrine.

---

## 2) Identity model

| Field | Meaning |
| ----- | ------- |
| **`org_entity_id` (`id`)** | Primary UUID for the org handle; **deterministic** UUIDv5 under a fixed namespace from `(tenant_id, entity_kind, identity_key_fingerprint)`. |
| **`tenant_id`** | Tenant scope; all org entities are tenant-isolated. |
| **`entity_kind`** | Closed set at runtime via `OrgEntityKind` (e.g. `human_actor`, `service_account`, `team`, `workspace`, `repository_asset`, `unknown_placeholder`). |
| **`lifecycle_state`** | `active` \| `tombstoned` \| `superseded`. |
| **`identity_key_fingerprint`** | `sha256` hex of **canonical JSON** (sorted keys) of the **identity material** used only for idempotency and UUIDv5 name derivation — **not** a merge assertion. |
| **`metadata_json`** | Non-authoritative display hints, provenance pointers, operator notes (bounded). |
| **`superseded_by_id`** | Optional FK to replacement entity when lifecycle is `superseded`. |
| **`tombstoned_at`** | Set when provider account is deleted / handle retired; historical links remain read-only per temporal doctrine. |

**Uniqueness:** `(tenant_id, entity_kind, identity_key_fingerprint)` is **unique** — second insert with same triple is an upsert / noop refresh, not a silent second handle.

---

## 3) Determinism (**G-P04-ORG-01**)

For fixed `tenant_id`, `entity_kind`, and **identity material** dict (canonical JSON), **`org_entity_id` MUST be stable** across processes and time:

- `identity_key_fingerprint = sha256(json.dumps(material, sort_keys=True, separators=(',', ':')))`
- `org_entity_id = uuid.uuid5(PHASE04_ORG_ENTITY_NAMESPACE, f"{tenant_id}:{entity_kind}:{identity_key_fingerprint}")`

Verification gate **G-P04-ORG-01** exercises this contract (static harness in canonical verification until org verification runner exists).

---

## 4) Relationship to Phase 03 anchors

- **Canonical identity anchors** remain **bundle-scoped** provider identity projection.
- **Org entities** may later **link** to anchors via the **link ledger** (P04-04+); P04-03 does **not** auto-create org entities from anchors (optional backfill is **P04-20**).

---

## 5) Admin (read-only, sparse)

- **List:** `GET /admin/tenants/{tenant_id}/cortex/identity/entities`
- **Detail:** `GET /admin/tenants/{tenant_id}/cortex/identity/entities/{org_entity_id}`

No mutating routes in P04-03.

---

## References

- `phase-04-implementation-plan.md` — P04-03  
- `phase-04-normative-index.md`  
