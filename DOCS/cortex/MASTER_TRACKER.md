# Cortex Master Tracker

## 1) Project Snapshot
- **Architecture maturity:** Core foundation defined across Phases 01-04 and 10; storage/queryability challenge pass added.
- **Ingestion vs exhaust (non‑negotiable distinction):** **Substrate** (runs, replay lanes, envelope validation, checkpoint storage, admin triggers, verification jobs) is **not** Phase 01 success. **Phase 01 success** = **full raw organizational exhaust** per `DOCS/cortex/01-ingestion/phase-01-organizational-exhaust-spec.md` (pagination, per-stream cursors, backfill + incremental, replay semantics, exit criteria). Do not treat “sync ran,” “scope_ping rows exist,” or “integration connected” as exhaust progress. Deep exhaust is tracked in **§2.5**, `organizational-exhaust-execution-track.md`, `connector-exhaust-matrix.md`, `exhaust_coverage_registry.py`, and admin raw aggregates.
- **Implementation stage:** Phase 01 Steps **0–16** = ingestion substrate + checkpoint spine + connector depth + admin exhaust proof + verification gate + live-lane logical idempotency lock + runtime correctness hardening — **Yes (Phase 01 complete)**.
- **Current focus:** Phase **03** Canonicalization program entry (**Steps 1–18** doctrine-locked); Phase **02** Raw Memory stabilization (**Steps 1–16**) shipped including operational trust proof **G16**.
- **Total phases:** 10.
- **Current blockers:** Phase 01 hard blockers cleared; remaining work is post-closure soak/scale confidence and later-phase architecture. (Cortex ingestion routing defaults **on**; use `CORTEX_CONNECTOR_MIGRATION_*=false` only to opt out.)
- **Next major milestone:** Phase **03 Step 1** — canonical ontology foundations (`phase-03-canonical-model-doctrine.md`, `phase-03-normative-index.md`) before deterministic runtime work.

## 2) Phase Overview
| Phase | Name | Goal | Architecture Status | Spec Completeness | Ready For Coding |
| ----- | ---- | ---- | ------------------- | ----------------- | ---------------- |
| 01 | Ingestion | Bring **organizational exhaust** safely into Cortex (substrate **and** connector depth) | **Substrate + checkpoint spine + Slack/GitHub/Linear/Notion/Calls deep slices + admin exhaust proof + verification gate + Step 15 live idempotency lock + Step 16 runtime correctness hardening** shipped (0–16) | Ready (Core Contracts Frozen) | **Phase 01 closure:** **Yes** |
| 02 | Raw Memory | Preserve trustworthy replay-safe raw organizational memory continuity (non-semantic) | **Steps 1–16 stabilization shipped** (verification + gates **G13–G16**, operational trust proof) | Ready With Caveats | **Phase 02 closure runtime:** **Yes** (operator verification + proof gates; organizational exhaust depth remains §2.5) |
| 03 | Canonicalization | Deterministic structural projection from raw memory to canonical primitives (mapping system + replay/provenance + verification split across **Steps 1–18**) | Architecture Defined | Strong (Doctrine + **18-stage program locked** — pre-runtime) | Almost |
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

- **Scope:** Default rule is Phases **03–10 Step 6** where a phase uses the legacy 6-step template. **Phase 03 exception:** Phase 03 runs **Steps 1–18** (granular canonical runtime program); **operator/admin closure + operational certification** must ship through **Steps 16–18** (control plane, stabilization/proof, closure certification)—see Phase 03 tracker rows. **Phase 02 exception:** Step **9** is the dedicated **Runtime Memory Control Plane**, Step **10** establishes baseline closure gate runtime, and Steps **11–16** complete stabilization/proof before final closure confidence. **Phase 01 exception:** substrate **operator closure** is Step **6**; **phase closure** requires Steps **7–16** (Step 16 is the final runtime-correctness hardening gate).
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
| 1 | Runtime contracts + invariants | Implemented in runtime verification: I1 raw payload immutability, I2 provenance reconstructability, I3 source identity+revision preservation, I4 replay lineage durability, I5 deterministic retrieval, I6 temporal ordering anchors; exposed in tenant/admin verification as `raw_memory_contracts`. | Strong | Yes |
| 2 | Persistence + provenance runtime model | Implemented runtime model: durable `raw_memory_lineage_index` table + migration backfill, transactional lineage upsert on every successful raw append (live/replay), replay lineage continuity persisted (`latest_replay_job_id`/`latest_replay_version`), and Step 2 verification checks exposed in tenant/admin verification as `raw_memory_persistence`. | Strong | Yes |
| 3 | Temporal continuity implementation | Implemented runtime model: durable `raw_memory_revision_index` + migration backfill, temporal revision-chain persistence with supersession linkage, deletion-observed visibility, deterministic ordering precedence (`provider_event_timestamp` -> `source_revision_key` -> `fetched_at` -> stable raw id), and Step 3 verification checks exposed as `raw_memory_temporal` with retrieval helpers (`list_revision_chain`, `latest_known_before_t`). | Strong | Yes |
| 4 | Replay equivalence + divergence implementation | Implemented runtime replay model: per-replay-job equivalence scan + divergence classification (`D0`-`D5`) with severity/closure metadata, blocking policy for forbidden classes (`D3`+), deterministic replay ordering checks, lineage mismatch detection (`D4`), expected-provider/schema divergence handling (`D1`/`D2`), and tenant/admin verification exposure as `raw_memory_replay`. | Strong | Yes |
| 5 | Query model implementation (anti-goal enforced) | Implemented runtime query model: deterministic supported evidence retrieval classes (`source`, `replay`, `audit`, `provenance`, `temporal`) via `/admin/tenants/{tenant_id}/cortex/memory/query`, anti-goal guardrails block semantic/graph/intelligence intents, and Step 5 conformance checks are enforced in tenant/admin verification as `raw_memory_query`. | Strong | Yes |
| 6 | Storage + retention implementation | Implemented runtime storage-retention model: durable `raw_memory_archive_catalog` + `raw_memory_retention_events` (with migration backfill), transactional archive-catalog writes on raw append, policy-driven retention apply path (`/admin/tenants/{tenant_id}/cortex/memory/retention/apply`) supporting dry-run and auditable actions, and Step 6 conformance checks exposed as `raw_memory_storage` in tenant/admin verification. | Strong | Yes |
| 7 | Failure/recovery implementation | Implemented runtime failure/recovery model: durable failure-case registry (`raw_memory_failure_cases`) and recovery validation ledger (`raw_memory_recovery_validations`), deterministic failure-class synchronization (corruption/lineage/replay divergence/replay interruption/archive corruption), repairable recovery validation workflow (`/admin/tenants/{tenant_id}/cortex/memory/recovery/validate`), failure visibility endpoint (`/admin/tenants/{tenant_id}/cortex/memory/failures`), and Step 7 conformance checks exposed as `raw_memory_failure_recovery` in tenant/admin verification. | Strong | Yes |
| 8 | Trust-state + API contract implementation | Implemented runtime trust contract: canonical trust annotation payload + gate tolerance decisions (G1-G7), continuity-gap contract shaping from active failure cases, persisted trust snapshots (`raw_memory_trust_state`) and transition events (`raw_memory_trust_transitions`), and operator/API visibility via `/admin/tenants/{tenant_id}/cortex/memory/trust-state` + verification block `raw_memory_trust`. | Strong | Yes |
| 9 | Runtime Memory Control Plane | Implemented runtime/operator control plane: aggregated memory truth API (`/admin/tenants/{tenant_id}/cortex/memory/control-plane`), step-9 verification contract (`raw_memory_control_plane`), replay/provenance/temporal/corruption inspectors, operator checklist + safe actions surface, and admin UI activation for Cortex Memory/Verification tabs backed by `AdminCortexMemoryPage`. | Strong | Yes |
| 10 | Phase closure trust gate | Implemented baseline binary closure enforcement: `raw_memory_phase_closure` gate evaluator (G1–G10), hard/soft/warn decision model, active blocking-flag closure deny rule, closure API (`/admin/tenants/{tenant_id}/cortex/memory/phase-closure`), verification integration, and operator-visible phase status (`open`/`closed`) in the Memory/Verification admin surface. | Strong | Yes |
| 11 | Progressive trust enforcement | Implemented runtime calibrated enforcement policy layer: trust-aware decision engine (`observe`/`progressive`/`strict`), deterministic `would_block` vs `blocked` semantics, catastrophic-only hard-block behavior in progressive mode, enforcement telemetry surfaced in control-plane + verification payload, and trust-aware replay/query route annotations (`enforcement` payload + runtime block on catastrophic state). | Strong | Yes |
| 12 | Unified verification semantics | Implemented canonical gate path (`raw_memory_verification_unified.py`): shared G1–G7 for trust annotations and closure, merged G8–G10, `phase02_verification_truth` + freshness/proof-quality payload on tenant verification, `raw_memory_verification_step12` contract checks, cache-hit stale proof-quality stamping, control-plane `verification_truth` surface, trust API requires `raw_memory_contracts` for G1 alignment with closure. | Strong | Yes |
| 13 | Replay divergence hardening | **Implemented:** exported divergence registry (`REPLAY_DIVERGENCE_CLASS_META`, `FORBIDDEN_DIVERGENCE_CLASSES`), **D5** when lineage-breaking replay coincides with active continuity-broken failure cases, `verify_phase02_step13_replay_divergence_hardening` + tenant verification payload `raw_memory_replay_hardening`, stabilization gate **G13** merged into phase closure, denial-path + D2/D3/D4/D5 matrix coverage in `test_step13_replay_divergence_hardening.py`. | Strong | Yes |
| 14 | Trust-signal hardening | **Implemented:** `infer_proof_quality` primary axis including **inferred** when trust G1–G7 slice diverges from closure; **`freshness.label`** (`fresh`/`stale`); stabilization gate **G14**; `verify_phase02_step14_trust_signal_hardening` + payload `raw_memory_trust_signal`; trust persistence enriched with `verification.proof_quality`/`verification.freshness`; control-plane **`health_overview.proof_quality_primary`** / **`verification_freshness`**; admin Memory + Verification UI surfaces; tests `test_step14_trust_signal.py`. | Strong | Yes |
| 15 | Critical integrity hardening | **Implemented:** read-only verifier `verify_phase02_step15_critical_integrity` cross-checks revision index ↔ raw fingerprints and lineage ↔ revision heads (trust-critical pointers); stabilization gate **G15** merged into canonical closure path; tenant `/cortex/ingestion/verification` exposes `raw_memory_critical_integrity`; control-plane **`health_overview`** + checklist surface integrity state; admin Memory UI shows critical pointer integrity; tests `test_step15_critical_integrity.py`. | Strong | Yes |
| 16 | Operational trust proof pass | **Implemented:** composite verifier `verify_phase02_step16_operational_trust_proof` (replay+divergence depth, runtime correctness + recovery, temporal continuity, critical integrity, trust signal, freshness coherence, replay proof artifacts); stabilization gate **G16** on canonical closure path; tenant verification exposes `raw_memory_operational_trust_proof`; control-plane checklist + **`health_overview`** operational trust fields; admin Memory UI tile; tests `test_step16_operational_trust_proof.py`. Phase **02** may be claimed operationally closed when tenant verification passes including **G16** (subject to organizational exhaust caveats in §2.5). | Strong | Yes |

### Missing / Incomplete
- Phase **02** organizational exhaust **depth** remains connector/workload-dependent (§2.5); closure gates prove **substrate + trust mechanics**, not omniscient provider coverage.

### Implementation Blockers
- No Phase **02** redesign blockers; Phase **03** runtime remains gated on mapping bundle registry + key appendix acceptance (`phase-03-implementation-readiness-audit.md`).

**Confidence:** High architecture confidence; Phase **02** operational trust proof path (**G16**) is enforceable in verification — continue soak for scale and connector exhaust expansion under §2.5.

---

### Phase 03 — Canonicalization (18-step deterministic canonical runtime program)
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Canonical ontology foundations | Freeze **structural** ontology slice + enums + non-semantic class graph (`phase-03-canonical-model-doctrine.md`, `phase-03-anti-goals-doctrine.md`). | Strong | No |
| 2 | Canonical object taxonomy | Lock entity/event/artifact/relationship/snapshot boundaries + examples (`phase-03-canonical-model-doctrine.md`). | Strong | No |
| 3 | Logical key doctrine + oracle vectors | Author per-class logical key derivation + idempotency tuples + test vectors (`phase-03-logical-key-doctrine.md`). | Strong | No |
| 4 | Deterministic mapping contracts | Freeze rule/table shapes, evidence grades (E0/E1), forbidden transforms (`phase-03-deterministic-canonicalization-doctrine.md`). | Strong | No |
| 5 | Mapping bundle registry + versioning | Implement registry process: bundle IDs, pins, compatibility lines, ownership, changelogs (`phase-03-mapping-bundle-registry.md`, `phase-03-mapping-system-doctrine.md`). | Strong | No |
| 6 | Canonical transform runtime | Deterministic mapping engine + **transform/field lineage** emission (`phase-03-transform-lineage-doctrine.md`). | Strong | No |
| 7 | Ambiguity persistence runtime | Ambiguity store + lifecycle + competing-rule behaviors (`phase-03-ambiguity-confidence-doctrine.md`). | Strong | No |
| 8 | Confidence propagation runtime | Wire confidence as structured metadata (no ranking semantics) (`phase-03-ambiguity-confidence-doctrine.md`). | Strong | No |
| 9 | Canonical identity continuity | Provider-scoped continuity + Phase 04 boundary hooks (`phase-03-identity-continuity-doctrine.md`). | Strong | No |
| 10 | Replay / rebuild / regeneration runtime | Pins, rebuild jobs, regeneration supersession, divergence **C0–C5** receipts (`phase-03-replay-versioning-doctrine.md`). | Strong | No |
| 11 | Provenance lineage runtime | Forward/reverse indexes, multi-merge provenance, conflicting evidence chains (`phase-03-provenance-traceability-doctrine.md`). | Strong | No |
| 12 | Temporal continuity + ordering runtime | Late evidence, supersession chains, rebuild sort order determinism (`phase-03-temporal-timeline-doctrine.md`). | Strong | No |
| 13 | Canonical query + retrieval runtime | Bounded graph/timeline/provenance queries + anti-goal guards (`phase-03-canonical-query-doctrine.md`). | Strong | No |
| 14 | Failure, degradation + remediation | Failure taxonomy + **policy-gated recovery** (`phase-03-failure-degradation-doctrine.md`, `phase-03-remediation-recovery-doctrine.md`). | Strong | No |
| 15 | Canonical verification engine | Invariant suite, CI vectors, divergence tooling (`phase-03-verification-engine-doctrine.md`, `phase-03-closure-gates-doctrine.md`). | Strong | No |
| 16 | Canonical control plane + admin | Mandatory operator surfaces **A–H** + logical IA (Overview→Recovery); deterministic proof—not semantic dashboards (`phase-03-canonical-control-plane-doctrine.md`). | Strong | No |
| 17 | Stabilization + proof pass | Soak, economics probes, large-tenant reconstruction drills—evidence recorded (`phase-03-implementation-readiness-audit.md`). | Strong | No |
| 18 | Closure + operational certification | **G-P03-01–G-P03-21** PASS + archived certification artifacts including **operator visibility gates** (`phase-03-closure-gates-doctrine.md`, `phase-03-canonical-control-plane-doctrine.md`). | Strong | No |

**Phase 03 closure rule:** Phase 03 is **not closed** until **operator-visible deterministic proof surfaces** satisfy **G-P03-15–G-P03-21** (no opaque canonical trust). Operator/control-plane requirements **co-evolve** with runtime stages per `03-canonical/implementation-plan.md` cross-cutting track—not only Step 16.

### Missing / Incomplete
- Runtime implementation across Steps **1–18** (spec sequencing complete; execution not started).
- **Governance infra execution:** registry lifecycle + pin enforcement + oracle manifests + CI promotion suites must exist as **running systems** — doctrines `phase-03-mapping-bundle-registry.md`, `phase-03-bundle-pinning-doctrine.md`, `phase-03-oracle-vectors-doctrine.md`, `phase-03-ci-deterministic-enforcement-doctrine.md` (see `phase-03-closure-gates-doctrine.md` §Existential deterministic infrastructure).
- Canonical query optimization at scale remains workload-dependent.

### Implementation Blockers
- **Rebuild economics / replay cost:** large-tenant reconstruction may exceed initial budgets—requires soak metrics (**Step 17**) before declaring production readiness.
- **Mapping evolution:** undeclared compatibility breaks risk **C5** divergence until registry governance is **operational** (**Step 05**) — see hardened registry doctrine.
- **Canonical drift:** mitigated by verification engine (**Step 15**) + **pinned bundles** (**Step 10**) + **CI fail-closed promotion** (`phase-03-ci-deterministic-enforcement-doctrine.md`).
- **Ambiguity explosion:** unresolved mapping backlog may spike—requires monitoring + mapping roadmap (**Steps 07–08**, **17**).
- **Version migration:** bundle bumps must ship explicit compatibility lines (`phase-03-mapping-bundle-registry.md`).
- **Logical key stability:** any change requires oracle vector updates (**Step 03**) + gate re-run (`phase-03-oracle-vectors-doctrine.md`).
- Phase 02 stabilization/trust surfaces may gate halt semantics for canonical materialization.

### Remaining operational risks (explicit)

See `phase-03-implementation-readiness-audit.md` §Operational risks — includes rebuild economics, mapping governance, drift, replay cost, large-tenant reconstruction, ambiguity explosion, version migration, key stability.

**Additional operator-trust risks (control-plane doctrine):**

- **Opaque rebuild drift** — divergence exists but not surfaced to operators (violates **G-P03-15**).
- **Hidden mapping invalidation** — bundle bumps leave stale canonical scopes invisible (**G-P03-19**).
- **Ambiguity explosion invisibility** — backlog grows without thresholds/alerts (**G-P03-18**).
- **Unverifiable canonical provenance** — object inspector cannot show lineage/bundle/rule receipts (**G-P03-16/G-P03-17**).
- **Operator-blind replay divergence** — regeneration jobs lack receipts / generation metadata (**G-P03-20**).

**Confidence:** **8 / 10** program readiness — doctrine + **implementation-grade sequencing** + **control-plane co-evolution model** locked; execution + economics + **operator proof surfaces** validation remain (**Steps 05–06 partial surfaces through 18**).

**Anti-goals (non-negotiable):** Phase 03 remains **structural, deterministic, provenance-safe, replay-safe** — not semantic reasoning, managerial interpretation, AI synthesis, graph cognition, or execution narratives (`phase-03-anti-goals-doctrine.md`).

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
- **Current goal:** Begin Phase **03** deterministic canonical runtime program per `DOCS/cortex/implementation/phased-roadmap.md` and Phase **03** normative docs; keep Phase **02** verification green in CI/admin.
- **Parallel:** migration flags and operator soak continue; Phase 01 closure criteria are already met.
- **Next planned implementation entry:** Phase **03 Step 1** (canonical ontology foundations — freeze primitives/taxonomy before mapping runtime).

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
