# Phase 04 — Merge Governance Doctrine

**Status:** normative — **P04-06**.  
**Audience:** implementers, verification authors, operators.  
**Runtime:** `vector.domains.cortex.identity.merge_governance`, tables **`cortex_org_merge_policies`**, **`cortex_org_merges`**.  
**Companion:** `phase-04-architecture-identity-linking-doctrine.md`, `phase-04-org-entity-and-handle-doctrine.md`, `phase-04-link-ledger-doctrine.md`.

---

## 1) Purpose

**Merge governance** defines how organizational continuity records **human / team / service** merges and **rollbacks** as an **append-only ledger**. Wrong merges are irreversible at the human level; the system therefore requires **auditable policy rows**, **evidence**, and **operator attribution** where the doctrine demands it, and forbids **silent deletion** of merge history (**G-P04-13**).

---

## 2) Ledger model (v1)

### 2.1 Merge policy (`cortex_org_merge_policies`)

| Field | Meaning |
| ----- | ------- |
| **`id`** | UUID primary key. |
| **`tenant_id`** | Tenant scope. |
| **`policy_ref`** | Stable string reference for operator defaults / certification. |
| **`engine_build_ref`** | Writer stamp. |
| **`created_at`** | Creation time. |

Policies are **created before** merges that reference them; merges always carry **`merge_policy_id`**.

### 2.2 Merge record (`cortex_org_merges`)

| Field | Meaning |
| ----- | ------- |
| **`id`** | UUID primary key (the **merge_record** for **G-P04-01**). |
| **`tenant_id`** | Tenant scope. |
| **`merge_kind`** | `human_actor_merge` \| `team_merge` \| `service_split` \| `compensating_merge`. |
| **`merge_policy_id`** | FK to **`cortex_org_merge_policies`** (required for every row — operator/policy record). |
| **`source_entity_ids`** | JSON array of org-entity UUIDs involved on the “from” side (length rules depend on **`merge_kind`**). |
| **`target_entity_id`** | Org entity UUID that is the merge outcome anchor (survivor / declared target). |
| **`evidence_raw_record_ids`** | JSON array of `raw_ingestion_records.id` integers backing the merge. |
| **`operator_user_id`** | Nullable for automated kinds; **required** for **`human_actor_merge`** (**G-P04-MRG-01**). |
| **`supersedes_merge_id`** | Self-FK: required for **`compensating_merge`** — rollback / correction is modeled as a **new** row, never by deleting prior rows (**G-P04-13**). |
| **`metadata_json`** | Bounded hints; **`evidence_basis: "email_only"`** is **rejected** at write time for human merges (negative test / operator guardrail). |
| **`engine_build_ref`** | Writer stamp. |
| **`created_at`** | Append time. |

**Append-only:** application code **must not** `DELETE` from **`cortex_org_merges`**. Corrections use **`compensating_merge`** rows.

---

## 3) Kind-specific rules (v1)

| `merge_kind` | Evidence / operator | DB / runtime |
| ------------- | -------------------- | ------------ |
| **`human_actor_merge`** | At least **two distinct** raw evidence ids; at least **two** source org entities; **`operator_user_id`** set; not **`email_only`** metadata. | CHECK + runtime |
| **`team_merge`** | At least one raw evidence id. | Runtime |
| **`service_split`** | At least one raw evidence id. | Runtime |
| **`compensating_merge`** | **`supersedes_merge_id`** required; superseded row same tenant. | CHECK + runtime |

---

## 4) Verification

- **G-P04-MRG-01** — Static contract: human merge policy constants (two-persona evidence floor) are exported and self-consistent.
- **G-P04-01** — Persisted **`human_actor_merge`** rows satisfy policy + dual evidence + operator (DB scan; aligned with CHECK).
- **G-P04-13** — Compensating merges reference an existing prior merge in the same tenant; documents append-only rollback path (DB scan + static companion).

---

## 5) Admin (minimal, P04-06)

- **List:** `GET /admin/tenants/{tenant_id}/cortex/identity/merges`
- **Append:** `POST /admin/tenants/{tenant_id}/cortex/identity/merges` — durable merge_record insert (approval workflow is expanded in later control-plane steps).

---

## References

- `phase-04-implementation-plan.md` — Stage P04-06, §12.1 **G-P04-01**, **G-P04-MRG-01**, **G-P04-13**  
- `phase-04-normative-index.md`
