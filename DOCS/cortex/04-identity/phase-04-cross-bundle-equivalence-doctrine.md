# Phase 04 — Cross-Bundle Equivalence Doctrine

**Status:** normative — **P04-09**.  
**Audience:** implementers, verification authors, operators.  
**Runtime:** `vector.domains.cortex.identity.bundle_equivalence` (logical **`identity.bundle_equivalence`** from the implementation plan).  
**Persistence:** `cortex_bundle_equivalence_declarations` — explicit tenant-scoped **equivalence** between two **distinct** mapping bundle pins.  
**Companion:** `phase-04-link-ledger-doctrine.md`, `vector.domains.cortex.continuity.bundle_continuity_semantics`.

---

## 1) Purpose

Canonical materializations and logical keys are **bundle-scoped** (Phase 03). Org-meaning links that intentionally join **two different bundle universes** on canonical endpoints must not rely on implicit equality: they require a **durable equivalence declaration** plus optional **raw evidence** audit. Absent declaration → verification treats declared cross-bundle edges as **violations** (**G-P04-03**).

---

## 2) Declaration shape

- **Tenant-scoped** row: `(tenant_id, left_bundle_id, right_bundle_id)` with **`left_bundle_id` < `right_bundle_id`** lexicographically (**CHECK** `ck_cortex_bundle_eq_pair_ordered`) so the pair has a **canonical key**.  
- **Foreign keys** to `cortex_mapping_bundles.bundle_id` for both bundle columns.  
- **`replay_ordinal`**: append-only **monotonic integer per tenant**, assigned on insert so replay/rebuild jobs have a **declared ordering** surface (**G-P04-14**).  
- **`revoked_at`**: soft-invalidates a declaration; a new active row may be inserted after revocation.  
- **Unique active pair:** partial unique index on `(tenant_id, left_bundle_id, right_bundle_id)` where **`revoked_at IS NULL`**.

---

## 3) Link metadata contract (cross-bundle edge)

Authoritative org links may carry **`metadata_json.cross_bundle_canonical`**:

```json
{
  "cross_bundle_canonical": {
    "source_bundle_id": "<bundle A>",
    "target_bundle_id": "<bundle B>"
  }
}
```

When both ids are **non-empty strings** and **distinct**, verification **G-P04-03** requires an **active** (non-revoked) equivalence declaration for the **normalized ordered pair** of those bundle ids.

---

## 4) Admin

- **`GET /admin/tenants/{tenant_id}/cortex/identity/bundle-equivalence`** — list declarations (optional `include_revoked`).  
- **`POST /admin/tenants/{tenant_id}/cortex/identity/bundle-equivalence`** — append declaration (operator escape hatch; validates bundle registry membership).

---

## 5) Verification

- **G-P04-BNDL-01** — Static bundle-pair normalization contract + persisted integrity (no duplicate `replay_ordinal` per tenant, declarations respect FK + ordered pair invariant).  
- **G-P04-03** — No authoritative org link with **`cross_bundle_canonical`** pointing at two different bundles without an active equivalence declaration for that pair.  
- **G-P04-14** — Replay ordering: `replay_ordinal` strictly increases along `(created_at, id)` for non-revoked rows per tenant (detects manual corruption or bypass of append path).

---

## References

- `phase-04-implementation-plan.md` — Stage P04-09, §12.1 **G-P04-BNDL-01**, **G-P04-03**, **G-P04-14**  
- `phase-04-normative-index.md`
