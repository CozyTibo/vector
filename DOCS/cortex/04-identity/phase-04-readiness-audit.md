# Phase 04 — Readiness & economics audit (P04-21)

**Status:** normative for Step **21** (stabilization + economics pass).  
**Purpose:** bounded, tenant-scoped **probes** that estimate **storage pressure**, **regeneration / replay work**, and **explosion risk** for the Phase 04 identity substrate—without turning verification into a load test.

## 1) Non-goals

- This document does **not** define merge policy, link semantics, or certification closure (see `phase-04-closure-gates-doctrine.md` for P04-22).
- Probes are **O(1) count / aggregate** queries plus fixed metadata; they must not scan unbounded raw memory or canonical materializations.

## 2) Row-size knobs (audit-grade estimates)

These constants are **order-of-magnitude** byte budgets per persisted row class for **operator-facing storage hints** only—not WAL, index, or TOAST overhead.

| Surface | Bytes / row (nominal) | Notes |
| ------- | --------------------: | ----- |
| `cortex_org_entities` | 480 | handle metadata + JSON columns |
| `cortex_org_links` (authoritative window) | 320 | evidence refs + temporal fields |
| `cortex_org_link_candidates` | 220 | candidate lane only |

**Reported estimate:** `bytes ≈ n_entities * 480 + n_candidates * 220 + n_auth_links * 320` for the counts defined in §3.

## 3) Counted volumes (per tenant)

| Key | Meaning |
| --- | ------- |
| `org_entities_active` | Org entities with `lifecycle_state=active` and not tombstoned |
| `org_links_authoritative_valid_now` | Authoritative links valid at probe `computed_at` (same half-open window as control-plane cards) |
| `org_link_candidates` | All candidate rows |
| `org_link_candidate_batches` | Candidate regeneration batches |
| `open_org_ambiguities` | Open org-ambiguity records (Phase 03 parity counter) |
| `pending_merge_proposals` | Recent merge rows whose metadata marks queue/proposal as `pending` (bounded scan, same cap as control plane) |
| `org_primitive_instances` | Execution primitive instances |
| `org_link_replay_jobs_total` | All replay/regen job rows |
| `org_link_replay_jobs_by_status` | Histogram keyed by `status` |

## 4) Warn / critical thresholds (explosion semantics)

**Warn** = posture `warn` — operator should plan capacity, batching, or cleanup; **does not** fail canonical verification (gate **G-P04-ECO-01** is `warn_only` unless **critical**).

**Critical** = posture `critical` — **G-P04-ECO-01** marks `passed: false` (still `warn_only` severity so overall verification **PASS** is unchanged); operators must treat this as a **hard economics / explosion** signal.

| Metric | Warn | Critical |
| ------ | ---: | -------: |
| `org_entities_active` | ≥ 10_000 | ≥ 50_000 |
| `org_link_candidates` | ≥ 100_000 | ≥ 500_000 |
| `org_links_authoritative_valid_now` | ≥ 25_000 | ≥ 150_000 |
| `open_org_ambiguities` | ≥ 500 | ≥ 5_000 |
| `pending_merge_proposals` | ≥ 200 | ≥ 2_000 |
| `org_primitive_instances` | ≥ 50_000 | ≥ 250_000 |
| `org_link_replay_jobs_total` | ≥ 5_000 | ≥ 50_000 |

Any **critical** breach sets `overall_posture=critical`. If none critical but any warn, `overall_posture=warn`. Else `ok`.

## 5) Regeneration / replay cost hints (bounded)

**Purpose:** give operators a **relative** sense of work for full candidate regen vs authoritative replay, not wall-clock SLAs.

- `candidate_regen_relative_units` ≈ `org_link_candidates + org_link_candidate_batches * 50` (batch header / manifest overhead fudge).
- `authoritative_replay_relative_units` ≈ `org_links_authoritative_valid_now * 2` (ledger scan + receipt fan-out fudge).

These are **dimensionless** integers for UI ordering and trend lines only.

## 6) Runtime contract

- HTTP: `GET /admin/tenants/{tenant_id}/cortex/identity/readiness-economics`
- JSON contract: `identity_readiness_economics_v1` (`identity_readiness_economics_schema_version` in payload).
- Implementation: `vector.domains.cortex.identity.readiness_economics`.

## 7) Database indexes (P04-21)

Composite indexes that align with probe `WHERE tenant_id = ?` and optional ordering/filtering on `created_at` / `status`—see Alembic revision **`20260511_0067`**.
