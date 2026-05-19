# Phase 08.5 — Continuous Execution Substrate Program (CESP) — Executive brief

**Status:** normative program (implementation in progress).  
**Placement:** constitutional bridge between **Phase 08 SIL freeze** and **Phase 09 operational intelligence products**.  
**Program id:** **CESP** · **Tracker:** Phase **08.5** · **Freeze target:** **P085-FINAL-FREEZE** (post Step 36).

---

## What this program solves

Phases **01–08** delivered a **lawful, replay-safe execution substrate** that *can* run end-to-end. Local and early-prod tenants still exhibit **operational starvation**:

- pipeline stalls after TCRE async gaps;
- graph/orphan sparsity blocks traversal;
- walks never complete → retrieval eligible count stays **0**;
- synthesis cards show **0** while governance gates pass (**fake-green idle**).

**CESP** closes the gap between **“architecture complete”** and **“substrate continuously alive.”**

---

## Why it matters

Phase **09** builds **operator-facing cognition workflows** on top of `SynthesisIntelligenceArtifactV1`. If substrate never progresses autonomously, Phase 09 ships **empty product shells** backed by **structurally legal but operationally dead** tenants.

CESP is the **operational maturation layer**: continuity, density, self-healing, truthful diagnostics, and certification before product work.

---

## How Cortex behavior changes

| Before CESP | After CESP (target) |
| ----------- | ------------------- |
| Post-ingestion may stop at phase 06 await | **Autonomous resume** with durable continuation + watchdog recovery |
| Graph orphans block traversal silently | **Density program** promotes lawful edges; operators see **why** |
| Traversal pending walks accumulate | **Scheduled completion** + stalled-walk recovery |
| TCRE `reconstruction_not_yet_run` at scale | **Saturation scheduler** drives reconstruction to coverage targets |
| Retrieval publishes empty epochs | **Density metrics + RET-SKIP explainability**; starvation is visible |
| Synthesis idle mistaken for healthy | **Idle vs starved** law; activation audits |
| Admin overview shows 0 with green | **Operational cockpit**: progression timeline, causal chains, recovery actions |
| Manual flush rituals | **Replay-safe auto-heal** within policy caps |

---

## What “alive substrate” means

A tenant is **operationally alive** when **all** hold for a rolling window (default **24h**):

1. **Continuity:** substrate pipeline completes **07→08** without manual intervention after ingestion.
2. **Density:** `retrieval_row_acceptance_rate ≥ θ_ret` and `eligible_scopes > 0` when upstream artifacts exist.
3. **Activation:** `synthesis_jobs_completed > 0` per policy workload cadence OR explicit **healthy_idle** classification.
4. **Survivability:** async failures recover within `T_recovery` without duplicate epochs/jobs.
5. **Truth:** operator surfaces show **same counts as DB**; no in-process-only metrics presented as durable truth.

**Maturity class `OPERATIONAL_ALIVE`** (see maturity doctrine) is required for Phase **09** entry.

---

## Constitutional placement

- **Not** a replacement for Phase 08 governance (SIL freeze stands).
- **Not** Phase 09 product features.
- **Is** Phase **08.5** — **Continuous Execution Substrate Program** under `DOCS/cortex/operational-runtime/`.
- **Code home (target):** `vector.domains.cortex.operational_runtime` + extensions to `substrate_pipeline`, `completeness`, `retrieval`, `synthesis`, admin.

---

## Success metrics (program-level)

| Metric | Target (prod tenant cohort) |
| ------ | --------------------------- |
| `substrate_pipeline_07_08_completion_rate` | ≥ **95%** within 2h of ingestion burst |
| `continuation_stall_rate` | ≤ **2%** of pipeline runs / week |
| `retrieval_epoch_empty_rate` | ≤ **5%** when `tcre_completed > 0` |
| `eligible_scopes_p50` | > **0** for onboarded tenants with graph+TCRE |
| `synthesis_throughput_jobs_per_day_p50` | policy-defined minimum |
| `autonomous_recovery_success_rate` | ≥ **90%** of watchdog recoveries |
| `fake_green_idle_incidents` | **0** in certification harness |

---

## Readiness for Phase 09 (summary)

Phase **09** MUST NOT start until **G-P085-CLOSE-01** passes: see [`phase-085-phase-09-readiness-doctrine.md`](./phase-085-phase-09-readiness-doctrine.md).

---

## Related artifacts

- Normative index: [`phase-085-normative-index.md`](./phase-085-normative-index.md)
- Runtime architecture: [`phase-085-runtime-architecture.md`](./phase-085-runtime-architecture.md)
- Gap matrix: [`cesp-spec-gap-matrix.md`](./cesp-spec-gap-matrix.md)
- Tracker: [`../MASTER_TRACKER.md`](../MASTER_TRACKER.md) § Phase 08.5
