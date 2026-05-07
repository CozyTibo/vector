# Cortex Master Tracker

## 1) Project Snapshot
- **Architecture maturity:** Core foundation defined across Phases 01-04 and 10; storage/queryability challenge pass added.
- **Implementation stage:** Phase 01 Step 0 **complete** (connector package + migration flags/policy). **Step 1 complete:** ingestion tables + `vector.domains.cortex.ingestion.sync_executor`, Celery `vector.cortex.ingestion.run_sync`, admin enqueue when `CORTEX_CONNECTOR_MIGRATION_*` routes the tenant. **Step 2 complete:** Celery Beat `vector.cortex.ingestion.scheduler_tick`, `cortex_live` queue routing, `vector.domains.cortex.ingestion.scheduler` (routed connections + min-gap), settings `CORTEX_INGESTION_*`. **Still open:** replay semantics (**Step 3**), envelope validation hardening (**Steps 4–5**), shadow/active parity + production rollout (**Step 6**).
- **Current focus:** Phase 01 **Step 3** — replay-safe ingestion semantics and runtime boundaries.
- **Total phases:** 10.
- **Current blockers:** Cross-phase replay/query scaling validation; deploy must set **`CORTEX_CONNECTOR_MIGRATION_*`** when enabling routed sync; later-phase verification depth.
- **Next major milestone:** Phase 01 Step 3 replay-safe ingestion semantics, then persistence contract enforcement (Steps 4–5).

## 2) Phase Overview
| Phase | Name | Goal | Architecture Status | Spec Completeness | Ready For Coding |
| ----- | ---- | ---- | ------------------- | ----------------- | ---------------- |
| 01 | Ingestion | Bring organizational data safely into Cortex | Architecture Defined | Ready (Core Contracts Frozen) | Yes (Core Contracts Frozen) |
| 02 | Raw Memory | Preserve immutable replayable organizational history | Architecture Defined | Ready With Caveats | Yes (Caveats) |
| 03 | Canonicalization | Transform raw exhaust into canonical memory | Architecture Defined | Needs Hardening | Almost |
| 04 | Identity & Linking | Reconstruct organizational continuity across tools/time | Architecture Defined | Core Defined | Almost |
| 05 | Organizational Graph | Model high-fidelity continuity and traversal structure | Not Started | Incomplete | No |
| 06 | Temporal & Causal Reasoning | Reconstruct causality and temporal organizational logic | Not Started | Incomplete | No |
| 07 | Retrieval & Query Engine | Operationalize high-signal cognition retrieval | Not Started | Incomplete | No |
| 08 | Synthesis & Intelligence Layer | Generate bounded intelligence from reconstructable memory | Not Started | Incomplete | No |
| 09 | Operational Intelligence Products | Deliver operator-facing cognition workflows | Not Started | Incomplete | No |
| 10 | Admin / Control Plane | Operate, inspect, and govern all Cortex phases | Architecture Defined | Core Defined | Almost |

## 3) Phase-By-Phase Step Tracker

**Status Legend**
- **Spec Accuracy:** `Not Started` | `Defined` | `Strong` | `Strong (Caveats)` | `Ready To Start`
- **Implemented:** `No` | `In Progress` | `Yes`

### Phase 01 — Ingestion
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 0 | Connector migration safety plan | Legacy-to-Cortex connector cutover safety and rollback strategy | Strong | Yes (spec appendices + `vector.domains.cortex.connectors` + migration flags/policy; executor Step 6+) |
| 1 | Connector ingestion lifecycle | Run → fetch → raw append-only rows → checkpoint (`ingestion_runs`, `raw_ingestion_records`, `connector_sync_state`) + Celery executor | Strong | Yes (`vector.domains.cortex.ingestion`, `app.tasks.cortex_ingestion_sync`, migration `20260508_0030`) |
| 2 | Polling and orchestration model | Sync cadence, queueing, orchestration defined | Strong | Yes (Beat tick + `cortex_live` lane + `iter_routed_live_sync_jobs`; env `CORTEX_INGESTION_SCHEDULER_*`, `CORTEX_INGESTION_MIN_GAP_SECONDS`) |
| 3 | Replay-safe ingestion semantics | Ingestion replay behavior and boundaries defined | Strong | No |
| 4 | Ingestion persistence contracts | Raw envelope, runs, checkpoints contracts defined | Strong | No |
| 5 | Ingestion verification model | Invariant, failure-probe, chaos verification defined | Strong | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Large-scale ingest + replay contention behavior still unvalidated in production.
- Throughput limits and SLO envelopes remain theoretical until runtime testing.
- Connector migration parity benchmarks (legacy vs Cortex path): **legacy poll worker removed** — parity applies to **mock vs real API** and **future Cortex path vs prior behavior**, once executor exists.
- Frozen-core contract doctrine is defined; runtime contract enforcement checks still to be implemented.
- Step 0 **shadow rollout plan approval** still blocked until **dual-path executor soak** + operational gates (**Phase 01 Step 6**).

### Implementation Blockers
- Storage/queryability threshold baselines must be finalized for replay-heavy windows.
- ~~Step 0 documentation (single spec file + appendices)~~ **cleared** (2026-05-07). Production cutover still needs **executor** + soak behind flags.
- Envelope stability policy must be wired into schema validation tests before rollout.

**Confidence:** High Confidence

---

### Phase 02 — Raw Memory
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Immutable memory model | Raw event immutability and lifecycle defined | Strong | No |
| 2 | Provenance-safe raw retention | Evidence-preserving storage semantics defined | Strong | No |
| 3 | Replay foundation rules | Replay dependency on raw memory defined | Strong | No |
| 4 | Raw access/query contracts | Query and retrieval boundaries documented | Strong | No |
| 5 | Raw-store governance and recovery | Corruption/recovery and governance model defined | Strong | No |
| 6 | Runtime implementation | Coding and production rollout | Ready To Start | No |

### Missing / Incomplete
- Extreme-window replay economics are modeled but not yet benchmarked.
- Archive rehydration throughput and deep-window query plans require runtime calibration.

### Implementation Blockers
- No foundational blockers; proceed with first-slice validation gates from `02-raw-store/raw-memory-readiness-gates.md`.

**Confidence:** High Confidence (With Caveats)

---

### Phase 03 — Canonicalization
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Canonical memory model | Canonical entities/events/relations model defined | Strong | No |
| 2 | Mapping and extraction boundaries | Deterministic vs AI extraction boundaries defined | Strong | No |
| 3 | Ambiguity and confidence model | Ambiguity persistence and confidence propagation defined | Strong | No |
| 4 | Replay/idempotency semantics | Canonical replay/version/idempotency contracts defined | Strong | No |
| 5 | Canonical observability/failure model | Failure and quality guardrails defined | Strong | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Canonical query optimization strategy is documented but not yet validated with workload traces.
- Canonical verification doctrine is weaker than Phase 01 operational verification depth.

### Implementation Blockers
- Depends on storage/queryability baselines and replay economics thresholds.

**Confidence:** Needs Architectural Validation

---

### Phase 04 — Identity & Linking
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Identity resolution model | Cross-tool identity continuity model defined | Strong | No |
| 2 | Organizational linkage model | Entity/topic/initiative linkage semantics defined | Strong | No |
| 3 | Ambiguity persistence model | Conflict and uncertain linkage persistence defined | Strong | No |
| 4 | Temporal continuity model | Ownership/initiative evolution linkage defined | Strong | No |
| 5 | Replay/provenance linkage semantics | Replay-safe linkage lineage constraints defined | Strong | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Identity replay verification at scale is not yet concretely validated.
- Cross-tool linkage query saturation behavior remains unproven.

### Implementation Blockers
- Waiting on lineage/provenance traversal thresholds from storage challenge outcomes.

**Confidence:** Needs Architectural Validation

---

### Phase 05 — Organizational Graph Layer
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Graph continuity model | Define graph-level continuity representation | Not Started | No |
| 2 | Traversal contract model | Define bounded traversal contracts and semantics | Not Started | No |
| 3 | Temporal graph behavior | Define edge validity and temporal path semantics | Not Started | No |
| 4 | Graph replay semantics | Define replay consistency for graph projections | Not Started | No |
| 5 | Graph observability model | Define graph traversal diagnostics and limits | Not Started | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Full phase architecture not yet authored.

### Implementation Blockers
- Requires validated outcomes from Phase 04 + storage traversal cost analysis.

**Confidence:** Experimental

---

### Phase 06 — Temporal & Causal Reasoning
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Temporal reasoning model | Define temporal reasoning primitives | Not Started | No |
| 2 | Causal reconstruction model | Define causality inference boundaries | Not Started | No |
| 3 | Reasoning provenance model | Define explainable reasoning evidence chains | Not Started | No |
| 4 | Replay-aware reasoning model | Define reasoning replay consistency semantics | Not Started | No |
| 5 | Failure/uncertainty model | Define reasoning uncertainty and conflict handling | Not Started | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Entire phase specification pending.

### Implementation Blockers
- Depends on completed graph/lineage substrate and queryability validation.

**Confidence:** Experimental

---

### Phase 07 — Retrieval & Query Engine
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Query contract model | Define retrieval/query contracts by workload class | Not Started | No |
| 2 | Retrieval ranking model | Define deterministic + bounded semantic retrieval strategy | Not Started | No |
| 3 | Provenance-aware retrieval | Define retrieval evidence guarantees | Not Started | No |
| 4 | Temporal retrieval strategy | Define as-of and evolution-aware retrieval behavior | Not Started | No |
| 5 | Query observability integration | Define retrieval performance/quality monitoring | Not Started | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Entire phase specification pending.

### Implementation Blockers
- Needs finalized storage/queryability architecture decisions and readiness gates.

**Confidence:** Experimental

---

### Phase 08 — Synthesis & Intelligence Layer
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Synthesis contract model | Define bounded synthesis outputs and constraints | Not Started | No |
| 2 | AI authority boundaries | Define strict synthesis AI governance and limits | Not Started | No |
| 3 | Evidence-backed synthesis | Define citation/provenance requirements for outputs | Not Started | No |
| 4 | Replay-safe synthesis behavior | Define reproducibility and replay semantics | Not Started | No |
| 5 | Synthesis quality governance | Define evaluation and drift controls | Not Started | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Entire phase specification pending.

### Implementation Blockers
- Depends on retrieval phase and full provenance/reasoning integrity foundation.

**Confidence:** Experimental

---

### Phase 09 — Operational Intelligence Products
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Product workflow definition | Define operator workflows powered by Cortex memory | Not Started | No |
| 2 | Incident/debug products | Define execution-debugging product surface | Not Started | No |
| 3 | Governance and controls | Define product-level safety and review controls | Not Started | No |
| 4 | Human-in-the-loop model | Define operator intervention and escalation flows | Not Started | No |
| 5 | Product observability model | Define user and operational quality signals | Not Started | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Entire phase specification pending.

### Implementation Blockers
- Depends on maturity of Phases 06-08 and admin operational readiness.

**Confidence:** Experimental

---

### Phase 10 — Admin / Control Plane
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Workspace phase visibility | Phase state and progress visualization defined | Strong | No |
| 2 | Replay/reprocess operator controls | Replay/flush/reprocess control model defined | Strong | No |
| 3 | Provenance/ambiguity inspection UX | Operator inspection model defined | Strong | No |
| 4 | Failure explanation model | Failure state explanation and diagnosis model defined | Strong | No |
| 5 | Permissions and dangerous actions | Admin safety and authorization model defined | Strong | No |
| 6 | Runtime implementation | Coding and production rollout | Not Started | No |

### Missing / Incomplete
- Integration detail with real runtime phase services is not yet specified.
- Operational load behavior for admin-heavy investigations remains unvalidated.

### Implementation Blockers
- Depends on initial runtime implementation of Phases 01-04 for end-to-end admin integration.

**Confidence:** Medium Confidence

## 4) Current Implementation Priority
- **Completed (Step 0–2):** Step 0 safety spec + `vector.domains.cortex.connectors` + migration policy. **Step 1:** Alembic `20260508_0030_cortex_phase01_ingestion_tables`, ORM `IngestionRun` / `RawIngestionRecord` / `ConnectorSyncState`, `vector.domains.cortex.ingestion.sync_executor`, Celery task `vector.cortex.ingestion.run_sync`, admin `connector_sync.enqueue_*` → task when flags route to Cortex. **Step 2:** Beat schedule `vector.cortex.ingestion.scheduler_tick`, worker queue `cortex_live`, `app.tasks.cortex_ingestion_scheduler` + `vector.domains.cortex.ingestion.scheduler`; tests under `tests/vector/domains/cortex/`.
- **Current goal:** Phase 01 **Step 3** — replay-safe ingestion semantics (`01-ingestion` replay docs) and runtime enforcement where specified.
- **Next planned implementation entry:** Step 3 replay semantics, then Step 4 persistence contract enforcement in runtime.

## 5) Implementation Readiness
| Phase | Architecture | Verification | Ready For Coding |
| ----- | ------------ | ------------ | ---------------- |
| 01 | Complete | Complete | Yes |
| 02 | Complete | Complete (Caveats) | Yes (Caveats) |
| 03 | Complete | Partial | Almost |
| 04 | Complete | Partial | Almost |
| 05 | Not Started | Not Started | No |
| 06 | Not Started | Not Started | No |
| 07 | Not Started | Not Started | No |
| 08 | Not Started | Not Started | No |
| 09 | Not Started | Not Started | No |
| 10 | Complete | Partial | Almost |

## 6) Current Architecture Gaps
- Large-scale replay economics and replay contention behavior still theoretical.
- Temporal lineage and deep provenance traversal costs not yet empirically validated.
- Identity linkage ambiguity backlog operations are not yet operationally tested.
- Cross-phase verification depth is uneven (strong in Phase 01, weaker in later phases).
- Future reasoning/retrieval/synthesis phases remain architecture-light or not started.

## 7) Open High-Risk Areas
- Replay scan cost growth under multi-year history.
- Join/recursion explosion for lineage and provenance queries.
- Indexing pressure and write amplification across replay + temporal workloads.
- Cross-tool continuity traversal latency in incident/debug windows.
- Admin operational load under concurrent replay and deep diagnostics.

## 8) Future Phases Roadmap
- **05 — Organizational Graph Layer:** Graph-structured continuity and traversal substrate.
- **06 — Temporal & Causal Reasoning:** Causal reconstruction over temporal organizational memory.
- **07 — Retrieval & Query Engine:** High-signal retrieval with provenance and temporal grounding.
- **08 — Synthesis & Intelligence Layer:** Bounded intelligence outputs from reconstructable evidence.
- **09 — Operational Intelligence Products:** Human-facing operational cognition workflows.
- **10 — Admin / Control Plane:** Cross-phase operation, governance, and debugging interface.

## 9) Document Usage Rules
- This file is operational tracking only; deep specs remain in phase folders.
- Keep entries one-line and status-driven; avoid architecture duplication.
- Update statuses, gaps, blockers, and confidence on every major architecture change.
- Use this file as the first-read command center before opening deep docs.
