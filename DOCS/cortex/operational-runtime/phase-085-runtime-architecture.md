# Phase 08.5 — Runtime architecture (operational flow)

**Status:** normative.

---

## End-to-end operational flow

```mermaid
flowchart TB
  subgraph ingest [Ingestion plane]
    CONN[Connectors / mock dataset]
    RAW[Raw + canonical backlog]
  end

  subgraph sched [Scheduling plane]
    PIR[post_ingestion_substrate_refresh]
    COORD[Pipeline coordinator phase 02]
    CONT[(continuation_states)]
    WATCH[continuity_watchdog]
  end

  subgraph substrate [Substrate pipeline]
    P02[02 canonical]
    P03[03 identity]
    P04[04 graph]
    P05[05 traversal]
    P06[06 TCRE async]
    P07[07 retrieval materialize + report]
    P08[08 synthesis + audit]
  end

  subgraph density [Density schedulers - CESP]
    GD[graph density pass]
    TW[traversal scheduler]
    TS[tcre saturation]
  end

  subgraph obs [Observability]
    MAT[maturity evaluator]
    CP[admin cockpit]
  end

  CONN --> RAW --> PIR --> COORD --> P02 --> P03 --> P04 --> P05
  P05 --> GD
  GD --> TW
  P05 --> P06
  P06 --> CONT
  P06 --> TS
  TS -->|TCRE complete| CONT
  CONT --> P07
  P07 --> P08
  WATCH --> CONT
  WATCH -->|recover| P07
  P07 --> MAT
  P08 --> MAT
  MAT --> CP
```

---

## Package layout (target)

```
vector/domains/cortex/operational_runtime/     # maturity, certification
vector/domains/cortex/substrate_pipeline/      # continuation, recovery (exists)
vector/domains/cortex/retrieval/                 # diagnostics, skip registry (partial)
vector/domains/cortex/synthesis/                 # eligibility, activation audit (partial)
vector/domains/cortex/completeness/              # fake-green fixes
app/tasks/cortex_substrate_continuity_watchdog.py
```

---

## Data flows

| Event | Durable writes |
| ----- | -------------- |
| Phase 06 enqueue | `continuation_states` WAITING |
| TCRE complete | resume receipt, phase 07 task |
| Phase 07 | `retrieval_materialization_reports`, index epoch |
| Phase 08 | `synthesis_activation_audits`, jobs, artifacts |
| Watchdog | continuation STALLED/RECOVERING, recovery receipts |

---

## Async boundaries

| Gap | Mechanism |
| --- | --------- |
| 06→07 | TCRE callback + continuation resume |
| 07→08 | `on_retrieval_publish_completed_for_pipeline_v1` |
| Stalled | watchdog `recover_stalled_pipeline_v1` |

---

## Truth surfaces

| Question | API |
| -------- | --- |
| Why retrieval 0? | materialization report + RET-SKIP |
| Why synthesis 0? | `explain_synthesis_eligibility_v1` |
| Is tenant alive? | `evaluate_tenant_runtime_maturity_v1` → upgraded |
| Pipeline stuck? | stalled catalog + continuation |
