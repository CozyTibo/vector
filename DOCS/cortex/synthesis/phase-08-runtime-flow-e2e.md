# Phase 08 — Runtime flow (E2E technical)

**Status:** normative.  
**Grounded in:** Phase **07** closure ([`../retrieval/PHASE07_RUNTIME_CLOSURE.md`](../retrieval/PHASE07_RUNTIME_CLOSURE.md)), `substrate_pipeline` phases **02–07**.

---

## Full stack flow (ASCII)

```text
[Connector] → raw append → checkpoint
     ↓
[Post-ingest] schedule_substrate_pipeline_v1 (debounce)
     ↓
┌────────────────────────────────────────────────────────────┐
│ COORDINATOR (Celery)                                        │
│  02 canonical materialize (batch)                           │
│  03 identity projection                                     │
│  04 graph export                                            │
│  05 OCTS reference walks → durable store                    │
│  06 TCRE reconstruction job (async) ──on complete──┐      │
│  07 retrieval index materialize + publish_index_epoch      │
│  08 synthesis jobs + publish_synthesis_epoch  ◄──────┘      │
└────────────────────────────────────────────────────────────┘
     ↓
[Overview] substrate completeness: synthesis stage green/yellow/red
     ↓
[Admin] synthesis control plane / artifact explorers
     ↓
[Phase 09] products consume artifact_id + publication epoch
```

---

## Phase 07 → 08 handoff (detailed)

| Step | Component | Action |
| ---- | --------- | ------ |
| 1 | `materialize_retrieval_index_for_pipeline_v1` | Writes `cortex_retrieval_index_entries` |
| 2 | `publish_retrieval_index_epoch_v1` | Sets tenant `published_index_epoch` |
| 3 | `phase_runners.run_phase_07` | Receipt: `{published_index_epoch, lookup_ids[], materialization_digest}` |
| 4 | `on_retrieval_publish_completed_for_pipeline_v1` | Enqueues phase **08** Celery task |
| 5 | `build_synthesis_job_from_pipeline_receipt_v1` | Default workload per index row |
| 6 | `execute_synthesis_job_envelope_v1` | FSM (see architecture) |
| 7 | `publish_synthesis_epoch_v1` | Monotonic synthesis epoch |

---

## Single synthesis job FSM (authoritative)

```text
INGRESS ──fail──► receipt(failed) ──► END
   │
   ▼
PLAN (retrieval sub-queries)
   │
   ▼
RETRIEVE ──► execute_retrieval_query_envelope_v1 × N
   │              (pins: index_epoch, tcre_policy_bundle_digest, replay_identity)
   ▼
BIND (RD→SD, evidence_scope_summary)
   │
   ▼
ASSEMBLE (claim slots)
   │
   ▼
LLM (structured JSON) ──timeout/schema──► SD-* ──► CLASSIFY
   │
   ▼
CLASSIFY (synthesis_legality_class)
   │
   ▼
RECEIPT (replay identity, digest)
   │
   ▼
PUBLISH (if lawful) ──► cortex_synthesis_artifacts.published=true
```

---

## Replay identities in flight

| Identity | Produced by |
| -------- | ----------- |
| `retrieval_query_replay_identity` | Phase **07** RECEIPT phase |
| `synthesis_job_replay_identity` | Phase **08** RECEIPT phase |
| `artifact_digest` | Canonical artifact body |
| `lineage_chain_digest` | Phase **08** lineage module |

Pipeline receipt stores all pins for operator re-run.

---

## Degradation propagation example

```text
TCRE gap (Phase 06) → RD-TCRE-GAP (Phase 07 hit) → SD-UPSTREAM-RD (Phase 08)
  → synthesis_legality_class = synthesis_degraded
  → claim "causal link X→Y" omitted with SD-CITE-GAP
  → narrative still publishes with explicit omission section
```

---

## Concurrency model

| Concern | Model |
| ------- | ----- |
| Pipeline phases | Sequential Celery chain per tenant run |
| Retrieval sub-queries | Sequential default; parallel max 2 if policy allows |
| Synthesis jobs per run | Bounded chord (32 default) |
| LLM calls | One per job (v1); no multi-turn |
| DB transactions | Per-phase commits; no whole-pipeline single txn |

---

## What operators see (runtime_backed)

After one full ingest cycle:

1. Overview → synthesis stage coverage %
2. Synthesis control plane → last `synthesis_publication_epoch`
3. Artifact explorer → `execution_understanding` for sample chain
4. Citation drilldown → retrieval hit provenance
5. Replay explorer → twin structural pass badge
