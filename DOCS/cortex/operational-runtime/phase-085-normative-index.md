# Phase 08.5 — Normative index (Continuous Execution Substrate Program)

**Status:** **Strong** (program locked; implementation **Partial**).  
**Role:** operational maturation between **Phase 08 SIL** and **Phase 09 products**.  
**Program id:** **CESP** · **Freeze version:** **PHASE085_PROGRAM_FREEZE_VERSION** `1` (program lock at Step 1; constitutional freeze target Step 36).  
**Normative tree:** `DOCS/cortex/operational-runtime/`.

**Changelog:** [`PHASE085_CONSTITUTIONAL_CHANGELOG.md`](./PHASE085_CONSTITUTIONAL_CHANGELOG.md).  
**Sequencing:** [`phase-085-implementation-sequencing-plan.md`](./phase-085-implementation-sequencing-plan.md).  
**Gaps:** [`cesp-spec-gap-matrix.md`](./cesp-spec-gap-matrix.md).  
**Executive brief:** [`PHASE085_EXECUTIVE_BRIEF.md`](./PHASE085_EXECUTIVE_BRIEF.md).

---

## Program freeze (P085-01 / CESp-01)

| Field | Value |
| ----- | ----- |
| **PHASE085_PROGRAM_FREEZE_VERSION** | `1` — MUST match runtime constant `vector.domains.cortex.operational_runtime.normative.PHASE085_PROGRAM_FREEZE_VERSION`. |
| **PHASE085_STEP_PROGRAM_COUNT** | `36` |
| **PHASE085_PROGRAM_ID** | `CESP` |
| **Primary gate** | **G-P085-CESP-01** (`verify_gp085_cesp01_program_freeze_static`) |
| **Admin catalog** | `GET /admin/catalog/cortex/operational-runtime/program` |

---

## Constitutional sentence

**Phase 08.5** makes the Cortex **execution substrate operationally alive**: it enforces **autonomous progression**, **substrate density growth**, **replay-safe self-healing**, and **truthful operator visibility** across ingestion → synthesis — without weakening Phase **05–08** legality, replay, or degradation law.

**NOT:** new cognition, chat, product workflows, or governance rewrites.  
**IS:** continuity, density, recovery, maturity, cockpit, economics, Phase **09** readiness certification.

---

## Upstream / downstream

| Boundary | Law |
| -------- | --- |
| **Phase 08** | SIL artifacts, synthesis legality, publication epochs — **immutable** consumer contract |
| **Phase 08.5** | May extend substrate pipeline orchestration, completeness projections, admin — **MUST NOT** weaken **G-P08-*** |
| **Phase 09** | **Blocked** until **G-P085-CLOSE-01** + **OPERATIONAL_ALIVE** certification |
| **Phase 10** | Cockpit surfaces register under admin shell |

---

## Freeze bundles (FF-P085-0..6)

| Bundle | Steps | Intent |
| ------ | ----- | ------ |
| **FF-P085-0** | 1–4 | Index, endgoal, boundaries, gap discipline |
| **FF-P085-1** | 5–9 | Substrate continuity + recovery law |
| **FF-P085-2** | 10–13 | Graph density & continuity expansion |
| **FF-P085-3** | 14–17 | Traversal completion automation |
| **FF-P085-4** | 18–23 | TCRE + retrieval density maturity |
| **FF-P085-5** | 24–29 | Synthesis activation + operational health |
| **FF-P085-6** | 30–36 | Admin cockpit + economics + certification |

---

## Step program ↔ doctrine (1:1)

| Step | Title | Primary normative file(s) | Gate(s) |
| ---- | ----- | ------------------------- | ------- |
| 1 | Normative index + program freeze | **This file** | **CESP-01** |
| 2 | Endgoal + fake-green prohibition | [`phase-085-endgoal-doctrine.md`](./phase-085-endgoal-doctrine.md) | **G-P085-ANTI-IDLE-01** |
| 3 | Phase boundaries (08 / 08.5 / 09) | [`phase-085-phase-boundaries-doctrine.md`](./phase-085-phase-boundaries-doctrine.md) | **CESP-BND-*** |
| 4 | Gap matrix + vocabulary | [`cesp-spec-gap-matrix.md`](./cesp-spec-gap-matrix.md) | **G-P085-GAP-MATRIX** |
| 5 | Continuation state machine law | [`phase-085-substrate-continuity-doctrine.md`](./phase-085-substrate-continuity-doctrine.md) | **G-P085-CONT-01** (runtime) |
| 6 | Autonomous phase progression | same §Progression | **G-P085-PROG-01** |
| 7 | Async durability + dead-letter | [`phase-085-recovery-continuity-doctrine.md`](./phase-085-recovery-continuity-doctrine.md) | **G-P085-DLQ-01** |
| 8 | Replay-safe retry + recovery receipts | same §Receipts | **G-P085-REC-01** |
| 9 | Stalled pipeline watchdog + auto-heal | same §Watchdog | **G-P085-WATCH-01** |
| 10 | Graph density metrics + maturity | [`phase-085-graph-density-doctrine.md`](./phase-085-graph-density-doctrine.md) | **G-P085-GRAPH-01** |
| 11 | Lawful edge promotion automation | same §Promotion | **G-P085-PROMO-01** |
| 12 | Continuity stitching + orphan law | same §Stitching | **G-P085-ORPHAN-01** |
| 13 | Graph completeness propagation | same §Propagation | COMP graph stage |
| 14 | Automatic traversal scheduling | [`phase-085-traversal-completion-doctrine.md`](./phase-085-traversal-completion-doctrine.md) | **G-P085-WALK-01** |
| 15 | Traversal retry + frontier healing | same §Retry | **G-P085-WALK-02** |
| 16 | Stalled traversal recovery | same §Recovery | **G-P085-WALK-03** |
| 17 | Traversal density + explainability | same §Metrics | **G-P085-WALK-04** |
| 18 | TCRE auto-scheduling saturation | [`phase-085-tcre-maturity-doctrine.md`](./phase-085-tcre-maturity-doctrine.md) | **G-P085-TCRE-01** |
| 19 | Reconstruction density metrics | same §Density | **G-P085-TCRE-02** |
| 20 | Causal omission explainability | same §Omissions | **G-P085-TCRE-03** |
| 21 | Retrieval density maturity | [`phase-085-retrieval-density-doctrine.md`](./phase-085-retrieval-density-doctrine.md) | **G-P085-RET-01** |
| 22 | Index freshness + starvation gates | same §Starvation | **G-P085-RET-02** |
| 23 | Retrieval completeness propagation | same §Completeness | COMP retrieval stage |
| 24 | Synthesis activation automation | [`phase-085-synthesis-activation-doctrine.md`](./phase-085-synthesis-activation-doctrine.md) | **G-P085-SYN-01** |
| 25 | Idle vs starved distinction | same §IdleLaw | **G-P085-SYN-02** |
| 26 | Synthesis throughput maturity | same §Throughput | **G-P085-SYN-03** |
| 27 | Multi-dimensional maturity model | [`phase-085-operational-health-maturity-doctrine.md`](./phase-085-operational-health-maturity-doctrine.md) | **G-P085-MAT-01** |
| 28 | Operational health dimensions | same §Health | **G-P085-HEALTH-01** |
| 29 | Autonomous recovery score | same §RecoveryScore | **G-P085-HEALTH-02** |
| 30 | Admin cockpit specification | [`phase-085-admin-cockpit-spec.md`](./phase-085-admin-cockpit-spec.md) | **G-P085-CP-01** |
| 31 | Dedicated explorer surfaces | same §Explorers | **G-P085-CP-02** |
| 32 | Progression timelines + causal chains | same §Timeline | **G-P085-CP-03** |
| 33 | Queue pressure + density caps | [`phase-085-runtime-economics-doctrine.md`](./phase-085-runtime-economics-doctrine.md) | **G-P085-ECON-01** |
| 34 | Replay storm + overload degradation | same §Storms | **G-P085-ECON-02** |
| 35 | Phase 09 readiness gates | [`phase-085-phase-09-readiness-doctrine.md`](./phase-085-phase-09-readiness-doctrine.md) | **G-P085-READY-01** |
| 36 | Certification pack + closure | [`phase-085-closure-gates-doctrine.md`](./phase-085-closure-gates-doctrine.md) | **G-P085-CLOSE-01** |

**E2E architecture:** [`phase-085-runtime-architecture.md`](./phase-085-runtime-architecture.md).

---

## Vocabulary (closed)

| Term | Meaning |
| ---- | ------- |
| **CESP** | Continuous Execution Substrate Program — Phase 08.5 |
| **Operational aliveness** | Tenant satisfies continuity + density + activation + survivability + truth (executive brief) |
| **Fake-green idle** | Stage `healthy` while eligible work exists upstream — **forbidden** for graph/traversal/TCRE/retrieval/synthesis |
| **Starvation** | Upstream artifacts exist but downstream stage `processed_count = 0` beyond `T_starve` |
| **Healthy idle** | No eligible upstream artifacts **and** operator-classified idle — may show green |
| **Continuation** | Durable async-gap state between pipeline phases (TCRE wait, etc.) |
| **Density** | Lawful row/scope growth rate per stage (not raw ingest volume) |
| **Recovery receipt** | Canonical hash proving idempotent resume attempt |
| **RET-SKIP-*** | Retrieval materialization skip taxonomy (extends Phase 07) |
| **OPERATIONAL_ALIVE** | Maturity class required for Phase 09 |

---

## CI gate catalog (summary)

| Gate | Step | hard_fail |
| ---- | ---- | --------- |
| G-P085-ANTI-IDLE-01 | 2 | yes |
| G-P085-CONT-01 | 5 | yes |
| G-P085-PROG-01 | 6 | yes |
| G-P085-WATCH-01 | 9 | yes |
| G-P085-RET-01 | 21 | yes |
| G-P085-SYN-02 | 25 | yes |
| G-P085-MAT-01 | 27 | yes |
| G-P085-CLOSE-01 | 36 | yes |

Full wiring in [`phase-085-testing-strategy.md`](./phase-085-testing-strategy.md) (Step 36 deliverable).

---

## Implementation status snapshot (2026-05-18)

| Area | Status |
| ---- | ------ |
| Continuation persistence + resume | **Partial** (`pipeline_continuation`, migration 0082) |
| Watchdog + recovery | **Partial** (`stalled_pipeline_recovery`, Celery beat) |
| Retrieval diagnostics + RET-SKIP | **Partial** |
| Eligibility explainability | **Partial** |
| Coarse maturity (STAGE_0–6) | **Partial** |
| Graph/traversal/TCRE automation | **Not Started** |
| Admin cockpit UI | **Not Started** (APIs partial) |
| CESP-CERT-PACK-1 | **Not Started** |
