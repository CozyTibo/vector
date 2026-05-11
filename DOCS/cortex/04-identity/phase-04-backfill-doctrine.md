# Phase 04 — Identity Anchor → Org Handle Backfill Doctrine

**Status:** normative — **P04-20**.  
**Audience:** implementers, verification authors, operators.  
**Runtime:** `vector.domains.cortex.identity.backfill`, table **`cortex_org_identity_backfill_runs`**.

---

## 1) Purpose

Materialize **read-only organizational handles** (`cortex_org_entities`) from Phase 03 **`cortex_canonical_identity_anchors`** so operators have a Phase 04 surface **without** silently claiming semantic merges.

Backfill is **candidate / hint lane only**: it MUST NOT create authoritative org links, MUST NOT promote link candidates, and MUST NOT append org merges.

---

## 2) Lane contract

| Constant | Meaning |
| -------- | ------- |
| **`anchor_backfill_lane`** | Literal **`canonical_identity_anchor_v1`** stored on upserted org entity `metadata_json`. |

Identity material for deterministic org entity ids is derived only from `(lane, canonical_entity_id, provider_identity_hash)` so replays are stable.

---

## 3) Gate **G-P04-BF-01**

For each org entity row whose `metadata_json.anchor_backfill_lane == canonical_identity_anchor_v1`, there MUST be **zero** non-revoked **`cortex_org_links`** rows with `link_authority = authoritative` where either endpoint equals that org entity id.

Violations indicate the backfill lane was incorrectly wired into authoritative linkage (forbidden).

---

## 4) Operator surfaces

- **Run (sync):** `POST /admin/tenants/{tenant_id}/cortex/identity/backfill/from-canonical-anchors` — bounded scan + upsert; persists optional **`cortex_org_identity_backfill_runs`** audit row.
- **List runs:** `GET /admin/tenants/{tenant_id}/cortex/identity/backfill/runs` — recent backfill attempts.

---

## 5) References

- `phase-04-org-entity-and-handle-doctrine.md` §4 (anchor relationship)  
- `phase-04-implementation-plan.md` — Stage P04-20  
- `phase-04-mock-data-strategy.md` — hostile continuity fixtures (co-requisite)
