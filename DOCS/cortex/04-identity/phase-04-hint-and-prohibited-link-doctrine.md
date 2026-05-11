# Phase 04 — Hint, Inferred & Prohibited Link Classes Doctrine

**Status:** normative — **P04-07**.  
**Audience:** implementers, verification authors, operators.  
**Runtime:** `vector.domains.cortex.identity.link_classes`, column **`cortex_org_links.link_class`** (with existing **`link_authority`** for candidate vs promoted truth rows).  
**Companion:** `phase-04-link-ledger-doctrine.md`, `phase-04-merge-governance-doctrine.md`.

---

## 1) Purpose

Org-meaning links are not only **authoritative** claims. Operators and engines also record **hints**, **inferred** soft edges, and **prohibited** classes so that **“maybe” never silently becomes “is”** and merge / replay logic never treats non-truth rows as authoritative closure material (**G-P04-02**, **G-P04-HINT-01**).

---

## 2) `link_class` discriminant (v1)

| Value | Meaning |
| ----- | ------- |
| **`authoritative`** | Truth-plane org-meaning link (subject to candidate vs **`link_authority`** promotion rules in P04-05). |
| **`hint`** | Non-truth, operator- or engine-originated suggestion; **excluded from merge closure**. |
| **`inferred`** | Non-truth, model-derived soft edge; **excluded from merge closure**. |
| **`prohibited`** | Explicit “must not merge / must not treat as true” marker; **excluded from merge closure**. |

**Authority layer:** rows with `link_class` ∈ {`hint`, `inferred`, `prohibited`} **must** use **`link_authority = 'non_authoritative'`** so they never share the authoritative authority plane with promoted links (**G-P04-HINT-01**, enforced by CHECK + runtime).

---

## 3) Persistence & replay

- Hints are **first-class rows** in **`cortex_org_links`** (same evidence-or-rule bar as authoritative rows — **G-P04-06**).
- Regeneration / replay may rebuild hint rows with explicit `link_class` + `link_authority` pairing; authoritative replay hashes remain scoped to **authoritative-class + authoritative-authority** edges only (see `link_ledger.compute_authoritative_link_set_sha256`).

---

## 4) Merge closure

**Merge closure material** (future merge graph steps) may only include links for which:

- `link_class == 'authoritative'`, and  
- `link_authority == 'authoritative'`, and  
- `revoked_at IS NULL`

Helper: `link_classes.row_eligible_for_merge_closure_material`.

---

## 5) Verification

- **G-P04-02** — Static: merge-closure whitelist is exactly authoritative-class authoritative-authority material (frozen set export).
- **G-P04-HINT-01** — Persisted: no tenant rows pair `link_class` ∈ {hint, inferred, prohibited} with `link_authority` ≠ `non_authoritative` (DB scan; aligned with CHECK).

---

## 6) Admin (read-only)

- **Hint bucket:** `GET /admin/tenants/{tenant_id}/cortex/identity/links/hints` — lists non-truth classes (bounded).
- **Filtered list:** `GET .../cortex/identity/links?link_class=` optional filter on the main list.

---

## References

- `phase-04-implementation-plan.md` — Stage P04-07, §12.1 **G-P04-02**, **G-P04-HINT-01**  
- `phase-04-normative-index.md`
