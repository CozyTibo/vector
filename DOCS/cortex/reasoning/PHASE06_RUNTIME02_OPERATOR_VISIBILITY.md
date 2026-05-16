# Phase 06 RUNTIME-02 — operator visibility (human-debuggable reconstruction)

**Status:** shipped (bounded); extended by **RUNTIME-03** hardening (OCTS binding, edge expansion, hostile corpus, persisted replay diff).  
**Not claimed:** production-certified, execution intelligence, organizational reasoning, retrieval/synthesis.

## What is operationally visible

After RUNTIME-02, operators can inspect a completed reconstruction job without reading doctrine or raw reducer code:

| Surface | API | Content |
|---------|-----|---------|
| Chronology explanations | `GET .../runtime/jobs/{id}/operator-view` | Per-materialization: timestamps, `replay_safe_ordering`, `chronology_legality_class`, `CHRON-PROJ-*` rule id, template summary, policy digest, retrieval refs |
| Edge explanations | same | Per-edge: source/target mats, kind, `TCRE-EDGE-TEMPORAL-01` label, legality class, template summary |
| Chain timeline | same | Ordered steps: source → edge → target, chronology classes, continuity labels |
| Degradation (“why degraded?”) | same | `CD-CHRON` / edge legality templates with triggering rule + signals |
| Reconstruction summary | same | Counts (strict/degraded, edges by kind), policy pack, engine build, duration |
| Replay structural diff | twin response + `GET .../replay-diff` | Chronology/edge/chain/digest/policy/count mismatches (no fuzzy diff) |
| Extended health | `GET .../runtime/health` | Degraded %, failed jobs, avg duration, last twin result, divergence timestamp |

All explanation text is **template-driven** from lawful rule ids and receipt fields — **no LLM**, no probabilistic inference.

## Layer separation

1. **Doctrine** — frozen under `DOCS/cortex/reasoning/`  
2. **Reducers** — `runtime/*_runtime_reducer.py` (lawful receipts only)  
3. **Persistence** — `cortex_tcre_reconstruction_*` tables (opaque JSON bodies)  
4. **Operator projections** — `runtime/chronology_explanation_projection.py`, `causal_edge_explanation_projection.py`, `chain_timeline_projection.py`, `replay_diff_projection.py`, `degradation_explanation_projection.py`, `operator_views.py`  
5. **UI** — admin Reasoning job detail (collapsible panels, timeline list)

## Retrieval prep (Phase 07)

Operator view emits stable refs only (no retrieval implementation):

- `retrieval_lookup_id` per chronology/edge  
- `chronology_window_ref` per materialization  
- `retrieval_chain_ref` on timeline  
- `retrieval_refs.job_ref` on job aggregate  

## What remains missing

- Full **12 debugger** surfaces from `reasoning-admin-control-plane-spec.md` (only runtime job/health + catalogs today)  
- **OCTS walk** integration on live tenant exhaust  
- **Graph visualization** (explicitly deferred)  
- **Historical trend** / SLO dashboards (health is point-in-time aggregate)  
- **Cross-tenant** operator plane  
- **Production certification** (`reasoning-runtime-legality-matrix.md` deployment predicates still block)  
- Rich **coordination-edge** derivation (runtime still emits temporal-order edges from canonical sort only)  
- **Policy substitution** UI (digest pinned to default pack)  

## Known runtime limitations

- Bounded slice (default 50 materializations); not full-tenant reconstruction  
- Chronology heuristics use `temporal_ordering_key` presence + `observed_at`/`occurred_at` skew only  
- Degraded % on health derives from recent job `summary_json` (empty until jobs run post-RUNTIME-02)  
- Replay diff compares **in-memory double runs**, not persisted artifact byte equality  
- No Celery queue latency metric (only `queue_depth_proxy`)  

## Phase 07 dependencies

Phase 07 retrieval/synthesis may assume:

- Deterministic artifact digests and stable lookup ids from operator projections  
- Replay-safe chronology/edge/chain refs addressable without re-running reducers  
- Proven twin replay on bounded slices (RUNTIME-01) + structural diff visibility (RUNTIME-02)  

Phase 07 must **not** assume: semantic ranking, embeddings, or production-certified TCRE deployment.
