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

**Next wave (S1):** authoritative link dedupe + idempotent promotion (`dup_factor ≤ 1.05`).

---

## Do not use for routine ops

- `backend/scripts/prod_substrate_proof_queries.py` (deprecated; use continuity + graph truth snapshots)
- `backend/scripts/archive/unlock/*` (recovery only)
- Per-step `continuity_p0_phase_*_proof.py` (CI gates only, not daily ops)
