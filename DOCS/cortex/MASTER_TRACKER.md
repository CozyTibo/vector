# Cortex Master Tracker

## 1) Project Snapshot
- **Architecture maturity:** Core foundation defined across Phases 01-04 and 10; storage/queryability challenge pass added.
- **Ingestion vs exhaust (non‑negotiable distinction):** **Substrate** (runs, replay lanes, envelope validation, checkpoint storage, admin triggers, verification jobs) is **not** Phase 01 success. **Phase 01 success** = **full raw organizational exhaust** per `DOCS/cortex/01-ingestion/phase-01-organizational-exhaust-spec.md` (pagination, per-stream cursors, backfill + incremental, replay semantics, exit criteria). Do not treat “sync ran,” “scope_ping rows exist,” or “integration connected” as exhaust progress. Deep exhaust is tracked in **§2.5**, `organizational-exhaust-execution-track.md`, `connector-exhaust-matrix.md`, `exhaust_coverage_registry.py`, and admin raw aggregates.
- **Implementation stage:** Phase 01 Steps **0–16** = ingestion substrate + checkpoint spine + connector depth + admin exhaust proof + verification gate + live-lane logical idempotency lock + runtime correctness hardening — **Yes (Phase 01 complete)**.
- **Current focus:** Phase **04** Identity & Linking — **Step 22 (P04-22) shipped**: **`phase-04-closure-gates-doctrine.md`**; Alembic **`20260511_0068`** (**`cortex_org_certification_archives`**); **`vector.domains.cortex.identity.org_identity_certification_pack`** (deterministic pack + **`G-P04-CLOSE-MAP-01/02`** + **`G-P04-CLOSE-01`** closure matrix); canonical verification **`G-P04-CLOSE-01`** (**`hard_fail`**, runs after core gates via **`_canonical_verification_gate_results_core`** to avoid recursion); admin **`GET/POST .../cortex/identity/certification-pack`** family + archive list/detail; ontology **`ONTOLOGY_SCHEMA_VERSION` 41** + `identity_control_plane_surface_version` **6** + org certification pointer metadata; Cortex nav **Identity certification** (`/cortex/identity-certification`); tests **`test_phase04_step22_org_certification_pack.py`**. **Next (cross-phase):** Phase **05** Organizational Graph — Step **1** (graph continuity model) per roadmap, after Phase **04** program sign-off / soak. Phase **03** remains **Steps 1–18 complete** + Phase **3.5** continuity foundation.
- **Total phases:** 10.
- **Current blockers:** Phase 01 hard blockers cleared; remaining work is post-closure soak/scale confidence and later-phase architecture. (Cortex ingestion routing defaults **on**; use `CORTEX_CONNECTOR_MIGRATION_*=false` only to opt out.)
- **Next major milestone:** Phase **05** Step **1** — **organizational graph continuity model** (Phase **04** Steps **1–22** shipped through org certification archive + **G-P04-CLOSE-01** + operator/admin closure surfaces). Organizational exhaust depth (§2.5) remains the cross-phase execution track.

## 2) Phase Overview
| Phase | Name | Goal | Architecture Status | Spec Completeness | Ready For Coding |
| ----- | ---- | ---- | ------------------- | ----------------- | ---------------- |
| 01 | Ingestion | Bring **organizational exhaust** safely into Cortex (substrate **and** connector depth) | **Substrate + checkpoint spine + Slack/GitHub/Linear/Notion/Calls deep slices + admin exhaust proof + verification gate + Step 15 live idempotency lock + Step 16 runtime correctness hardening** shipped (0–16) | Ready (Core Contracts Frozen) | **Phase 01 closure:** **Yes** |
| 02 | Raw Memory | Preserve trustworthy replay-safe raw organizational memory continuity (non-semantic) | **Steps 1–16 stabilization shipped** (verification + gates **G13–G16**, operational trust proof) | Ready With Caveats | **Phase 02 closure runtime:** **Yes** (operator verification + proof gates; organizational exhaust depth remains §2.5) |
| 03 | Canonicalization | Deterministic structural projection from raw memory to canonical primitives (mapping system + replay/provenance + verification split across **Steps 1–18**) | **Steps 1–18 shipped:** Steps **1–17** as before + **Step 18** `canonical_certification_pack.py` (`CERTIFICATION_PACK_SCHEMA_VERSION`), Alembic **`20260508_0050`** (**`cortex_canonical_certification_archives`**), admin **`GET .../certification-pack`**, **`POST .../certification-pack/archive`**, **`GET .../certification-pack/archives`**, **`GET .../certification-pack/archives/{id}`**, merged ontology certification pointers + closure doctrine anchors, verification gate **G-P03-21**, Canonical UI certification route + nav; tests `test_phase03_step18_certification_pack.py`. Doctrine: `phase-03-closure-gates-doctrine.md`, `phase-03-canonical-control-plane-doctrine.md`. | Strong (Doctrine + **18-stage program locked**) | **Yes (Caveats)** — Phase **03** operator closure track **complete**; soak/scale + organizational exhaust caveats remain (§2.5 / §2.6) |
| 04 | Identity & Linking | Organizational continuity layer: org handles, link ledger, merge governance, replay-safe candidates vs authoritative semantics; **Execution Continuity Operator Console** (`phase-04-control-plane-doctrine.md`); **hostile mock continuity** fixtures (`phase-04-mock-data-strategy.md` + `mock_connectors` implementation) | **Architecture + 22-stage program** + **P04-01–P04-22 shipped** (through **org identity certification pack** + **`cortex_org_certification_archives`** + **G-P04-CLOSE-01** + economics + anchor backfill + operator console) + mock strategy (`04-identity/*`, `vector.domains.cortex.identity`) | Strong (program + closure doctrine **Shipped**) | **No** (phase) — **Steps 1–22:** **Yes** (operator program complete); organizational **exhaust** depth remains §2.5 |
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

- **Scope:** Default rule is Phases **03–10 Step 6** where a phase uses the legacy 6-step template. **Phase 03 exception:** Phase 03 runs **Steps 1–18** (granular canonical runtime program); **operator/admin closure + operational certification** must ship through **Steps 16–18** (control plane, stabilization/proof, closure certification)—see Phase 03 tracker rows. **Phase 04 exception:** Phase 04 runs **Steps 1–22** (organizational continuity program **P04-01–P04-22**); **operator/admin closure + certification** must ship through **Steps 17–22** (control plane, API, worker jobs, migrations/backfill, stabilization/economics, closure pack)—see Phase 04 tracker rows. **Phase 02 exception:** Step **9** is the dedicated **Runtime Memory Control Plane**, Step **10** establishes baseline closure gate runtime, and Steps **11–16** complete stabilization/proof before final closure confidence. **Phase 01 exception:** substrate **operator closure** is Step **6**; **phase closure** requires Steps **7–16** (Step 16 is the final runtime-correctness hardening gate).
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
- No Phase **02** redesign blockers; Phase **03** Steps **1–18** are shipped (mapping registry + transform + ambiguity + confidence + identity + replay jobs + provenance + temporal ordering + **bounded canonical query API** + **failure/remediation** + **canonical verification engine** + **canonical control plane aggregate** + **stabilization / economics proof pass** + **Step 18 certification pack + archive**). Phase **03** operator/admin closure artifacts are **enforceable in runtime** subject to organizational exhaust caveats (§2.5 / §2.6).

**Confidence:** High architecture confidence; Phase **02** operational trust proof path (**G16**) is enforceable in verification — continue soak for scale and connector exhaust expansion under §2.5.

---

### Phase 03 — Canonicalization (18-step deterministic canonical runtime program)
| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Canonical ontology foundations | **Implemented:** runtime `CanonicalLayerKind`, `CanonicalObjectKind`, `CanonicalStructuralEdgeKind`, frozen structural class graph, `build_phase03_step01_ontology_public_document`; admin **`GET /admin/tenants/{tenant_id}/cortex/canonical/ontology`**; Cortex **Canonical** UI; tests `test_phase03_step1_ontology.py`, `test_admin_cortex_canonical_step1.py`. Doctrine: `phase-03-canonical-model-doctrine.md`, `phase-03-anti-goals-doctrine.md`. *(Payload gains taxonomy fields in Step 2 + `ONTOLOGY_SCHEMA_VERSION` bump.)* | Strong | Yes |
| 2 | Canonical object taxonomy | **Implemented:** runtime `vector.domains.cortex.canonical.taxonomy` (`CanonicalStructuralRole`, family boundary text, per-kind structural role + exemplar ids); merged into `build_phase03_step01_ontology_public_document` (`taxonomy_families`, `kind_taxonomy`, `taxonomy_hard_rules`, enriched `object_kinds`); admin ontology JSON + Canonical UI; tests `test_phase03_step2_taxonomy.py`. Doctrine: `phase-03-canonical-model-doctrine.md`. | Strong | Yes |
| 3 | Logical key doctrine + oracle vectors | **Implemented:** runtime `logical_keys.py` (`LOGICAL_KEY_PROFILE_VERSION`, ordered idempotency tuple fields per `CanonicalObjectKind`, global rules); `oracle_manifest.py` (`ORACLE_MANIFEST_SCHEMA_VERSION`, frozen stub-bundle vectors covering mandatory oracle coverage categories incl. C3/C4/C5 drift detectors); merged logical-key section into `build_phase03_step01_ontology_public_document`; admin **`GET .../cortex/canonical/oracle-manifest`**; Cortex Canonical UI (logical keys + oracle table); tests `test_phase03_step3_*.py`. Doctrine: `phase-03-logical-key-doctrine.md`, `phase-03-oracle-vectors-doctrine.md`. | Strong | Yes |
| 4 | Deterministic mapping contracts | **Implemented:** runtime `mapping_contracts.py` (`MAPPING_CONTRACT_SCHEMA_VERSION`, `EvidenceGrade` E0/E1, determinism criteria, structural extraction vs semantic inference ban, allowed deterministic operation ids, forbidden anti-goals list, field emission posture, mapping versioning rules, frozen **mapping_table_row_shape** for bundle authoring); merged into `build_phase03_step01_ontology_public_document`; admin ontology JSON + Canonical UI; tests `test_phase03_step4_mapping_contracts.py`. Doctrine: `phase-03-deterministic-canonicalization-doctrine.md`. | Strong | Yes |
| 5 | Mapping bundle registry + versioning | **Implemented:** Postgres tables + Alembic **`20260508_0039`** (seed stub bundle id aligned with oracle manifest); ORM `CortexMappingBundle*` models; `build_tenant_mapping_registry_public_document`; admin **`GET .../cortex/canonical/mapping-registry`**; ontology merged registry pointer section (`mapping_registry_metadata.py`); Canonical UI registry panel; tests `test_phase03_step5_*`. Doctrine: `phase-03-mapping-bundle-registry.md`, `phase-03-mapping-system-doctrine.md`. | Strong | Yes |
| 6 | Canonical transform runtime | **Implemented:** deterministic stub routing + SHA-256 hashes + persisted materializations + per-field lineage (`transform_runtime.py`, `TRANSFORM_RUNTIME_SCHEMA_VERSION`), Alembic **`20260508_0040`**, admin **`POST .../transform/materialize`**, **`GET .../transform/lineage`**, ontology **`ONTOLOGY_SCHEMA_VERSION` 6** + Canonical UI panel; tests `test_phase03_step6_transform_runtime.py`. Doctrine: `phase-03-transform-lineage-doctrine.md`. | Strong | Yes |
| 7 | Ambiguity persistence runtime | **Implemented:** durable **`cortex_canonical_ambiguity_records`** + append-only **`cortex_canonical_ambiguity_lifecycle_events`** (Alembic **`20260508_0041`**), `ambiguity_runtime.py` (`AMBIGUITY_RUNTIME_SCHEMA_VERSION`), lifecycle statuses (`open` → superseded / `void`), operator aggregates (by status/class/connector), admin **`GET/POST .../canonical/ambiguity`** + **`GET .../{id}`** + **`POST .../{id}/lifecycle`**, ontology **`ONTOLOGY_SCHEMA_VERSION` 7** + Canonical UI; tests `test_phase03_step7_ambiguity_runtime.py`. Doctrine: `phase-03-ambiguity-confidence-doctrine.md`. | Strong | Yes |
| 8 | Confidence propagation runtime | **Implemented:** Phase 03 confidence taxonomy (`Phase03ConfidenceClass` + forbidden auto classes), **`confidence_runtime.py`** (`CONFIDENCE_PROPAGATION_SCHEMA_VERSION`), persisted **`confidence_class`** + **`confidence_metadata`** on each field-lineage row (Alembic **`20260508_0042`**), deterministic stub assignment in **`transform_runtime.py`**, per-materialization **`confidence_rollup`** in admin lineage payloads, **`GET .../canonical/confidence/summary`**, ontology frozen taxonomy + non-ranking semantics + Canonical UI; tests `test_phase03_step8_confidence.py`. Doctrine: `phase-03-ambiguity-confidence-doctrine.md`. | Strong | Yes |
| 9 | Canonical identity continuity | **Implemented:** **`cortex_canonical_identity_anchors`** (Alembic **`20260508_0043`**), UUIDv5 **`canonical_entity_id`** from tenant+bundle+kind+provider-identity hash, **`phase04_boundary_json`** defaults (`human_identity_resolution: phase_04_only`, `linkage_merge_authority: none`), upsert wired from **`transform_runtime.materialize_raw_record`**, lineage payloads include **`canonical_entity_id`** + **`phase04_boundary`**, admin list/detail routes, ontology **`ONTOLOGY_SCHEMA_VERSION` 9**; tests `test_phase03_step9_identity.py`. Doctrine: `phase-03-identity-continuity-doctrine.md`. | Strong | Yes |
| 10 | Replay / rebuild / regeneration runtime | **Implemented:** Alembic **`20260508_0044`** (**`cortex_canonical_replay_jobs`** + **`cortex_canonical_replay_job_receipts`** + **`last_replay_job_id`** on materializations), **`replay_runtime.execute_canonical_replay_job`** (pinned bundle, dry-run, rebuild vs regeneration, Phase 02 trust **C3** gate, undeclared bundle migration **C5** rejection when `source_bundle_id` set without compatibility edge, **C2**/`C4` receipts), admin **`POST .../replay-jobs/run`**, **`GET .../replay-jobs`**, **`GET .../replay-jobs/{job_id}`**, ontology replay taxonomy + routes (**`ONTOLOGY_SCHEMA_VERSION` 10**); tests `test_phase03_step10_replay.py`. Doctrine: `phase-03-replay-versioning-doctrine.md`. | Strong | Yes |
| 11 | Provenance lineage runtime | **Implemented:** Alembic **`20260508_0045`** (**`cortex_canonical_provenance_records`**), per-materialization envelope ( **`primary_raw_record_ids`**, **`rule_ids_involved`**, **`derivation_json`**, optional **`parent_materialization_id`**), forward index on **`(tenant_id, raw_record_id)`**, upsert on **`materialize_raw_record`**, admin provenance **GET** routes, ontology **`ONTOLOGY_SCHEMA_VERSION` 11** + UI; tests `test_phase03_step11_provenance.py`. **N:1 / many:many / explicit contestation** wiring deferred to later steps. Doctrine: `phase-03-provenance-traceability-doctrine.md`. | Strong | Yes |
| 12 | Temporal continuity + ordering runtime | **Implemented:** Alembic **`20260508_0046`** ( **`occurred_at` / `observed_at` / `canonical_processed_at` / `source_revision_key` / `temporal_ordering_key`** on **`cortex_canonical_transform_materializations`**; **`cortex_canonical_temporal_supersessions`**), **`temporal_runtime.py`** (`TEMPORAL_RUNTIME_SCHEMA_VERSION`, deterministic ordering key + supersession record + rebuild preview), transform **`materialize_raw_record`** persists anchors and appends supersession when replacing same scope, admin temporal **GET/POST** routes, ontology **`ONTOLOGY_SCHEMA_VERSION` 12** + UI; tests `test_phase03_step12_temporal.py`. Doctrine: `phase-03-temporal-timeline-doctrine.md`. | Strong | Yes |
| 13 | Canonical query + retrieval runtime | **Implemented:** **`canonical_query_runtime.py`** (`CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION`), admin **`POST .../cortex/canonical/query`**, anti-goal guardrails, ontology **`ONTOLOGY_SCHEMA_VERSION` 13** (superseded by Step 14 ontology bump); tests `test_phase03_step13_canonical_query.py`. Doctrine: `phase-03-canonical-query-doctrine.md`. | Strong | Yes |
| 14 | Failure, degradation + remediation | **Implemented:** Alembic **`20260508_0047`** (**`cortex_canonical_failure_cases`**, **`cortex_canonical_remediation_validations`**), **`failure_remediation_runtime.py`** (`FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION`), materialize error capture + replay job forbidden-divergence / execution-failed sync, admin **`GET .../canonical/failures`**, **`POST .../canonical/remediation/validate`** (scoped rebuild via replay job, ambiguity triage ack ledger, Phase 02 trust **blocked**), ontology **`ONTOLOGY_SCHEMA_VERSION` 14** + Canonical UI; tests `test_phase03_step14_failure_remediation.py`. Doctrine: `phase-03-failure-degradation-doctrine.md`, `phase-03-remediation-recovery-doctrine.md`. | Strong | Yes |
| 15 | Canonical verification engine | **Implemented:** **`canonical_verification_engine.py`** (`CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION`), Alembic **`20260508_0048`** (**`cortex_canonical_verification_runs`** ledger), deterministic gate suite (**G-P03-01** … **G-P03-10**; **G-P03-16** in Step **16**; **G-P03-17** in Step **17**), admin **`POST .../verification/run`** + **`GET .../verification/runs`**, ontology (**`ONTOLOGY_SCHEMA_VERSION` 17** cumulative) + Canonical UI; tests `test_phase03_step15_verification_engine.py`. Doctrine: `phase-03-verification-engine-doctrine.md`, `phase-03-closure-gates-doctrine.md`. | Strong | Yes |
| 16 | Canonical control plane + admin | **Implemented:** `canonical_control_plane.py` (`CANONICAL_CONTROL_PLANE_SCHEMA_VERSION`), admin **`GET .../cortex/canonical/control-plane`**, deterministic aggregate (health counts, inspectors A–H-shaped slices, certification-style checklist, safe actions, logical IA route hints), ontology **`ONTOLOGY_SCHEMA_VERSION` 17** cumulative + **`control_plane_metadata.py`**, verification gate **G-P03-16**, Canonical UI **control-plane** route + ontology cross-link; tests `test_phase03_step16_control_plane.py` + admin HTTP test. Doctrine: `phase-03-canonical-control-plane-doctrine.md`. | Strong | Yes |
| 17 | Stabilization + proof pass | **Implemented:** `canonical_stabilization_proof.py` (`STABILIZATION_PROOF_SCHEMA_VERSION`), deterministic substrate/replay/verification/ambiguity probes + hard/warn checklist, Alembic **`20260508_0049`** (**`cortex_canonical_stabilization_proof_runs`**), admin **`GET/POST .../stabilization-proof`**, **`GET .../stabilization-proof/runs`**, ontology **`stabilization_proof_metadata.py`** + readiness audit anchor, verification gate **G-P03-17**, Canonical UI stabilization route + nav; tests `test_phase03_step17_stabilization_proof.py` + admin HTTP tests. Doctrine: `phase-03-implementation-readiness-audit.md`. | Strong | Yes |
| 18 | Closure + operational certification | **Implemented:** deterministic certification pack builder (`canonical_certification_pack.py`, **`CERTIFICATION_PACK_SCHEMA_VERSION`**), closure gate matrix **G-P03-14–G-P03-21** (doctrine **G-P03-17** lineage row is operator-audited sample; engine **G-P03-17** remains stabilization contract), structural verifier **`verify_phase03_step18_certification_pack_contract`**, persisted archives (**`cortex_canonical_certification_archives`** / Alembic **`20260508_0050`**), admin **`GET/POST .../certification-pack`** family, verification gate **G-P03-21**, ontology **`ONTOLOGY_SCHEMA_VERSION` 18** + certification route metadata, Canonical UI certification page + cross-links; tests **`test_phase03_step18_certification_pack.py`**. Doctrine: **`phase-03-closure-gates-doctrine.md`**, **`phase-03-canonical-control-plane-doctrine.md`**. | Strong | Yes |

**Phase 03 closure rule:** Phase 03 is **not closed** until **operator-visible deterministic proof surfaces** satisfy **G-P03-15–G-P03-21** (no opaque canonical trust). Operator/control-plane requirements **co-evolve** with runtime stages per `03-canonical/implementation-plan.md` cross-cutting track—not only Step 16.

### Missing / Incomplete
- Runtime implementation **Step 18** only (Steps **1–17** ontology through **stabilization proof** + prior control plane + verification engine + failure/remediation/query/temporal/provenance/replay/identity/confidence/ambiguity/transform/registry surfaces shipped).
- **Governance infra execution:** registry lifecycle + pin enforcement + oracle manifests + CI promotion suites must exist as **running systems** — doctrines `phase-03-mapping-bundle-registry.md`, `phase-03-bundle-pinning-doctrine.md`, `phase-03-oracle-vectors-doctrine.md`, `phase-03-ci-deterministic-enforcement-doctrine.md` (see `phase-03-closure-gates-doctrine.md` §Existential deterministic infrastructure).
- Canonical query optimization at scale remains workload-dependent.

### Implementation Blockers
- **Rebuild economics / replay cost:** large-tenant reconstruction may exceed initial budgets—operator **`stabilization-proof`** probes record substrate/replay scope metrics; production soak remains workload-dependent (**Step 18** certification).
- **Mapping evolution:** undeclared compatibility breaks risk **C5** divergence — mitigated by registry tables + pins (**Step 05** shipped); promotion CI coupling remains **Step 18** closure scope.
- **Canonical drift:** mitigated by verification engine (**Step 15**) + **pinned bundles** + **replay job receipts** (**Step 10**) + **CI fail-closed promotion** (`phase-03-ci-deterministic-enforcement-doctrine.md`).
- **Ambiguity explosion:** unresolved mapping backlog may spike—requires monitoring + mapping roadmap (**Step 17**); Steps **07–08** persist ambiguity rows + attach **non-ranking** confidence metadata to lineage for operator rollups.
- **Version migration:** bundle bumps must ship explicit compatibility lines (`phase-03-mapping-bundle-registry.md`).
- **Logical key stability:** any change requires oracle vector updates (**Step 03**) + gate re-run (`phase-03-oracle-vectors-doctrine.md`).
- Phase 02 stabilization/trust surfaces may gate halt semantics for canonical materialization.
- ~~Temporal ordering / rebuild sort determinism~~ **Mitigated (Step 12 core):** persisted **`temporal_ordering_key`** + supersession ledger + rebuild preview API + lineage listing ordered by temporal key.

### Remaining operational risks (explicit)

See `phase-03-implementation-readiness-audit.md` §Operational risks — includes rebuild economics, mapping governance, drift, replay cost, large-tenant reconstruction, ambiguity explosion, version migration, key stability.

**Additional operator-trust risks (control-plane doctrine):**

- **Opaque rebuild drift** — divergence exists but not surfaced to operators (violates **G-P03-15**).
- **Hidden mapping invalidation** — bundle bumps leave stale canonical scopes invisible (**G-P03-19**).
- **Ambiguity explosion invisibility** — backlog grows without thresholds/alerts (**G-P03-18**).
- ~~**Unverifiable canonical provenance** — object inspector cannot show lineage/bundle/rule receipts (**G-P03-16/G-P03-17**).~~ **Partially mitigated (Step 11 core):** provenance admin routes + per-mat envelope (`rule_ids_involved`, `derivation_json`, raw multiset) — rich object inspector UI remains **Step 16** scope.
- ~~**Operator-blind replay divergence** — regeneration jobs lack receipts / generation metadata (**G-P03-20**).~~ **Mitigated (Step 10 core):** canonical replay jobs emit per-raw **C0–C5** receipts + job summary; operator/admin surfaces list/detail + Canonical UI run panel.

**Confidence:** **8 / 10** program readiness — doctrine + **implementation-grade sequencing** + **control-plane co-evolution model** locked; execution + economics + **operator proof surfaces** validation remain (**Steps 14–18**); Steps **07–13** add ambiguity durability + lineage confidence + **identity anchors** + **replay jobs** + **provenance forward/reverse indexes** + **temporal ordering keys / supersession ledger** + **operator canonical query surface** with explicit Phase **04** handoff posture on identity.

**Anti-goals (non-negotiable):** Phase 03 remains **structural, deterministic, provenance-safe, replay-safe** — not semantic reasoning, managerial interpretation, AI synthesis, graph cognition, or execution narratives (`phase-03-anti-goals-doctrine.md`).

---

### Phase 04 — Identity & Linking (22-step organizational continuity program)

**Normative docs:** `DOCS/cortex/04-identity/phase-04-architecture-identity-linking-doctrine.md`, `phase-04-implementation-plan.md` (stages **P04-01–P04-22** in §4), `phase-04-normative-index.md` (**§Program freeze**), **`phase-04-anti-goals-doctrine.md`**, **`phase-04-topology-vs-meaning-doctrine.md`** (P04-02), **`phase-04-control-plane-doctrine.md`** (Execution Continuity Operator Console), **`phase-04-mock-data-strategy.md`** (hostile continuity mock/fixtures for dev + CI). **Sequencing authority:** `phase-04-implementation-plan.md` §4 — each tracker Step **#** maps **1:1** to **P04-{NN}**.

**Phase 04 exception (terminal closure):** Phase 04 runs **Steps 1–22** (doctrine-first boundary through certification pack). Operator/admin closure + operational certification ship through **Steps 17–22** — **Steps 17–18** deliver the **Execution Continuity Operator Console** (`phase-04-control-plane-doctrine.md`: tables-first, evidence-first, no graph theater), then worker jobs, migrations/backfill, stabilization/economics, closure pack — mirroring Phase 03’s “late steps = proof + closure” pattern; see **Terminal step — admin & operator closure** above.

| Step # | Step | Description | Spec Accuracy | Implemented |
| ------ | ---- | ----------- | ------------- | ----------- |
| 1 | Normative index + program freeze | **Implemented:** `phase-04-normative-index.md` §Program freeze (**`PHASE04_PROGRAM_FREEZE_VERSION` 1**), expanded vocabulary, doctrine hierarchy; **`phase-04-anti-goals-doctrine.md`**; package **`vector.domains.cortex.identity`** with **`normative.PHASE04_PROGRAM_FREEZE_VERSION`**; automated contract tests **`test_phase04_step01_normative_freeze.py`**. **Maps P04-01.** | Strong | Yes |
| 2 | Topology vs meaning boundary | **Implemented:** `phase-04-topology-vs-meaning-doctrine.md` (**INV-P04-TOPO-01**–**05**); `vector.domains.cortex.identity.boundary_checks` (`validate_org_meaning_link_payload`, `verify_topology_meaning_boundary_static`, `validate_org_link_type_not_topology` for ledger `link_type`); **G-P04-08** gate in `run_canonical_verification`; cumulative ontology / verification metadata through **Step 17** (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests `test_phase04_step02_boundary_checks.py`. **Maps P04-02.** | Strong | Yes |
| 3 | Org handle + org entity doctrine | **Implemented:** org-scoped handles (deterministic ids, kinds, lifecycle fields)—not Phase 03 canonical row ids; `phase-04-org-entity-and-handle-doctrine.md`; ORM + Alembic **`cortex_org_entities`** (**`20260509_0051`**); `vector.domains.cortex.identity.org_entities` (`upsert_org_entity`, `list_org_entities`, `get_org_entity`, **G-P04-ORG-01** static gate in `run_canonical_verification`); admin **`GET /admin/tenants/{tenant_id}/cortex/identity/entities`** + detail; org-entity ontology pointer section; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests `test_phase04_step03_org_entities.py`. **Maps P04-03.** | Strong | Yes |
| 4 | Link ledger doctrine | **Implemented:** typed authoritative links between org entities; `phase-04-link-ledger-doctrine.md`; ORM + Alembic **`cortex_org_links`** (**`20260509_0052`**, CHECK evidence-or-rule); `vector.domains.cortex.identity.link_ledger` (`append_authoritative_org_link`, `list_org_links`, `get_org_link`, temporal overlap helpers); verification **G-P04-LINK-01** (static) + **G-P04-06** (persisted rows); admin **`GET /admin/tenants/{tenant_id}/cortex/identity/links`** + detail; link-ledger ontology pointer section; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests `test_phase04_step04_link_ledger.py`. **Maps P04-04.** | Strong | Yes |
| 5 | Candidate vs authoritative linkage | **Implemented:** `phase-04-candidate-vs-authoritative-linkage-doctrine.md`; Alembic **`20260509_0053`** (**`cortex_org_link_candidate_batches`**, **`cortex_org_link_candidates`**, **`cortex_org_link_promotion_policies`**, link promotion FKs + CHECK pairing); `candidate_generation` (`regenerate_link_candidates`, `compute_candidate_set_sha256`, static **G-P04-04**/**G-P04-05**), `authoritative_writer` (`create_promotion_policy`, `promote_candidate_to_authoritative_link`); Celery **`app.tasks.cortex_org_link_jobs`** (**`vector.cortex.identity.regenerate_link_candidates`**, **`replay_authoritative_links`**); verification **G-P04-CAND-01** + **G-P04-04** + **G-P04-05**; admin **`GET .../link-candidates`** + optional **`link_authority`** on links list; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step05_candidate_authoritative.py`**. **Maps P04-05.** | Strong | Yes |
| 6 | Merge governance doctrine | **Implemented:** `phase-04-merge-governance-doctrine.md`; Alembic **`20260509_0054`** (**`cortex_org_merge_policies`**, **`cortex_org_merges`** + CHECK human dual evidence + operator + compensating **`supersedes_merge_id`** + team/service evidence floor); `merge_governance` (`create_merge_policy`, `append_org_merge`, `list_org_merges`); verification **G-P04-MRG-01** (static) + **G-P04-01** (persisted human merge completeness) + **G-P04-13** (compensating chain + append-only contract); admin **`GET/POST .../cortex/identity/merges`**; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step06_merge_governance.py`**. **Maps P04-06.** | Strong | Yes |
| 7 | Hint / inferred / prohibited link classes | **Implemented:** `phase-04-hint-and-prohibited-link-doctrine.md`; Alembic **`20260510_0055`** (**`cortex_org_links.link_class`**, CHECK allowed values + non-truth **`link_authority='non_authoritative'`**); `link_classes` (`OrgLinkClass`, merge-closure helper) + `link_ledger` (`append_non_truth_org_link`, hint bucket list, hash / overlap filters); verification **G-P04-02** (static whitelist) + **G-P04-HINT-01** (persisted authority-plane audit); admin **`GET .../links/hints`** + **`link_class`** query on links list; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step07_hint_links.py`**. **Maps P04-07.** | Strong | Yes |
| 8 | Temporal validity + revocation | **Implemented:** `phase-04-temporal-validity-and-revocation-doctrine.md`; Alembic **`20260510_0056`** (**`ck_cortex_org_links_valid_half_open`**); `org_link_temporal` (**half-open axis**, strip dict) + `link_ledger` (**`assert_org_link_validity_half_open`** on append paths, **`list_authoritative_temporal_overlap_violations_for_tenant`**, **`list_org_link_temporal_timeline`**); verification **G-P04-TMP-01** (static + persisted overlap) + **G-P04-11** (tombstone contract); admin **`GET .../cortex/identity/links/timeline`**; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step08_temporal.py`**. **Maps P04-08.** | Strong | Yes |
| 9 | Bundle + cross-bundle equivalence | **Implemented:** `phase-04-cross-bundle-equivalence-doctrine.md`; Alembic **`20260510_0057`** (**`cortex_bundle_equivalence_declarations`**, ordered-pair **`CHECK`**, **`replay_ordinal`**, partial unique active pair, FK to **`cortex_mapping_bundles`**); seed bundle **`bundle.phase04.step09.equivalence.b.v1`**; `bundle_equivalence` (**append/list**, **`cross_bundle_edge_bundles_from_link_metadata`**, **`has_active_bundle_equivalence_declaration`**); verification **G-P04-BNDL-01** / **G-P04-03** / **G-P04-14**; admin **`GET/POST .../cortex/identity/bundle-equivalence`**; `bundle_continuity_semantics.bundle_equivalence_declaration_surface`; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step09_bundle_equivalence.py`**. **Maps P04-09.** | Strong | Yes |
| 10 | Continuity replay + regeneration | **Implemented:** `phase-04-continuity-replay-doctrine.md`; Alembic **`20260510_0058`** (**`cortex_org_link_replay_jobs`**, **`cortex_org_link_replay_job_receipts`**); `org_link_replay_runtime` (**`execute_org_link_replay_job`**, L-class receipts, **`verify_org_link_replay_rpl01_static`**); verification **G-P04-RPL-01**; admin **`GET/POST .../cortex/identity/replay-jobs`**; Celery **`vector.cortex.identity.run_org_link_replay_job`**; `org_link_replay_metadata` merged into ontology; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step10_org_link_replay.py`**. **Maps P04-10.** | Strong | Yes |
| 11 | Linkage rule engine + versioning | **Implemented:** `phase-04-linkage-rule-engine-doctrine.md`; Alembic **`20260510_0059`** (**`cortex_link_rule_versions`**, partial unique active semantic per tenant; **`cortex_org_link_candidate_batches.link_rule_version_id`** FK); `linkage_rules` (**`create_link_rule_version`**, **`compute_rules_manifest_sha256`**, **`verify_link_rule_rule01_static`**); verification **G-P04-RULE-01**; admin **`GET/POST .../cortex/identity/link-rule-versions`**; `candidate_generation` / `org_link_replay_runtime` pin batches when an active rule row matches `pinned_rule_version`; `link_rule_version_metadata` merged into ontology; cumulative ontology through Step 17 (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step11_linkage_rules.py`**. **Maps P04-11.** | Strong | Yes |
| 12 | Execution primitive persistence | **Implemented:** `phase-04-execution-primitive-persistence-doctrine.md`; Alembic **`20260510_0060`** (**`cortex_org_primitive_instances`**, evidence array CHECK, **`uq_cortex_org_primitive_instances_tenant_primitive_key`**); `execution_primitives` (**`append_org_primitive_instance`**, list/detail helpers, **`verify_gp04_09_primitive_evidence_discipline_static`**, **`verify_gp04_prim01_static_evidence_contract`**); verification **G-P04-09** + **G-P04-PRIM-01**; admin **`GET/POST .../cortex/identity/primitive-instances`**; `execution_primitive_persistence_metadata` merged into ontology; tests **`test_phase04_step12_execution_primitives.py`**. **Maps P04-12.** | Strong | Yes |
| 13 | Graph boundary + projection export | **Implemented:** `phase-04-graph-boundary-doctrine.md` + `phase-04-graph-projection-export-doctrine.md`; `projection_export` (**`build_org_graph_projection_v1`**, **`build_org_graph_projection_export_document`**, canonical JSON **SHA-256**); verification **G-P04-10** + **G-P04-EXP-01**; admin **`GET .../cortex/identity/graph-projection`**; `graph_projection_export_metadata` merged into ontology (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step13_graph_projection.py`**. **Maps P04-13.** | Strong | Yes |
| 14 | Ambiguity + multiplicity (org scope) | **Implemented:** `phase-04-ambiguity-multiple-persona-doctrine.md`; Alembic **`20260510_0061`** (**`cortex_org_ambiguity_records`**, CHECK ≥2 involved ids, partial unique open **`subject_key`**); `org_ambiguity` (**`append_org_ambiguity_record`**, list/detail, integrity scan); verification **G-P04-AMB-01** + **G-P04-12** (warn-only pressure); admin **`GET/POST .../cortex/identity/org-ambiguities`**; `org_ambiguity_metadata` merged into ontology (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step14_org_ambiguity.py`**. **Maps P04-14.** | Strong | Yes |
| 15 | Identity verification engine extension | **Implemented:** `phase-04-verification-gates-doctrine.md`; **`cortex_org_verification_runs`** (Alembic **`20260510_0062`**); **`vector.domains.cortex.identity.verification`** (`run_org_identity_verification`, `phase04_identity_gate_slice`, **`PHASE04_NORMATIVE_NUMBERED_GATE_IDS`**); canonical runner **G-P04-VER-01** (metadata + normative tuple coherence); admin **`POST .../cortex/identity/verification/run`** + **`GET .../cortex/identity/verification/runs`**; `org_verification_metadata` merged into ontology (cumulative with Steps **17–18**); tests **`test_phase04_step15_org_identity_verification.py`**. Operator-console gates **G-P04-22–G-P04-26** ship Step **18**. **Maps P04-15.** | Strong | Yes |
| 16 | Failure + remediation (org scope) | **Implemented:** `phase-04-failure-remediation-doctrine.md`; Alembic **`20260510_0063`** (**`cortex_org_failure_cases`**, **`cortex_org_remediation_validations`**); **`vector.domains.cortex.identity.failure_remediation`** (`recompute_org_derived_failure_cases`, `sync_org_failure_cases`, `validate_org_remediation`, **G-P04-19** in `run_canonical_verification`); derived classes **org_link_replay_job_failed** / **org_link_replay_missing_receipts** / **org_link_temporal_overlap**; `org_link_replay_runtime` records failures on job exception; admin **`GET .../cortex/identity/failures`** + **`POST .../cortex/identity/remediation/validate`**; `org_failure_remediation_metadata` merged into ontology (**`ONTOLOGY_SCHEMA_VERSION` 36**); tests **`test_phase04_step16_org_failure_remediation.py`**. **Maps P04-16.** | Strong | Yes |
| 17 | Control plane aggregate (org continuity) | **Implemented:** `phase-04-control-plane-doctrine.md` §§5–7, **Appendix A**; **`vector.domains.cortex.identity.control_plane`** (`build_identity_control_plane`, **identity_control_plane_v1**); canonical verification **G-P04-18** / **G-P04-21**; admin **`GET .../cortex/identity/control-plane`**; `identity_control_plane_metadata` merged into ontology (**`ONTOLOGY_SCHEMA_VERSION` 36**); frontend Cortex **Identity** tab (`/cortex/entity-resolution`); tests **`test_phase04_step17_identity_control_plane.py`**. **Maps P04-17.** | Strong | Yes |
| 18 | API routes (internal/admin) | **Implemented:** `phase-04-control-plane-doctrine.md` §§15–16 + Appendix B; Alembic **`20260510_0064`** (**`cortex_org_identity_console_audits`**); **`operator_console`** (list-row builders, merge-queue mutations, **`IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE`**), **`operator_console_verification`** (**G-P04-22**–**G-P04-26**), **`projection_export.build_org_graph_projection_preview_metadata`**; admin **handles** / **merge-queue** (+ POST actions) / **ambiguity-queue** / **primitives** / **projection-preview** / **link revoke** + §9.2 filters on **links** list; **`CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION` 2**; ontology **`ONTOLOGY_SCHEMA_VERSION` 37** + route metadata surface bumps; OpenAPI **`DOCS/cortex/04-identity/openapi/identity_admin.yaml`**; tests **`test_phase04_step18_operator_console.py`**. **Maps P04-18.** | Strong | Yes |
| 19 | Celery / worker jobs | **Implemented:** Alembic **`20260510_0065`**; **`worker_dispatch`** (tenant-bound **`GET .../identity/worker-tasks/{celery_task_id}`**); **`POST .../identity/replay-jobs/enqueue`**, legacy **`regenerate-async`** / **`authoritative-replay-async`** with **`cortex_identity_celery_dispatches`**; **`POST .../identity/projection-export/run`** enqueues **`graph_projection_export`** replay job; **`run_org_link_replay_job_task`** `job_id` path + `org_link_replay_runtime` **`ORG_LINK_REPLAY_SCHEMA_VERSION` 2**; ontology **38**; tests **`test_phase04_step19_worker_visibility.py`**. **Maps P04-19.** | Strong | Yes |
| 20 | Migration + backfill strategy | **Implemented:** **`phase-04-backfill-doctrine.md`**; Alembic **`20260511_0066`** (**`cortex_org_identity_backfill_runs`**); **`vector.domains.cortex.identity.backfill`** (bounded anchor scan → org entities, **`ANCHOR_BACKFILL_LANE`**, dry-run + audit); verification **`G-P04-BF-01`**; admin **`POST .../identity/backfill/from-canonical-anchors`**, **`GET .../identity/backfill/runs`**; mock **`continuity_fixture`** + **`phase04_continuity_fixtures`** + **`validate_mock_dataset.py`** Phase 04 checks; ontology **39** / control-plane surface **4**; tests **`test_phase04_step20_anchor_backfill.py`**, **`test_phase04_mock_continuity_fixture.py`**. **Maps P04-20.** | Strong | Yes |
| 21 | Stabilization + economics pass | **Implemented:** **`phase-04-readiness-audit.md`**; Alembic **`20260511_0067`**; **`vector.domains.cortex.identity.readiness_economics`** + **`readiness_economics_metadata`**; verification **`G-P04-ECO-01`**; admin **`GET .../cortex/identity/readiness-economics`**; Identity overview economics warnings panel; ontology **40** / control-plane surface **5**; tests **`test_phase04_step21_readiness_economics.py`**. **Maps P04-21.** | Strong | Yes |
| 22 | Closure + certification pack | **Implemented:** **`phase-04-closure-gates-doctrine.md`**; Alembic **`20260511_0068`** (**`cortex_org_certification_archives`**); **`vector.domains.cortex.identity.org_identity_certification_pack`** + metadata; verification **`G-P04-CLOSE-01`** (closure matrix **G-P04-CLOSE-MAP-01/02** + contract row); admin **`GET/POST .../cortex/identity/certification-pack`** + archives list/detail; **`_canonical_verification_gate_results_core`** split to avoid pack/engine recursion; ontology **41** / control-plane surface **6**; frontend **`identity-certification`** route; tests **`test_phase04_step22_org_certification_pack.py`**. **Maps P04-22.** | Strong | Yes |

### Missing / Incomplete
- **Steps 1–22 (P04-01–P04-22) complete** — through **org identity certification** (**G-P04-CLOSE-01**) + **readiness economics** (**G-P04-ECO-01**) + **anchor backfill** (**G-P04-BF-01**) + **continuity_fixture** mock sidecar + **worker job enqueue + poll** + **operator console §15 HTTP routes** + **G-P04-22**–**G-P04-26** + **identity control-plane aggregate** + **G-P04-18**/**G-P04-21** + **org failure/remediation** + **G-P04-19** + **org verification slice** + **org ambiguity** + **OrgGraphProjectionV1** + prior identity / merge / link / bundle-equivalence / replay / rule-version / primitive surfaces.
- Phase **04** normative doctrine inventory is **complete** for the locked 22-stage program (**exceptions:** optional future doctrines listed in `phase-04-implementation-plan.md` §5 “Likely additional”); hostile mock **implementation** in `mock_connectors` remains **expandable** for stress scenarios (`nexora_p04_hostile_baseline`, mock strategy §17).
- Mock tenant must adopt **hostile continuity** scenarios (`phase-04-mock-data-strategy.md`): multi-tool identity collisions, ambiguity/merge pressure, L-class replay drift — **not** clean-demo-only Nexora for Phase 04 validation. **Progress:** generated datasets now embed **`continuity_fixture`** + CI validation for minimum **Alex** collision slice (`validate_mock_dataset.py`); deeper `P04MD-*` injectors remain expandable in **`company_generator`** overlays.
- Phase 04 **async export job** is wired via **`POST .../projection-export/run`** → queued **`graph_projection_export`** org link replay job + Celery (**P04-19**); worker must run to materialize completion receipts off the hot path.
- Identity / linkage **certified-slice** economics probes are shipped (Step **21**); **hostile-mock stress at production scale** remains optional soak work (`nexora_p04_hostile_baseline`, mock strategy §17).

### Implementation Blockers
- Phase **05** kickoff depends on graph doctrine authorship + Phase **04** soak confidence; Phase **04** numbered program (**P04-01–P04-22**) is **shipped** in runtime + admin surfaces.
- Deeper hostile-mock stress remains optional soak beyond bounded probes (economics Step **21**, certification Step **22**).

**Confidence:** **Program 9 / 10** (sequencing + gates + boundaries); **execution readiness** follows doctrine freeze + schema sign-off (**~7 / 10** until then).

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
- **Current goal:** Phase **05** organizational graph — begin **Step 1** (graph continuity model) per `DOCS/cortex/MASTER_TRACKER.md` Phase 05 table; keep Phase **02** verification green in CI/admin.
- **Parallel:** migration flags and operator soak continue; Phase 01 closure criteria are already met.
- **Next planned implementation entry:** Phase **05** graph layer (continuity + traversal contracts) after Phase **04** operator sign-off on hostile-mock / exhaust caveats as needed.

## 5) Implementation Readiness
| Phase | Architecture | Verification | Ready For Coding |
| ----- | ------------ | ------------ | ---------------- |
| 01 | **Complete through Step 15:** substrate + deep connector exhaust + admin proof + verification gate + live logical idempotency lock | Step 5/6 + Step 7–15 test coverage (integration-marked suites + admin/API verification gates) | **Yes (Phase 01 closed)** |
| 02 | Complete | Complete (Caveats) | Yes (Caveats) |
| 03 | Steps **1–11** runtime shipped (transform + lineage confidence + ambiguity + identity + replay + provenance + admin) | Partial | **Yes (Caveats)** |
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
