# Phase 04 — Continuity Replay & Regeneration Doctrine

**Status:** normative — **P04-10**.  
**Audience:** implementers, verification authors, operators.  
**Runtime:** `vector.domains.cortex.identity.org_link_replay_runtime` (logical **`identity.replay_jobs`** surface from the implementation plan).  
**Persistence:** **`cortex_org_link_replay_jobs`** + **`cortex_org_link_replay_job_receipts`** — durable org-link continuity jobs with **L-class** receipts (link drift / parity), mirroring the **receipt discipline** of Phase 03 canonical replay (C0–C5) at a **link-layer** abstraction.  
**Companion:** `phase-04-candidate-vs-authoritative-linkage-doctrine.md`, `phase-04-link-ledger-doctrine.md`, `phase-03-replay-versioning-doctrine.md` (pattern only).

---

## 1) Purpose

**Authoritative replay** and **candidate regeneration** are distinct lanes (Step 5). Operators need **durable job rows + receipts** to prove what ran, with **deterministic hashes** for candidate material (**G-P04-RPL-01** overlaps the regen hash contract) and **snapshot hashes** for authoritative link sets. Jobs are **tenant-scoped**, **append-only** (status transitions only), and **never** delete historical rows.

---

## 2) Job kinds

| `job_kind` | Meaning |
| ---------- | ------- |
| **`authoritative_replay`** | Compute and record **authoritative link set SHA-256** (`link_ledger.compute_authoritative_link_set_sha256`); optional **`dry_run`** skips side effects beyond ledger reads. |
| **`candidate_regen`** | Run **`regenerate_link_candidates`** with a pinned **`pinned_rule_version`** (required when `dry_run=false`); persists batch + emits summary hash. |

---

## 3) Receipts (L-class)

Receipt rows use **`receipt_class`** in **`L0`–`L7`** (reserved taxonomy for link drift; **L0** = “parity / snapshot recorded” in v1). Receipts carry **`detail_json`** only (no raw-record FK — org continuity is not raw-indexed like canonical replay).

---

## 4) Admin (minimal)

- **`POST /admin/tenants/{tenant_id}/cortex/identity/replay-jobs/run`** — create + execute one job (synchronous operator path).  
- **`GET .../cortex/identity/replay-jobs`** — recent jobs.  
- **`GET .../cortex/identity/replay-jobs/{job_id}`** — job + ordered receipts.

Celery: **`vector.cortex.identity.run_org_link_replay_job`** — async wrapper with the same execute path.

---

## 5) Verification

- **G-P04-RPL-01** — Static: deterministic **candidate set hash** invariants (order independence) + **L-class** envelope allowlist; Persisted: **`completed`** org-link replay jobs must have **≥ 1** receipt row (receipt discipline).

---

## References

- `phase-04-implementation-plan.md` — Stage P04-10, §12.1 **G-P04-RPL-01**  
- `phase-04-normative-index.md`
