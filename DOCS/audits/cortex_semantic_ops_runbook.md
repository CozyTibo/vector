# Cortex semantic ops runbook (Wave S0+)

**Audience:** Engineers operating Fizzer / prod Cortex  
**Baseline:** [`baselines/graph_truth_fizzer_wave_s0_baseline.json`](baselines/graph_truth_fizzer_wave_s0_baseline.json)  
**Plan:** [`cortex_semantic_execution_intelligence_phase_plan.md`](cortex_semantic_execution_intelligence_phase_plan.md)

---

## What to care about (two tracks)

| Track | Question | Tools |
|-------|----------|-------|
| **Runtime continuity** | Is the worker moving slices? | `continuity_audit_snapshot.py`, continuity admin tab |
| **Semantic readiness** | Is retrieval/synthesis becoming **useful**? | `graph_truth_audit_snapshot.py`, **Semantic readiness** admin card |

Do not conflate them. A moving FSM with 10k duplicate link rows is **not** semantic progress.

---

## Non-negotiable constraints (implementation review)

1. **Retrieval is the product substrate** — graph exists to scope and link identity for retrieval, not as the product.
2. **No new `link_type`** without prod evidence, expected edge count, retrieval use-case, and synthesis use-case (written in PR).
3. **Delete before add** — fewer panels, fewer counters, fewer proof scripts in operator paths.
4. **Graph progress = `unique_auth_pairs`**, not `COUNT(*)` from `cortex_org_links`.
5. **Synthesis stays fail-loud** — empty claims are worse than FAILED.

---

## Operator commands (only these two for truth baselines)

From repo root, with prod DB credentials in `.env` (`DB_PROD_*` or `DATABASE_URL`):

```bash
# Semantic / graph truth / retrieval mix / synthesis claims
cd backend
python scripts/graph_truth_audit_snapshot.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f \
  --json

# Runtime continuity (lease, phases, AA panel) — separate track
python scripts/continuity_audit_snapshot.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f \
  --json
```

Optional write to file:

```bash
python scripts/graph_truth_audit_snapshot.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f \
  --json \
  --out ../DOCS/audits/baselines/graph_truth_snapshot_latest.json
```

---

## Admin UI (deployed app)

| Surface | Path | Primary metrics |
|---------|------|-----------------|
| **Semantic readiness** | Cortex → Overview (top card) | unique pairs, dup factor, promotion rules, retrieval org_link %, synthesis claims |
| **Graph phase** | Cortex → Graph | Same graph truth metrics; row count labeled diagnostic |
| **API** | `GET …/cortex/pipeline/semantic-readiness` | JSON for scripts/dashboards |

**Deprecated as primary KPIs:** raw authoritative link rows, raw candidate totals, phase 04 `edge_count` without dup factor.

---

## Wave S0 sign-off SQL (Fizzer)

```sql
\set tenant 'c08ef32b-f89a-40f6-9566-e19b5329436f'

SELECT
  COUNT(*) AS auth_edge_rows,
  COUNT(DISTINCT (source_entity_id, target_entity_id)) AS unique_auth_pairs,
  ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT (source_entity_id, target_entity_id)), 0), 2) AS dup_factor
FROM cortex_org_links
WHERE tenant_id = :'tenant' AND link_authority = 'authoritative' AND revoked_at IS NULL;

SELECT rule_id, COUNT(DISTINCT (source_entity_id, target_entity_id)) AS unique_pairs, COUNT(*) AS rows
FROM cortex_org_links
WHERE tenant_id = :'tenant' AND link_authority = 'authoritative' AND revoked_at IS NULL
GROUP BY 1 ORDER BY unique_pairs DESC;
```

Compare results to baseline JSON before/after each wave.

---

## What Wave S0 shipped (code)

| Step | Deliverable |
|------|-------------|
| S0.1 | `semantic_readiness_v1.py`, `graph_truth_audit_snapshot.py` |
| S0.2 | Admin semantic readiness card + API + graph page truth metrics |
| S0.3 | This runbook + [`graph_truth_fizzer_wave_s0_baseline.json`](baselines/graph_truth_fizzer_wave_s0_baseline.json) |

## Wave S1 — Graph dedupe & idempotent promotion (COMPLETE)

| Step | Deliverable |
|------|-------------|
| S1.1 | Partial unique index `uq_cortex_org_links_auth_active_endpoints` + idempotent `append_authoritative_org_link` |
| S1.2 | `scripts/revoke_duplicate_authoritative_links.py` (`--dry-run` default, `--apply` + `--out`) |
| S1.3 | Phase 04 receipt: `unique_auth_pairs`, `unique_pairs_delta`, `dup_factor` |
| S1.4 | Promotion schedules on **promotable** pairs only; receipts include `unique_pairs_delta` |

**Migrate (revokes dupes + index):** `alembic upgrade head` (revision `20260523_0092`).

**Operator dedupe (tenant-scoped, receipted):**

```bash
cd backend
python scripts/revoke_duplicate_authoritative_links.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f

python scripts/revoke_duplicate_authoritative_links.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f \
  --apply \
  --out ../DOCS/audits/baselines/graph_truth_fizzer_wave_s1_dedupe_receipt.json
```

Re-run graph truth snapshot and compare `dup_factor` to S0 baseline (target **≤ 1.05**).

## Wave S2 — Identity continuity (COMPLETE)

| Step | Deliverable |
|------|-------------|
| S2.1 | Fair promotion scheduling across GitHub/Slack/Notion/Linear/email rules |
| S2.2 | Per-rule candidate caps + distinct endpoint-pair dedupe |
| S2.3 | Anchor→entity boundary repair on phase 03 backfill |
| S2.4 | Second `link_type` **deferred** (no prod evidence ≥100 edges); baseline + audit script |

**Operator audit:**

```bash
cd backend
python scripts/identity_continuity_audit_snapshot.py \
  --tenant c08ef32b-f89a-40f6-9566-e19b5329436f \
  --json
```

**Sign-off targets:** `promotion_rule_count ≥ 3`, `candidate_inflation_ratio < 3`, `anchors_missing_org_entity_pct` cut ≥50% from S0/S1 measurement.

Baseline template: [`baselines/identity_continuity_fizzer_wave_s2_baseline.json`](baselines/identity_continuity_fizzer_wave_s2_baseline.json)

---

## Do not use for routine ops

- `backend/scripts/prod_substrate_proof_queries.py` (deprecated; use continuity + graph truth snapshots)
- `backend/scripts/archive/unlock/*` (recovery only)
- Per-step `continuity_p0_phase_*_proof.py` (CI gates only, not daily ops)
