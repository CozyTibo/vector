# Phase 07 — Implementation sequencing plan

**Status:** normative handoff (no code in this pass).

---

## Sequencing waves

### Wave 0 — Doctrine freeze (current pass)

- Ship `DOCS/cortex/retrieval/*` + MASTER_TRACKER Steps 1–30  
- Gap matrix P0 = none for architecture  

### Wave 1 — Contracts + gates (no DB)

| Order | Deliverable | Unlocks |
| ----- | ----------- | ------- |
| 1.1 | `normative.py`, `anti_goals.py`, static G-P07-ANTI-* | all code |
| 1.2 | `query_contract.py`, schemas, G-P07-SCHEMA-01 | addressing |
| 1.3 | `addressing.py`, golden vectors G-P07-ADDR-01 | engine |
| 1.4 | `legality.py`, `degradation.py`, legality matrix API stub | admin legality view |

### Wave 2 — Read path over existing stores (minimal index)

| Order | Deliverable | Unlocks |
| ----- | ----------- | ------- |
| 2.1 | `bindings/tcre_binding.py` — read artifacts | TCRE queries |
| 2.2 | `bindings/octs_binding.py` — durable walks | traversal queries |
| 2.3 | `query_engine.py` — POST query (no index) | admin debugger |
| 2.4 | `provenance.py`, `ranking.py` | lawful responses |
| 2.5 | G-P07-REPLAY-01 harness | replay trust |

### Wave 3 — Index + coverage

| Order | Deliverable | Unlocks |
| ----- | ----------- | ------- |
| 3.1 | Migration align `cortex_retrieval_index_entries` | scale |
| 3.2 | Index build job + epoch publish | coverage metrics |
| 3.3 | `retrieval_completeness_projection.py` | overview stage |
| 3.4 | Propagation rules in completeness | degradation panel |

### Wave 4 — Operator plane

| Order | Deliverable | Unlocks |
| ----- | ----------- | ------- |
| 4.1 | `control_plane.py`, readiness economics | ops |
| 4.2 | Admin SPA routes (overview, query, lineage) | operators |
| 4.3 | Audit table + trail UI | compliance |
| 4.4 | Tenant verification slice | CI |

### Wave 5 — Closure

| Order | Deliverable | Unlocks |
| ----- | ----------- | ------- |
| 5.1 | RETRIEVAL-CERT-PACK-1 + G-P07-CLOSE-01 | Phase 08 start |
| 5.2 | Runtime legality matrix enforcement | production |

---

## Parallel tracks

| Track | Can parallelize after |
| ----- | --------------------- |
| Frontend admin | Wave 2.3 (API stubs) |
| Celery index jobs | Wave 3.1 |
| Golden vectors | Wave 1.3 |

---

## Critical path

```text
anti_goals → query_contract → addressing → tcre_binding → query_engine → replay_gate → index → completeness → admin → close
```

---

## Phase 08 readiness checklist

Before Phase 08 coding:

- [ ] `RetrievalEvidenceHitV1` schema frozen  
- [ ] Phase 08 ingress rejects non-authoritative retrieval  
- [ ] Sample queries documented for synthesis fixtures  

---

## Estimated step mapping (tracker → waves)

| Tracker steps | Wave |
| ------------- | ---- |
| 1–9 | 0–1 |
| 10–13 | 1–2 |
| 14–18 | 2–3 |
| 19–21 | 3 |
| 22–26 | 4 |
| 27–30 | 5 |
