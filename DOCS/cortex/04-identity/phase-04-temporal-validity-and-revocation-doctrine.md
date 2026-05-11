# Phase 04 — Temporal Validity & Revocation Doctrine

**Status:** normative — **P04-08**.  
**Audience:** implementers, verification authors, operators.  
**Runtime:** `vector.domains.cortex.identity.org_link_temporal` (logical **`identity.temporal`** surface from the implementation plan), fields on **`cortex_org_links`**: **`valid_from`**, **`valid_to`**, **`revoked_at`**, **`supersedes_link_id`**.  
**Companion:** `phase-04-link-ledger-doctrine.md`, `phase-04-hint-and-prohibited-link-doctrine.md`.

---

## 1) Purpose

Org-meaning links exist in **time**: they may be **open-ended** on one or both bounds, **superseded** by a newer row, or **revoked** without erasing history. Provider account deletion or connector tombstones **must not** remove ledger rows (**G-P04-11**); corrections use **supersession** + **revocation timestamps** only.

---

## 2) Half-open validity

When both **`valid_from`** and **`valid_to`** are set, the active window is **\[`valid_from`, `valid_to`)** — **`valid_from` < `valid_to`** is required (**CHECK** + runtime).  
`NULL` on an axis means **unbounded** on that side (same convention as the link ledger runtime).

---

## 3) Overlap rule (authoritative truth plane)

For **merge-closure-eligible** authoritative links (authoritative **`link_class`** + authoritative **`link_authority`**, **`revoked_at IS NULL`**), two rows with the same **`(tenant_id, link_type, source_entity_id, target_entity_id)`** must **not** have overlapping **\[start, end)** intervals (**G-P04-TMP-01** persisted scan).

---

## 4) Revocation & tombstones

- **`revoked_at`**: instant the link ceases to be active; row **remains** queryable for audit and replay.  
- **`supersedes_link_id`**: optional chain to a replacement row.  
- **G-P04-11** — Normative contract: no **hard `DELETE`** from **`cortex_org_links`** in product/runtime paths; “deleted provider” semantics are modeled via **revocation / supersession / metadata**, not row removal.

---

## 5) Admin (sparse)

- **Timeline strip:** `GET /admin/tenants/{tenant_id}/cortex/identity/links/timeline` — recent rows with temporal columns (optional `include_revoked`).

---

## 6) Verification

- **G-P04-TMP-01** — Half-open axis static self-check **plus** persisted overlap detection for authoritative org links (same edge key, non-revoked, merge-closure material).  
- **G-P04-11** — Static tombstone / soft-revocation contract for the link ledger.

---

## References

- `phase-04-implementation-plan.md` — Stage P04-08, §12.1 **G-P04-TMP-01**, **G-P04-11**  
- `phase-04-normative-index.md`
