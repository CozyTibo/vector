# Phase 07 constitutional changelog

## 2026-05-16 — P07-23 retrieval admin control plane catalog (runtime)

**Scope:** Step **23** shipped in `vector.domains.cortex.retrieval.retrieval_control_plane`.

### Added

- Sixteen operator surfaces registry + wiring checklist (**RET-CP-01**).  
- RBAC matrix (`cortex.retrieval.query` / `.read` / `.index_rebuild`).  
- OpenAPI path matrix **G-P07-CP-01** → `DOCS/cortex/retrieval/schemas/generated/retrieval_admin_v1.openapi.json`.  
- `build_retrieval_control_plane_v1` aggregate (workload histogram, health strip, metrics).  
- Admin `GET .../retrieval/control-plane`, `GET .../audit`, `GET .../readiness-economics` (Step 25 placeholder).  
- Frontend control-plane surface checklist page.  
- pytest `test_phase07_step23_control_plane.py` + `test_admin_cortex_retrieval_control_plane.py`.

---

## 2026-05-16 — P07-22 retrieval observability + health model (runtime)

**Scope:** Step **22** shipped in `vector.domains.cortex.retrieval.retrieval_observability`.

### Added

- Integer control-plane metrics + structured query logs (**RET-OBS-01**).  
- ``build_retrieval_runtime_health_v1`` + R-LEG health predicates + policy-pack alerts (**RET-OBS-02/03**).  
- Durable ``cortex_retrieval_query_audit`` (Alembic **20260516_0072**).  
- Query FSM ``record_retrieval_query_observability_v1`` + ``retrieval_query_log`` on results.  
- **G-P07-OBS-01** static gate; admin ``GET .../retrieval/health`` + ``GET .../observability``.  
- Overview admin health strip (frontend).  
- pytest ``test_phase07_step22_observability.py``.

---

## 2026-05-16 — P07-21 artifact lineage retrieval (runtime)

**Scope:** Step **21** shipped in `vector.domains.cortex.retrieval.retrieval_artifact_lineage`.

### Added

- Terminal→root ``build_artifact_lineage_chain_v1`` wrapper with ``max_lineage_hops`` cap (**RET-LINEAGE-01**).  
- ``lineage_chain_digest`` replay pin law + ``RD-LINEAGE-GAP`` for truncation / pin mismatch / edge omissions (**RET-LINEAGE-02**).  
- Query FSM ``apply_retrieval_lineage_binding_to_query_v1``; ``lineage_explorer`` workload expands chain nodes to hits.  
- **G-P07-LINEAGE-01** static gate; golden ``query/lineage_explorer_minimal_v1``.  
- Admin ``GET .../retrieval/lineage-explorer`` catalog + ``GET .../lineage/{kind}/{ref}`` with ``max_lineage_hops``.  
- pytest ``test_phase07_step21_artifact_lineage.py``.

---

## 2026-05-16 — P07-17 graph / identity / canonical bindings (runtime)

**Scope:** Step **17** shipped in `vector.domains.cortex.retrieval.retrieval_graph_binding`.

### Added

- ``CortexOrgEntity`` / ``CortexOrgLink`` durable reads (**RET-GRAPH-01**).  
- ``org_entity_id`` + ``org_link_id`` → ``retrieval_lookup_id`` (**RET-GRAPH-02**).  
- Candidate links → ``evidence_candidate_only``; ``RD-GRAPH-ORPHAN`` for orphans (**RET-GRAPH-03**).  
- Graph scope queries + export sequence pin law for graph-scoped workloads.  
- **G-P07-GRAPH-01** static gate; ``index_graph_ref_for_retrieval_v1``.  
- Admin ``GET .../retrieval/graph-binding``.  
- Golden ``retrieval_golden_vectors/v1/cases/graph/entity_link_addressing_v1``.  
- pytest ``test_phase07_step17_graph_binding.py``.

---

## 2026-05-16 — P07-16 OCTS walk + traversal bindings (runtime)

**Scope:** Step **16** shipped in `vector.domains.cortex.retrieval.retrieval_octs_binding`.

### Added

- Durable walk reads via ``resolve_octs_walk_store_v1`` (**RET-OCTS-01**).  
- ``retrieval_walk_ref`` from ``walk_result_hash`` + ``traversal_epoch`` (**RET-OCTS-02**).  
- Exploration partition isolation + ``RD-TRAVERSAL-IDLE`` / ``RD-TRAVERSAL-BLOCKED`` (**RET-OCTS-03**).  
- Walk scope query kinds: ``walk_by_id``, ``walk_by_hash_and_epoch``, ``tenant_completed_walk_inventory``, ``graph_eligible_idle_probe``.  
- **G-P07-OCTS-01** static gate; ``materialize_retrieval_index_from_walk_v1`` + ``index_walk_for_retrieval_v1``.  
- Admin ``GET .../retrieval/traversal-binding``.  
- Golden ``retrieval_golden_vectors/v1/cases/octs/walk_ref_scope_v1``.  
- pytest ``test_phase07_step16_octs_binding.py``.

---

## 2026-05-16 — P07-15 TCRE / chronology / edge bindings (runtime)

**Scope:** Step **15** shipped in `vector.domains.cortex.retrieval.retrieval_tcre_binding`.

### Added

- Read `cortex_tcre_reconstruction_jobs` + artifacts (**RET-TCRE-01**); no inline reducer.  
- RUNTIME-02 handoff ref → `retrieval_lookup_id` map (**RET-TCRE-02**, **G-P07-TCRE-01**).  
- `RD-TCRE-GAP` coverage gap propagation + `tcre_replay_artifact_pins` on query responses.  
- `materialize_retrieval_index_from_tcre_job_v1` + optional `tcre_reconstruction_job_id` on `index_tcre_chain_for_retrieval_v1`.  
- Admin ``GET .../retrieval/tcre-binding`` (+ optional `job_id` lookup map).  
- Golden ``retrieval_golden_vectors/v1/cases/tcre/binding_lookup_map_v1``.  
- pytest ``test_phase07_step15_tcre_binding.py``.

---

## 2026-05-16 — P07-14 retrieval index materialization (runtime)

**Scope:** Step **14** shipped in `vector.domains.cortex.retrieval.retrieval_index_materialization`.

### Added

- ``cortex_retrieval_index_epochs`` + ``index_epoch`` column on index entries (Alembic **20260516_0071**).  
- Index build FSM **QUEUED → BUILDING → PUBLISHED** + **RET-IDX-01** publish barrier on reads.  
- **G-P07-REPLAY-02** index permutation invariance compare helper.  
- ``index_lag_epochs`` + ``published_index_epoch`` on query responses.  
- Admin ``GET .../retrieval/index`` + ``POST .../retrieval/index/rebuild``.  
- Golden ``retrieval_golden_vectors/v1/cases/index/publish_barrier_v1``.  
- pytest ``test_phase07_step14_index_materialization.py``.

---

## 2026-05-16 — P07-13 bounded caps + omission law (runtime)

**Scope:** Step **13** shipped in `vector.domains.cortex.retrieval.retrieval_bounded_caps`.

### Added

- ``RetrievalPolicyPackV1_Default.json`` fixture (caps + closed ``RD-*`` registry).  
- **RET-DEG-01** closed omission registry + **RET-DEG-02** monotonicity doctrine anchor.  
- Cap ceiling enforcement (no bypass) + 413 ``retrieval_response_too_large`` + 503 ``retrieval_timeout``.  
- ``retrieval_omission_histogram`` + ``substrate_health_state`` observability.  
- **G-P07-DEG-01** static registry gate.  
- Admin ``GET .../retrieval/omission-explorer``.  
- pytest ``test_phase07_step13_bounded_caps.py``.

---

## 2026-05-16 — P07-12 deterministic ranking + selection (runtime)

**Scope:** Step **12** shipped in `vector.domains.cortex.retrieval.retrieval_ranking_selection`.

### Added

- ``RetrievalSelectionPolicyProfileV1_Default`` + ``RetrievalSelectionPolicyProfileV1_LegalityFirst`` profile ids.  
- Integer tuple sort dimensions (**RET-RANK-01**) + forbidden score keys (**RET-RANK-02** / **G-P07-RANK-01**).  
- Post-sort cap truncation → ``RD-CAP-HITS`` / ``RD-CAP-CHRON`` / ``RD-CAP-EDGE`` / ``RD-CAP-LINEAGE``.  
- ``selection_sort_trace`` + ``cap_overflow_totals`` on query responses.  
- Admin ``GET .../retrieval/ranking-selection`` catalog.  
- pytest ``test_phase07_step12_ranking_selection.py``.

---

## 2026-05-16 — P07-11 temporal retrieval model (runtime)

**Scope:** Step **11** shipped in `vector.domains.cortex.retrieval.retrieval_temporal`.

### Added

- Frozen ``temporal_scope_v1`` schema (`t_as_of_unix_ns`, windows, epochs, export/graph pins).  
- **RET-TEMP-01..04** (valid-at-T selection, TCRE pin law, ``omitted_temporal_future``, skew copy-through).  
- Temporal legality envelope floors + ``temporal_skew_audit`` observability.  
- **G-P07-TEMP-01** static schema gate.  
- Admin ``GET .../retrieval/temporal-explorer`` catalog.  
- pytest ``test_phase07_step11_temporal_retrieval.py``.

---

## 2026-05-16 — P07-10 provenance + evidence envelope (runtime)

**Scope:** Step **10** shipped in `vector.domains.cortex.retrieval.retrieval_provenance_evidence`.

### Added

- `RetrievalProvenanceEnvelopeV1` with content-addressed ``provenance_envelope_id``.  
- Evidence legality classes + **RET-PROV-01** missing-digest degraded floor + **RET-PROV-02** omission semantics rows.  
- **G-P07-PROV-01** static field checklist gate.  
- Query FSM PROVENANCE phase builds ``retrieval_evidence_hits`` + ``provenance_coverage_percent``.  
- Admin ``GET .../retrieval/provenance-inspector`` catalog.  
- pytest ``test_phase07_step10_provenance_evidence.py``.

---

## 2026-05-16 — P07-20 substrate completeness + overview (runtime)

**Scope:** Step **20** shipped in `vector.domains.cortex.retrieval.retrieval_completeness_projection`.

### Added

- `project_retrieval_completeness_v1` — 7th substrate pipeline stage in completeness ledger.  
- **RET-COMP-01** eligible vs indexed coverage + never idle-healthy law.  
- Admin `GET .../retrieval/coverage` + `GET .../retrieval/overview` catalogs.  
- Retrieval overview UI coverage strip (eligible / indexed / replay-safe).  
- pytest `test_phase07_step20_substrate_completeness.py`.

---

## 2026-05-16 — P07-19 degradation taxonomy + propagation (runtime)

**Scope:** Step **19** shipped in `vector.domains.cortex.retrieval.retrieval_degradation_taxonomy`.

### Added

- Substrate propagation table + `propagate_upstream_triggers_to_rd_omissions_v1`.  
- **RET-DEG-02** hit/omission multiset monotonicity validators.  
- `retrieval_rd_rollup` + completeness registry validation.  
- Admin `GET .../retrieval/degradation-topology`.  
- pytest `test_phase07_step19_degradation_taxonomy.py`.

---

## 2026-05-16 — P07-18 retrieval replay equivalence proofs harness (runtime)

**Scope:** Step **18** shipped in `vector.domains.cortex.retrieval.retrieval_replay_equivalence_proofs`.

### Added

- Stage **C** harness wiring **G-P07-REPLAY-01/02** + `run_retrieval_gp07_stage_c_replay_gates_v1`.  
- PR-blocking bundle `run_retrieval_gp07_pr_blocking_static_stages_v1` (stages **A+B+C**).  
- Golden `query/replay_equivalence_double_run_v1`; twin failure → `RD-REPLAY-TWIN` + `retrieval_degraded`.  
- Admin replay inspector harness + twin diff field catalog.  
- pytest `test_phase07_step18_replay_equivalence_proofs.py`.

---

## 2026-05-16 — P07-09 retrieval addressing model (runtime)

**Scope:** Step **9** shipped in `vector.domains.cortex.retrieval.retrieval_addressing`.

### Added

- **RET-ADDR-01** resolution order (direct → legacy index → compose canon).  
- `sha256:` + 64-hex ``retrieval_lookup_id`` law; window/chain/walk/lineage ref bodies.  
- Partial addressing assessment + resolve-failure observability counter.  
- Golden corpus **G-P07-ADDR-01** under ``retrieval_golden_vectors/v1/``.  
- Admin ``GET .../retrieval/addressing`` catalog.  
- pytest ``test_phase07_step09_retrieval_addressing.py``.

---

## 2026-05-16 — P07-08 query replay identity + pins (runtime)

**Scope:** Step **8** shipped in `vector.domains.cortex.retrieval.retrieval_replay_equivalence`.

### Added

- Canonical ``retrieval_query_replay_identity`` (envelope + policy digest + hits + omissions).  
- Replay pin law + ``RD-POLICY-MISMATCH`` authoritative mismatch rows.  
- **G-P07-REPLAY-01** double-run compare + ``replay_equivalence`` twin workload.  
- Divergence counter + admin ``GET .../replay-inspector``.  
- pytest ``test_phase07_step08_replay_identity_pins.py``.

---

## 2026-05-16 — P07-07 query legality matrix + degradation floors (runtime)

**Scope:** Step **7** shipped in `vector.domains.cortex.retrieval.retrieval_legality_matrix`.

### Added

- Five query legality classes with ordinals + Phase 08 authority flags.  
- **R‑LEG‑01..07** predicate catalog + failure-class aggregate (`aggregate_query_legality_class_v1`).  
- `assert_retrieval_query_lawful_v1` (audit may return `retrieval_unverifiable`).  
- Degradation class floors in `retrieval_degradation_projection`.  
- Admin legality matrix + `runtime-legality-matrix` + `retrieval_queries_by_legality` histogram.  
- **G‑P07‑LEG‑01** static gate; pytest `test_phase07_step07_query_legality_degradation.py`.

---

## 2026-05-16 — P07-06 lawful query envelope + execution FSM (runtime)

**Scope:** Step **6** shipped in `vector.domains.cortex.retrieval.query_execution`.

### Added

- `RetrievalQueryEnvelopeV1` normalize/coerce (**RET‑QC‑02** addressing resolution).  
- Deterministic FSM **VALIDATE → RESOLVE → BOUND → PROVENANCE → CLASSIFY → RECEIPT** (**RET‑QC‑03**).  
- **R‑LEG‑01..07** pre-check snapshot; `RetrievalQueryReceiptV1` canonical digest.  
- `execute_retrieval_query_envelope_v1` orchestrator; `retrieval_query_engine` delegates.  
- Admin `POST .../retrieval/query` uses envelope FSM; legality GET exposes `query_execution_phases`.  
- Static gates **G‑P07‑QC‑02** / **G‑P07‑QC‑03**.  
- pytest `test_phase07_step06_query_envelope_fsm.py`.

---

## 2026-05-16 — P07-05 query workload classes + intents (runtime)

**Scope:** Step **5** shipped in `vector.domains.cortex.retrieval.query_contract`.

### Added

- **14** closed workload classes + **5** intents (**G‑P07‑QC‑01**).  
- Per-workload default selection caps + intent/workload pairing law.  
- `build_retrieval_query_replay_identity_scope_v1` (workload + intent pins).  
- Admin `GET .../retrieval/query-contract` for debugger forms.  
- JSON schema workload enum aligned with runtime registry.  
- pytest `test_phase07_step05_query_workload_intents.py`.

---

## 2026-05-16 — P07-04 upstream ingress law (runtime)

**Scope:** Step **4** shipped in `vector.domains.cortex.retrieval.retrieval_ingress`.

### Added

- Observed vs derived vs forbidden artifact kind partition (**RET‑ING‑01..04**).  
- `RD-INDEX-STALE` for derived reads without published `index_epoch`.  
- `evidence_candidate_only` for candidate graph links in authoritative partition.  
- Ingress table in query contract doctrine + `build_retrieval_ingress_law_catalog_v1`.  
- Admin `GET .../retrieval/ingress` + provenance inspector field catalog.  
- pytest `test_phase07_step04_upstream_ingress.py`.

---

## 2026-05-16 — P07-03 phase boundaries (06 / 08 / 09)

**Scope:** Step **3** shipped in `vector.domains.cortex.retrieval.phase_boundaries`.

### Added

- **RET‑BND‑06/08/09** validators + **G‑P07‑BND‑*** static gates.  
- `RD-TCRE-GAP` omission propagation from `reconstruction_coverage_gap`.  
- Admin legality GET includes `phase_boundaries` catalog; query POST enforces Phase 06 envelope boundary.  
- Query engine copies upstream legality fields + boundary validation on responses.  
- pytest `test_phase07_step03_phase_boundaries.py`.

---

## 2026-05-16 — P07-02 anti-goals + forbidden cognition (runtime)

**Scope:** Step **2** shipped in `vector.domains.cortex.retrieval.anti_goals`.

### Added

- **G‑P07‑ANTI‑01** package import scan; **G‑P07‑ANTI‑02** ingress token rejection; **G‑P07‑SCHEMA‑01** denylist + `schemas/retrieval-query-envelope-v1.schema.json`.  
- `RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1` + `retrieval_forbidden` in legality class set.  
- Admin `POST .../retrieval/query` rejects anti-goal bodies (403).  
- `validate_retrieval_authoritative_output_algebra_v1` on query engine responses (**RET‑ANTI‑01**).  
- pytest `test_phase07_step02_anti_goals.py`.

---

## 2026-05-16 — P07-01 normative index + program freeze (runtime)

**Scope:** Step **1** shipped in `vector.domains.cortex.retrieval.normative`.

### Added

- `PHASE07_PROGRAM_FREEZE_VERSION` **1** (aligned with `phase-07-normative-index.md`).  
- `build_phase07_normative_program_document_v1` — public program-freeze document (bundles, pipeline, replay identity field).  
- pytest `test_phase07_step01_normative_freeze.py` — doc/runtime contract gate.

---

## 2026-05-16 — Architecture finalization pass (pre-implementation)

**Scope:** Specification + MASTER_TRACKER only — **no runtime code**.

### Added

- Normative tree `DOCS/cortex/retrieval/` with **30-step** program.  
- Query contract system: workload classes, envelopes, legality, caps.  
- Retrieval addressing model (`retrieval_lookup_id`, refs).  
- Provenance/evidence envelope law.  
- Temporal retrieval semantics.  
- Deterministic ranking (anti-semantic).  
- `RD-*` degradation taxonomy + substrate propagation.  
- Replay equivalence **G-P07-REPLAY-01/02**.  
- Observability + health model.  
- Admin control plane (**16 surfaces**).  
- Substrate overview integration (7th pipeline stage).  
- Runtime architecture + legality matrix.  
- Verification harness catalog + closure **RETRIEVAL-CERT-PACK-1**.  
- Implementation sequencing plan (waves 0–5).

### Boundaries

- Phase 07 explicitly **does not** own synthesis (08), products (09), or TCRE reconstruction (06).  
- Forbidden: embeddings-first retrieval, LLM ranking, NL query boxes.

### Upstream

- Hard dependency on Phase **06** TCRE doctrine + bounded runtime.  
- Hard dependency on Phase **05** OCTS durable walks (**19–23**).  
- Consumes RUNTIME-02 stable refs (`retrieval_lookup_id`, etc.).

### Tracker

- Replaced shallow 6-row Phase 07 table with **30 implementation-grade rows**.
