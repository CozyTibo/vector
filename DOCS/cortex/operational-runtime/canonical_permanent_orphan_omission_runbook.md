# Canonical permanent orphan omission runbook (Phase D4)

**Status:** Active operator doctrine  
**Reference tenant (Fizzer):** ~466 `permanent_orphan` deferrals at 2026-05-22 baseline  
**Policy:** Bounded structural debt — **not** a failure to drive `deferral_total → 0`

## What “permanent orphan” means

During canonical forward-progress, rows can be quarantined in the **topology orphan** queue when ingest parents are missing (for example GitHub timeline events without review/commit/workflow parents in raw).

After `CORTEX_CANONICAL_PERMANENT_ORPHAN_DEFERRAL_THRESHOLD` retry cycles (default 5), the deferral is tagged:

```json
{ "permanent_orphan": true }
```

These rows are **intentionally excluded** from drainable routable work. They are **omission-class debt**, not “the system is broken.”

## What operators should optimize (primary)

| Metric | Role |
|--------|------|
| `drainable_routable_estimate` | **Primary KPI** — work the pipeline can actually process |
| `deferred_retry_ready` | Actionable deferrals — should trend down with ingest caps (D2) + graph motion (D3) |
| `deferred_permanent_orphan` | **Bounded omission** — stable band is OK; chasing zero is forbidden |
| `raw_minus_mat_admin_gap` | Diagnostic only — not the hero metric (D1) |

## What “success” looks like

- **Do not** require `deferral_total = 0` for continuity sign-off.
- **Do** require:
  - Drainable backlog moving down autonomously when lease is healthy
  - Retry-ready deferrals not growing without bound week-over-week
  - Permanent orphan count **stable or slowly growing** with documented causes (ingest depth, parent gaps)

## Fizzer reference (2026-05-22)

| Field | Typical value |
|-------|----------------|
| `deferred_total` | ~2.4k+ |
| `deferred_permanent_orphan` | **~466** |
| Share | Often 15–25% of deferrals |

A permanent orphan count near this band after caps/promotion work is **expected**, not fake-green.

## Common permanent-orphan sources

1. **GitHub timeline** events deferred for missing review/commit/workflow parents  
2. **Deep ingest caps** (pre-D2) leaving parent rows never materialized  
3. **Connector ordering** — child arrived before parent in a sync window  

Mitigations (parallel Phase D):

- **D2** — raise GitHub ingest caps to code defaults (10/16/120)  
- **D3** — lawful graph promotion on convergence schedule (auth links)  
- Ingest depth improvements per connector exhaust matrix (longer horizon)

## Anti-patterns (forbidden)

- Marking continuity **PASS** only because `deferral_total` dropped while ignoring drainable truth  
- Treating **466 permanent orphans** as a P0 defect requiring emergency drain scripts  
- Using **raw − materialized** gap as the primary “we are behind” signal  

## Proof / baseline

Prod proof step: `step_d4_permanent_orphan_omission_doctrine`

```bash
cd backend
VECTOR_SETTINGS_SKIP_DOTENV=1 python scripts/continuity_p0_phase_d4_permanent_orphan_omission_proof.py \
  --use-deployed-closure
```

Rollback: set `CORTEX_CANONICAL_PERMANENT_ORPHAN_OMISSION_DOC=0` to hide omission posture banners (legacy “chase zero” copy returns).

## Related docs

- `DOCS/audits/cortex_continuity_stabilization_plan.md` — Phase D table  
- `DOCS/cortex/connectors/connector-exhaust-matrix.md` — ingest depth limits  
- Phase D1 admin KPI — `drainable_routable` + islands, not raw−mat hero  
