# Phase 08 — Synthesis runtime architecture

**Status:** normative.  
**Code target:** `vector.domains.cortex.synthesis` (not yet implemented).  
**Integration anchor:** extends `vector.domains.cortex.substrate_pipeline` with `phase_08_synthesis`.

---

## 1) Layered architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  Admin / Control plane (Phase 08 slice + Phase 10 shell)        │
├─────────────────────────────────────────────────────────────────┤
│  synthesis_control_plane · debuggers · eval · certification     │
├─────────────────────────────────────────────────────────────────┤
│  Job API · publication · tenant verification · observability      │
├─────────────────────────────────────────────────────────────────┤
│  execute_synthesis_job_envelope_v1  (FSM)                         │
│    INGRESS → PLAN → RETRIEVE → BIND → ASSEMBLE → LLM → CLASSIFY   │
│    → RECEIPT → PUBLISH                                            │
├─────────────────────────────────────────────────────────────────┤
│  retrieval_client (Phase 07 only) · legality · replay · caps      │
├─────────────────────────────────────────────────────────────────┤
│  llm_adapters (isolated) · prompt_registry · structured output   │
├─────────────────────────────────────────────────────────────────┤
│  Persistence: jobs · artifacts · receipts · publication epochs    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2) Package layout (implementation target)

| Module | Responsibility |
| ------ | -------------- |
| `normative.py` | Program freeze version, public catalogs |
| `anti_goals.py` | G-P08-ANTI-*, forbidden keys |
| `synthesis_job_contract.py` | Workloads, intents, envelope validation |
| `synthesis_legality_matrix.py` | S-LEG aggregation, fail-closed |
| `synthesis_replay_equivalence.py` | Replay identity, twin diff |
| `synthesis_bounded_caps.py` | SD-* registry, cap enforcement |
| `synthesis_ingress.py` | Retrieval response validation |
| `synthesis_query_plan.py` | Deterministic retrieval fan-out plan |
| `synthesis_evidence_binding.py` | Citations, cite-or-omit |
| `synthesis_orchestrator.py` | FSM implementation |
| `synthesis_artifact_materialization.py` | Persist artifacts + digests |
| `synthesis_publication.py` | Epoch publish barrier |
| `synthesis_pipeline_integration.py` | Substrate phase runner |
| `synthesis_observability.py` | Metrics, health, lag |
| `synthesis_control_plane.py` | Admin aggregates |
| `synthesis_truth_validation.py` | Tenant truth probes |
| `synthesis_certification_pack.py` | SYNTHESIS-CERT-PACK-1 |
| `adapters/llm/` | Vendor SDK isolation |

---

## 3) Orchestrator (§Orchestrator)

### FSM phases (closed set)

| Phase | Deterministic? | Description |
| ----- | -------------- | ----------- |
| `INGRESS` | Yes | Validate envelope; anti-goals; policy pack load |
| `PLAN` | Yes | Build retrieval sub-query list from workload profile |
| `RETRIEVE` | Yes | Execute Phase **07** queries sequentially (bounded parallelism optional within cap) |
| `BIND` | Yes | Merge hits; propagate RD→SD; build evidence scope summary |
| `ASSEMBLE` | Yes | Build claim slots + citation placeholders |
| `LLM` | Mixed | Structured completion per policy; temperature pinned |
| `CLASSIFY` | Yes | Legality aggregation; degradation rollup |
| `RECEIPT` | Yes | `synthesis_job_receipt`, replay identity |
| `PUBLISH` | Yes | Bump `synthesis_publication_epoch` if barrier passes |

**Rule:** `RETRIEVE` MUST NOT be skipped — even if job carries pre-fetched retrieval receipt bytes, they MUST be verified against pinned replay identity.

### Retrieval fan-out

`build_synthesis_retrieval_plan_v1(job)` returns ordered list of `RetrievalQueryEnvelopeV1` dicts:

- Primary query from job `retrieval_scope`
- Secondary queries only from **policy pack** `retrieval_fanout_rules` (e.g. lineage_explorer for continuity workloads)
- Max sub-queries: `max_retrieval_subqueries` (default 8)

---

## 4) Bindings (§Bindings)

| Binding | Source fields on artifact |
| ------- | ------------------------- |
| Retrieval | `retrieval_query_replay_identity`, receipt digest, hit digests[] |
| TCRE | Copied from hit `provenance` / `tcre_binding_envelope` |
| OCTS | `traversal_binding_envelope` |
| Graph | `graph_binding_envelope` |
| Continuity | `continuity_context` on hits (Phase **07** reconstruction path) |

Bindings are **copied**, not re-derived.

---

## 5) Lineage (§Lineage)

On artifact persist:

1. Terminal node: `synthesis_artifact` / `artifact_id`
2. Edge: `synthesis_derived_from` → `retrieval_query_receipt`
3. Edge: `synthesis_indexes` → `retrieval_index` lookup id
4. Optional: `synthesis_uses` → `tcre_chain` / `octs_walk` from hit refs

`lineage_chain_digest` on artifact MUST match `build_artifact_lineage_chain_v1` for certification.

---

## 6) Completeness (§Completeness)

`project_synthesis_completeness_v1` feeds substrate overview stage **`synthesis`**:

| Metric | Definition |
| ------ | ---------- |
| `eligible_scopes` | Index rows × default workloads in policy pack |
| `synthesized_scopes` | Artifacts with matching `retrieval_lookup_id` + workload |
| `coverage_percent` | synthesized / eligible |
| `lag_epochs` | `published_index_epoch` − artifact `synthesis_publication_epoch` |

Propagation: upstream `RD-*` / retrieval legality floors synthesis legality via matrix (**S-LEG-UPSTREAM**).

---

## 7) Observability (§Observability)

| Metric | Type |
| ------ | ---- |
| `synthesis_jobs_total` | counter by workload, legality |
| `synthesis_job_duration_ms` | histogram |
| `synthesis_llm_tokens` | counter by model_route |
| `synthesis_sd_codes` | counter by SD-* |
| `synthesis_publication_lag_epochs` | gauge |

Health states: `healthy`, `degraded`, `critical`, `unresolved`, `replay_conflicted` (mirrors retrieval posture vocabulary).

---

## 8) Persistence (cross-ref)

See [`phase-08-data-contracts.md`](./phase-08-data-contracts.md) §Persistence:

- `cortex_synthesis_jobs`
- `cortex_synthesis_artifacts`
- `cortex_synthesis_job_receipts`
- `cortex_synthesis_publication_epochs`
- `cortex_synthesis_audit_log` (append-only)

All tables tenant-scoped; artifacts content-addressed by `artifact_digest`.

---

## 9) Async execution model

| Path | When |
| ---- | ---- |
| **Pipeline Celery** | Default: after phase **07** publish in same `substrate_pipeline_run_id` |
| **Manual admin job** | Operator trigger with scope + pins |
| **Replay twin** | Synchronous in verification harness only |

Worker queue: `vector` (same as substrate pipeline). Task id pattern: `cortex-synthesis-{tenant_id}-{pipeline_run_id}`.

**No** giant synchronous transaction spanning retrieval + LLM + publish — commit after `RETRIEVE`, after `LLM`, after `PUBLISH`.

---

## 10) Failure isolation

| Failure | Behavior |
| ------- | -------- |
| Retrieval fail-closed | Job aborts `INGRESS`/`RETRIEVE`; no LLM call |
| LLM timeout | `SD-LLM-TIMEOUT`; partial artifact forbidden — receipt only |
| LLM schema invalid | `SD-LLM-SCHEMA`; retry once per policy then fail |
| Publish barrier fail | Artifact stored `unpublished`; operator visibility |
