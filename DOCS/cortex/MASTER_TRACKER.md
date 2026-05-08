# Cortex Master Tracker

## 1) Project Snapshot
- **Architecture maturity:** Core foundation defined across Phases 01-04 and 10; storage/queryability challenge pass added.
- **Ingestion vs exhaust (non‑negotiable distinction):** **Substrate** (runs, replay lanes, envelope validation, checkpoint storage, admin triggers, verification jobs) is **not** Phase 01 success. **Phase 01 success** = **full raw organizational exhaust** per `DOCS/cortex/01-ingestion/phase-01-organizational-exhaust-spec.md` (pagination, per-stream cursors, backfill + incremental, replay semantics, exit criteria). Do not treat “sync ran,” “scope_ping rows exist,” or “integration connected” as exhaust progress. Deep exhaust is tracked in **§2.5**, `organizational-exhaust-execution-track.md`, `connector-exhaust-matrix.md`, `exhaust_coverage_registry.py`, and admin raw aggregates.
- **Implementation stage:** Phase 01 Steps **0–16** = ingestion substrate + checkpoint spine + connector depth + admin exhaust proof + verification gate + live-lane logical idempotency lock + runtime correctness hardening — **Yes (Phase 01 complete)**.
- **Current focus:** Phase 02 Step 1 planning/execution with Step 16 correctness suite active in operational verification.
- **Total phases:** 10.
- **Current blockers:** Phase 01 hard blockers cleared; remaining work is post-closure soak/scale confidence and later-phase architecture. (Cortex ingestion routing defaults **on**; use `CORTEX_CONNECTOR_MIGRATION_*=false` only to opt out.)
- **Next major milestone:** Phase 02 raw memory implementation kick-off with Phase 01 Step 16 invariant suite enforced in production-like runs.

## 2) Phase Overview
| Phase | Name | Goal | Architecture Status | Spec Completeness | Ready For Coding |
| ----- | ---- | ---- | ------------------- | ----------------- | ---------------- |
| 01 | Ingestion | Bring **organizational exhaust** safely into Cortex (substrate **and** connector depth) | **Substrate + checkpoint spine + Slack/GitHub/Linear/Notion/Calls deep slices + admin exhaust proof + verification gate + Step 15 live idempotency lock + Step 16 runtime correctness hardening** shipped (0–16) | Ready (Core Contracts Frozen) | **Phase 01 closure:** **Yes** |
| 02 | Raw Memory | Preserve immutable replayable organizational history | Architecture Defined | Ready With Caveats | Yes (Caveats) |
| 03 | Canonicalization | Transform raw exhaust into canonical memory | Architecture Defined | Needs Hardening | Almost |
| 04 | Identity & Linking | Reconstruct organizational continuity across tools/time | Architecture Defined | Core Defined | Almost |
| 05 | Organizational Graph | Model high-fidelity continuity and traversal structure | Not Started | Incomplete | No |
| 06 | Temporal & Causal Reasoning | Reconstruct causality and temporal organizational logic | Not Started | Incomplete | No |
| 07 | Retrieval & Query Engine | Operationalize high-signal cognition retrieval | Not Started | Incomplete | No |
| 08 | Synthesis & Intelligence Layer | Generate bounded intelligence from reconstructable memory | Not Started | Incomplete | No |
| 09 | Operational Intelligence Products | Deliver operator-facing cognition workflows | Not Started | Incomplete | No |
| 10 | Admin / Control Plane | Operate, inspect, and govern all Cortex phases | Architecture Defined | Core Defined | Almost |

## 2.5) Organizational Exhaust Coverage (first-class execution track)

**Purpose:** honest tracking of **what organizational exhaust we actually ingest** — independent of ingestion/replay/checkpoint **substrate** (“infrastructure”) **health signals** (those prove **wiring**, not **exhaust depth**).

**Primary artifacts:** **`DOCS/cortex/01-ingestion/phase-01-organizational-exhaust-spec.md`** (normative exhaust goal + exit criteria), **`DOCS/cortex/01-ingestion/phase-01-raw-persistence-doctrine.md`** (raw unit model per connector), **`DOCS/cortex/01-ingestion/phase-01-ingestion-continuity-doctrine.md`** (ingestion modes, idempotency, live/replay, convergence, checkpoints), **`DOCS/cortex/01-ingestion/phase-01-live-idempotency-doctrine.md`** (mandatory Step 15 live-lane correctness lock), **`DOCS/cortex/01-ingestion/phase-01-runtime-correctness-hardening-doctrine.md`** (Step 16 invariants + scope semantics), **`DOCS/cortex/implementation/organizational-exhaust-execution-track.md`** (gap map + roadmap + open decisions), `DOCS/cortex/connectors/connector-exhaust-matrix.md`, `backend/src/vector/domains/cortex/ingestion/exhaust_coverage_registry.py` (**update matrix + registry in the same PR** when streams change), `GET /admin/tenants/{tenant_id}/cortex/ingestion/exhaust-coverage`, `GET /admin/tenants/{tenant_id}/cortex/ingestion/raw-stats`, `DOCS/cortex/01-ingestion/real-ingestion-definition.md` (short form), `DOCS/cortex/connectors/ingestion-depth-model.md`, `DOCS/cortex/implementation/connector-expansion-roadmap.md`.

### Completeness matrix (snapshot — see matrix doc + registry for detail)

| Connector | Resource type (examples) | Coverage | Historical backfill | Replay safe | Canonicalized | Status |
| --------- | ------------------------ | -------- | ------------------- | ----------- | ------------- | ------ |
| Slack | `slack.user` / `slack.conversation` / `slack.message` / `slack.message_reply` / `slack.reaction` / `slack.file` | **partial** | **partial** (cursor-backed channel/thread continuation, still bounded per run) | **partial** | **none** | **in_progress** |
| Slack | `slack.scope_ping` | **partial** | n/a | **partial** | **none** | **in_progress** — **connectivity-only** / **non-exhaust** (emitted when connection detail missing) |
| GitHub | `github.installation_repositories` / `github.repository` | **partial** | **partial** (paged install scan; env max pages) | **partial** | **none** | **in_progress** |
| GitHub | `github.pull_request` / reviews / comments / commits / checks / workflows / deployments / branches / tags | **partial** | **partial** (cursor-backed page continuity per repo, bounded per run) | **partial** | **none** | **in_progress** |
| Linear | `linear.issue` / `linear.comment` / `linear.project` / `linear.cycle` / `linear.issue_relation` / `linear.issue_label` / `linear.initiative` / `linear.issue_attachment` / `linear.activity_history` | **partial/full** | **partial** | **partial** | **none** | **in_progress** (Step 10 core shipped; still bounded per-run) |
| Linear | `linear.viewer_ping` | **partial** | n/a | **partial** | **none** | **active** — **connectivity-only** / **non-exhaust** |
| Notion | `notion.search_result` / `notion.page` / `notion.database` / `notion.database_row` / `notion.block` | **partial** | **partial** | **partial** | **none** | **in_progress** |
| Notion | `notion.scope_ping` | **partial** | n/a | **partial** | **none** | **in_progress** — connectivity row retained; **non-exhaust by itself** |
| Calls | `calls.meeting` / `calls.participant` / `calls.transcript` / `calls.transcript_segment` / `calls.recording` | **partial** | **partial** | **partial** | **none** | **in_progress** |
| Calls | `calls.scope_ping` | **partial** | n/a | **partial** | **none** | **in_progress** — connectivity row retained; **non-exhaust by itself** |

**Interpretation:** Runtime correctly implements **substrate** behavior — **orchestration, replay lane semantics, checkpoints, raw persistence, admin, and verification** — for **partial / shallow** streams today; **remaining work is deep organizational exhaust** per connector (pagination, resource types, backfill windows, mapper-ready fields) — not re‑proving that the substrate exists.

**Matrix legend caveat:** For `*.scope_ping` / `viewer_ping`, **active** status or **non-trivial** coverage columns still mean **connectivity-only** / **synthetic health** — **non-exhaust**, not organizational depth. Do not treat them as Phase 01 exhaust progress.

### 2.6) Runtime vs authoritative doctrine — gap register (honest)

| Capability | Authoritative docs | Runtime today (`sync_executor`, `checkpoint_contract`, …) |
| ---------- | ------------------ | ---------------------------------------------------------- |
| **Dual-mode ingestion** (historical backfill cursors **distinct from** incremental watermarks) | `phase-01-ingestion-continuity-doctrine.md` §1–3 | **Partially implemented** — dual checkpoint lanes (`modes.incremental` / `modes.backfill`) shipped; runtime scheduler/backfill walkers still incremental-only today |
| **Live logical idempotency** (stable keys **without** `run_id` for hot streams) | Continuity §4; live idempotency doctrine | **Implemented (Step 15 core)** — live writes use logical identity+revision keys with conflict-ignore insertion; replay namespace remains isolated |
| **Slack** `conversations.history` **cursor** + per-channel checkpoint | Steps 8, 7; execution track B.1 | **Implemented (Step 8 core)** — per-channel history cursor + ring resume + time-budget chunking; still bounded by per-run page caps |
| **Slack** thread replies (`slack.message_reply`) | `phase-01-raw-persistence-doctrine.md` §2.1 | **Implemented (Step 8 core)** — `conversations.replies` for discovered thread roots with per-thread cursor continuity |
| **GitHub** full `/pulls` pagination + per-repo cursors | Step 9, 7 | **Implemented (Step 9 core)** — page continuity + per-repo checkpoint state + ring resume |
| **GitHub** reviews / comments / checks / workflows | Step 9 | **Implemented (Step 9 core)** — bounded per-run pages with checkpoint continuity |
| **Linear** `pageInfo` + `updatedAt` incremental | Step 10 | **Implemented** — paginated issues connection + checkpointed end-cursor + incremental `updatedAt` watermark |
| **Notion** pages / databases / blocks | Step 11 | **Implemented (Step 11 core):** paginated `/search`, `/databases/{id}`, `/databases/{id}/query`, `/blocks/{id}/children` with checkpointed continuation + time-budget resume |
| **Calls** transcripts / participants | Step 12 | **Implemented (Step 12 core):** checkpointed meeting/event pagination + `calls.meeting`, `calls.participant`, `calls.transcript`, `calls.transcript_segment`, `calls.recording`; `calls.scope_ping` auxiliary only |
| **Replay lane** idempotency `(replay_job_id, key)` | Continuity §6 | **Implemented** (partial index / ON CONFLICT) |
| **Checkpoint deep merge** + nested per-scope cursors | Step 7; continuity §7 | **Implemented (Step 7)** — schema versioning, migration, deep merge for nested maps, stream ownership metadata, corruption recovery hook, side-table advisory threshold |
| **Optional `cortex_backfill` queue** | Continuity §9 | **Not implemented** |
| **Admin exhaust proof** (aggregates, hide pings default) | Step 13; exhaust spec §10 | **Implemented (Step 13 core):** `raw-stats` supports connector/resource/time filters with default health-row hide; connector raw drilldown supports time + payload search + default health-row hide; frontend admin exposes operator filters and aggregate tables |
| **Verification gate** (exhaust depth + reconstruction drill) | Step 14; exhaust spec §11 | **Implemented (Step 14 core):** verification endpoint enforces gate checks (`ping_ratio_after_streams`, multi-connector evidence, reconstruction signal coverage), exposes reconstruction checklist payload, and runbook exists in `phase-01-reconstruction-drill-checklist.md` |
| **Runtime correctness hardening** (concurrency/retry/crash/checkpoint/replay overlap/live dedupe/connection scope) | Step 16 doctrine | **Implemented (Step 16 core):** connection-scoped live uniqueness, explicit connection scope for manual/replay triggers, scheduler emits connection-scoped jobs, runtime correctness invariant suite integrated into tenant verification, and dedicated Step 16 tests |

**Implementation note — live idempotency:** Step 15 + Step 16 are both shipped; live idempotency is logical-key based and validated by runtime correctness invariants.

**Use §2.6** to prevent tracker or admin copy from **overstating** parity with `phase-01-*-doctrine.md`.

## 3) Phase-By-Phase Step Tracker

### Terminal step — admin & operator closure (mandatory, all phases)

No phase is **complete** until its **last numbered step** in this tracker ships **both** production runtime **and** a **strong admin / control plane update** for that same phase.

- **Scope:** Phases **02–10 Step 6**. **Phase 01 exception:** substrate **operator closure** is Step **6**; **phase closure** requires Steps **7–16** (Step 16 is the final runtime-correctness hardening gate).
- **“Strong admin update” means at minimum:**
  1. **Visibility** — Operator UI reflects *this phase’s* new reality: health signals, lag/backlog, failure classes, and (where applicable) replay / reprocess / provenance context—not only raw logs.
  2. **Actions** — At least one **primary**, policy-gated operator control for that phase (manual trigger, scoped replay/reprocess, safe pause/resume, cohort toggle, etc.) with clear **scope, queue lane, and expected impact** before execution.
  3. **Verification** — A defined “**phase is working**” checklist runnable from the admin surface (smoke flows, invariant badges, drilldown to receipts), so we can confirm end-to-end behavior after rollout.
- **Spec references:** Visualization contract `10-admin/phase-visualization-model.md`; dangerous-action and RBAC patterns `10-admin/dangerous-action-safety-model.md`, `10-admin/admin-permissions-model.md`.
- **Phase 10:** Step 6 **unifies** cross-phase navigation and governance; it **does not** remove the requirement that **each** earlier phase already delivered its **own** Step **6** admin slice when that phase closed.

**Status Legend**
- **Spec Accuracy:** `Not Started` | `Defined` | `Strong` | `Strong (Caveats)` | `Ready To Start`
- **Implemented:** `No` | `In Progress` | `Yes`

### Phase 01 — Ingestion

**Organizational exhaust completion (definition):** Phase 01 is complete only when raw ingestion is deep enough to reconstruct organizational execution movement across communication, planning, review, delivery, and coordination streams **and** live-lane logical idempotency is revision-safe and deterministic.

**Step 7 — foundation layer (unlocks Steps 8–15):** implemented prerequisite for deep connector API pull. Deliverables:

- **`checkpoint_schema_version`** (or equivalent) and **backward-compatible** reads/writes of `connector_sync_state`
- **Nested cursor ownership rules** — which stream owns which keys; documented merge precedence; no silent cross-stream clobber
- **Deep merge semantics** for checkpoint JSON — not only the current flat numeric monotonic fields (`checkpoint_contract` today)
- **Dual-cursor model** — **incremental** watermarks **and** **historical backfill** cursors, **distinct** and **merge-safe**, per `phase-01-ingestion-continuity-doctrine.md`
- **Checkpoint migration path** — flat / legacy keys → nested structure with a **rolling** upgrade story
- **Cursor corruption recovery path** — detect invalid state, scoped reset, **operator-visible** outcome
- **Optional side-table escape hatch** — criterion + wiring when checkpoint blobs exceed safe size or query patterns
- **Cursor validation tests** — merge, migration, corruption, and regression cases
- **Replay / live checkpoint isolation** — replay jobs must not **overwrite** live incremental cursors; doctrine-aligned boundaries

| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 0 | Connector migration safety plan | Legacy-to-Cortex connector cutover safety and rollback strategy | Strong | Yes (spec appendices + `vector.domains.cortex.connectors` + migration flags/policy; executor Step 6+) |
| 1 | Connector ingestion lifecycle | Run → fetch → raw append-only rows → checkpoint (`ingestion_runs`, `raw_ingestion_records`, `connector_sync_state`) + Celery executor. **Phase 01 is *not* done for a connector when only substrate or health pings exist:** exhaust work includes **connector exhaust expansion**, **pagination completeness**, **resource-type expansion**, **historical sync/backfill**, **replay-safe deep retrieval**, and **large-scale persistence operations** — tracked in §2.5 and `implementation/connector-expansion-roadmap.md`. | Strong | Yes (`vector.domains.cortex.ingestion`, `app.tasks.cortex_ingestion_sync`, migration `20260508_0030`) |
| 2 | Polling and orchestration model | Sync cadence, queueing, orchestration defined | Strong | Yes (Beat tick + `cortex_live` lane + `iter_routed_live_sync_jobs`; env `CORTEX_INGESTION_SCHEDULER_*`, `CORTEX_INGESTION_MIN_GAP_SECONDS`) |
| 3 | Replay-safe ingestion semantics | Ingestion replay behavior and boundaries defined | Strong | Yes (context + lanes + migration `20260508_0031`; `run_sync_replay`, replay checkpoint scope, raw dedupe + `cortex_replay_metadata`) |
| 4 | Ingestion persistence contracts | Raw envelope, runs, checkpoints contracts defined | Strong | Yes (`raw_envelope_contract`, `checkpoint_contract`, `sync_context` sync_mode allowlist, executor validation + monotonic checkpoints; `PHASE_STEP4`) |
| 5 | Ingestion verification model | Invariant, failure-probe, chaos verification defined | Strong | Yes (`verification.py`, post-sync hook + `PHASE_STEP5`, Celery `vector.cortex.ingestion.verify_tenant`, admin invariant sweep) |
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for **substrate** only: visibility, scoped safe actions, verification that **substrate controls and probes** work (see **Terminal step** above) — **not** proof of organizational exhaust depth. Does **not** close Phase 01 exhaust. | Strong | Yes (`admin_overview`, admin HTTP + SPA Cortex ingestion tab, gated sync/replay/scheduler pause, `PHASE_STEP6`, Beat+Redis pause) |
| 7 | Exhaust checkpoint spine | **Foundation layer for Steps 8–14** — full deliverable list in **Step 7 — foundation layer** bullets above. Normative sequencing: `organizational-exhaust-execution-track.md` **R0**. **Implemented:** `checkpoint_contract.py` v2 schema + migration/deep merge/recovery, executor wiring (`sync_mode` lane writes + nested stream ownership), scheduler/admin/verification readers aligned, test coverage in `test_checkpoint_contract.py`, `test_sync_context.py`, `test_step3_replay_integration.py`. | Strong | Yes |
| 8 | Slack organizational exhaust | Full `conversations.history` **cursor** backfill + incremental per channel; `conversations.replies` (threads); reactions; files; time-budgeted Celery chunks + resume; DM/MPIM only if policy allows. **R1**. **Implemented core:** `sync_executor.py` Slack pagination + per-channel/per-thread checkpoints, `slack.message_reply` rows, reaction/file rows, channel time-budget resume + ring progression, admin/manual sync now supports `sync_mode=backfill`; matrix + registry updated. **Remaining Slack depth outside Step 8 core:** edits/pins/bookmarks/canvases and DM/MPIM policy expansion. | Strong | Yes |
| 9 | GitHub organizational exhaust | Full `/pulls` **pagination**; PR reviews; review + issue comments; commits; check runs; Actions workflow runs; deployments + statuses; branches/tags; per-repo cursors + rate-limit strategy. **R2**. **Implemented core:** paginated PR spine + review/comment/commit/check/workflow/deployment/branch/tag streams with per-repo checkpoint pages and resume budget; matrix + registry updated. | Strong | Yes |
| 10 | Linear organizational exhaust | Issues: GraphQL `pageInfo` pagination + `updatedAt` incremental watermark; comments; labels; projects; cycles; attachments; relations / activity as in matrix. **R3**. **Implemented core:** paginated issue cursor + watermark filtering in checkpoint (`streams.linear.issues`), paginated comments/projects/cycles/issueRelations/issueLabels/initiatives streams, issue attachment/activity extraction when present, linear deep-stream counters in checkpoint + registry/matrix updates + Step 10 integration tests. | Strong | Yes |
| 11 | Notion organizational exhaust | Workspace traversal implemented: `/search` pagination with checkpoint cursor + watermark, discovered database metadata + `/databases/{id}/query` pagination, nested `/blocks/{id}/children` traversal with per-parent cursor continuity, plus Step 11 test coverage (`test_step11_notion_exhaust.py`). `notion.scope_ping` remains auxiliary only. **R4**. | Strong | Yes |
| 12 | Calls / meetings organizational exhaust | Implemented core: checkpointed calls event pagination (`streams.calls.events`), raw meeting metadata rows (`calls.meeting`), attendee rows (`calls.participant`), transcript rows (`calls.transcript`), transcript segment rows (`calls.transcript_segment`), recording metadata rows (`calls.recording`), plus Step 12 integration coverage (`test_step12_calls_exhaust.py`). **R5**. | Strong | Yes |
| 13 | Admin organizational exhaust proof | Implemented core: backend `raw-stats` now supports connector/resource/time filters with default `*.scope_ping`/`viewer_ping` hide, connector raw drilldown supports payload search + time filters + explicit health-row include, frontend Cortex admin exposes these Step 13 proof controls and aggregate tables. **R6**. | Strong | Yes |
| 14 | Phase 01 exhaust verification gate | Implemented core: verification endpoint now enforces exhaust gate checks (ping-ratio threshold after streams, cross-connector evidence, reconstruction signal coverage), emits reconstruction drill checklist fields, and checklist runbook is documented in `phase-01-reconstruction-drill-checklist.md`. **R7**. | Strong | Yes |
| 15 | Live-lane logical idempotency + revision-safe ingestion | Implemented core: `source_identity_key` + `source_revision_key` persisted per raw row, canonical source-payload hashing, live conflict-ignore dedupe via unique logical key index (`replay_job_id IS NULL`), replay uniqueness preserved, admin/raw drilldown exposes identity+revision fields, and Step 15 integration coverage validates live dedupe + revision append semantics. **R8**. | Strong | Yes |
| 16 | Runtime correctness hardening | Implemented core: runtime correctness invariant suite (`runtime_correctness.py`) added to tenant verification; connection-scoped live uniqueness semantics (`tenant+connection+connector+identity+revision`) enforced; scheduler and task dispatch now carry explicit `connection_id`; admin trigger sync/replay supports explicit `connection_id` and rejects ambiguous multi-active connector scope; Step 16 integration/unit tests cover overlap, retries, checkpoints, and connection scoping. **R9**. | Strong | Yes |

### Missing / Incomplete
- **Phase 01 closure step status:** Step 16 shipped; remaining Phase 01 tasks are soak/telemetry maturity, not correctness blockers.
- **§2.6** — Step 15 and Step 16 runtime/doctrine parity hardened.
- Large-scale ingest + replay contention behavior still unvalidated in production.
- Throughput limits and SLO envelopes remain theoretical until runtime testing.
- Connector migration parity benchmarks (legacy vs Cortex path): **legacy poll worker removed** — parity applies to **mock vs real API** and Cortex executor behavior under flags.
- ~~Frozen-core runtime checks (Step 4)~~ **Done** for persisted raw payloads + checkpoint monotonic merge; **Step 5** ships automated per-run + tenant invariant probes; deeper chaos/failure-matrix automation remains **Step 6+** as operational maturity grows.
- Step 0 **shadow rollout plan approval** still needs **dual-path soak** + operator sign-off in live environments (Step 6 admin + controls are in place to support that).

### Implementation Blockers
- **Exhaust blockers (Phase 01):** none (Steps 0–16 complete).
- **Operational caveat (post–Step 7):** Deep organizational exhaust is **operational ingestion engineering** — expect **API rate-limit pressure**, **checkpoint complexity**, **replay contention** with live lanes, **large-scale raw storage growth**, and **long-horizon backfill scheduling** tradeoffs.
- Storage/queryability threshold baselines must be finalized for replay-heavy windows.
- ~~Step 0 documentation (single spec file + appendices)~~ **cleared** (2026-05-07). **Cortex ingestion executor + Steps 7–16 are shipped** for substrate + Slack/GitHub/Linear/Notion/Calls depth + admin proof + verification gate + live idempotency + runtime correctness hardening.
- Envelope stability policy must be wired into schema validation tests before rollout.

**Confidence:** **High** for Phase 01 closure behavior; continue production-like soak for Step 16 invariants and duplicate-prevention telemetry confidence.

---

### Phase 02 — Raw Memory
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Immutable memory model | Raw event immutability and lifecycle defined | Strong | No |
| 2 | Provenance-safe raw retention | Evidence-preserving storage semantics defined | Strong | No |
| 3 | Replay foundation rules | Replay dependency on raw memory defined | Strong | No |
| 4 | Raw access/query contracts | Query and retrieval boundaries documented | Strong | No |
| 5 | Raw-store governance and recovery | Corruption/recovery and governance model defined | Strong | No |
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Ready To Start | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

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
| 6 | Runtime implementation + admin closure | Deliver runtime **and** operator-grade admin for this phase: visibility, scoped safe actions, verification that the phase is healthy (see **Terminal step — admin & operator closure** above). | Not Started | No |

### Missing / Incomplete
- Integration detail with real runtime phase services is not yet specified.
- Operational load behavior for admin-heavy investigations remains unvalidated.

### Implementation Blockers
- Depends on initial runtime implementation of Phases 01-04 for end-to-end admin integration.

**Confidence:** Medium Confidence

## 4) Current Implementation Priority
- **Completed (Step 0–6, Phase 01 substrate):** Step 5 as before. **Step 6:** operator ingestion control plane — `vector.domains.cortex.ingestion.admin_overview`, `vector.infrastructure.cortex_scheduler_pause`, admin API under `/admin/tenants/{id}/cortex/ingestion` (+ **exhaust-coverage**, **raw-stats**, per-connector **raw-records** browse, actions + global scheduler pause), frontend **Cortex ingestion** tab (substrate + **declared exhaust** panel + ingested-data tabs for **current shallow / partial** streams only), `connector_sync` enqueue for all five connectors; tests `test_step2_scheduler` (Redis pause path), `test_admin_cortex_ingestion_step6` (integration).
- **Current goal:** Phase 02 Step 1 implementation while running Phase 01 Step 15 soak/telemetry checks.
- **Parallel:** migration flags and operator soak continue; Phase 01 closure criteria are already met.
- **Next planned implementation entry:** Phase 02 Step 1.

## 5) Implementation Readiness
| Phase | Architecture | Verification | Ready For Coding |
| ----- | ------------ | ------------ | ---------------- |
| 01 | **Complete through Step 15:** substrate + deep connector exhaust + admin proof + verification gate + live logical idempotency lock | Step 5/6 + Step 7–15 test coverage (integration-marked suites + admin/API verification gates) | **Yes (Phase 01 closed)** |
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
