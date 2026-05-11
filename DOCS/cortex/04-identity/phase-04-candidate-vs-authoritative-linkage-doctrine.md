# Phase 04 — Candidate vs Authoritative Linkage Doctrine

**Status:** normative — **P04-05**.  
**Audience:** implementers, verification authors.  
**Runtime:** `vector.domains.cortex.identity.candidate_generation`, `vector.domains.cortex.identity.authoritative_writer`.  
**Persistence:** `cortex_org_link_candidate_batches`, `cortex_org_link_candidates`, `cortex_org_link_promotion_policies`; authoritative rows remain in **`cortex_org_links`**.

---

## 1) Two-layer model

| Layer | Meaning | Source of truth |
| ----- | ------- | ---------------- |
| **Candidate** | Recomputable suggestion from rules + evidence snapshots | **`cortex_org_link_candidates`** (grouped by **`candidate_batch_id`**) + batch **`candidate_set_sha256`** |
| **Authoritative** | Durable org meaning edge | **`cortex_org_links`** with `link_authority='authoritative'` |

Candidates **never** imply merge closure or authoritative graph export. Promotion to authoritative is an **auditable write** requiring a **promotion policy** row (**G-P04-CAND-01**).

---

## 2) Promotion (**G-P04-CAND-01**)

When an authoritative link records `promoted_from_candidate_id`, **`promotion_policy_id` MUST be non-null** and MUST reference a `cortex_org_link_promotion_policies` row for the **same tenant**. The database enforces the pairing via `CHECK` + foreign keys.

---

## 3) Regeneration hash (**G-P04-04**)

For a frozen **`rule_version`** and frozen candidate material list, **`candidate_set_sha256`** (SHA-256 hex of canonical JSON of sorted row projections) MUST be stable across processes.

---

## 4) Authoritative replay hash (**G-P04-05**)

The set of authoritative links for a tenant, projected to a canonical sorted JSON array (stable field order, sorted evidence ids), MUST yield a stable **`authoritative_set_sha256`** for a given ledger state — replays that reproduce the same ledger rows MUST reproduce the same hash.

---

## 5) Jobs (Celery)

- **`vector.cortex.identity.regenerate_link_candidates`** — enqueue / run candidate regeneration for a tenant + `rule_version` (stub derives minimal candidates from org entities when present).
- **`vector.cortex.identity.replay_authoritative_links`** — compute `{authoritative_set_sha256, link_count}` for operator receipts.

---

## 6) Admin (sparse)

- **Candidate queue:** `GET /admin/tenants/{tenant_id}/cortex/identity/link-candidates` (recent batches + rows, bounded).

---

## References

- `phase-04-implementation-plan.md` — Stage P04-05  
- `phase-04-link-ledger-doctrine.md`
