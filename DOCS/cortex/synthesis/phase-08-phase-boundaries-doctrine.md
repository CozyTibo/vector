# Phase 08 — Phase boundaries (07 / 09 / 10)

**Status:** normative.

---

## Phase 08 OWNS

| Concern | Deliverable |
| ------- | ----------- |
| Synthesis job contracts | Workloads, envelopes, FSM, legality |
| Evidence-constrained intelligence | Claims, citations, narratives |
| LLM orchestration law | Routing, caps, prompt pins |
| Synthesis replay identity | Twin proofs, publication epochs |
| Synthesis receipts | Audit + pipeline linkage |
| Operator synthesis plane | Debuggers, replay explorer, eval views |
| Substrate completeness | Synthesis stage in overview |
| Pipeline phase **08** | Celery + publish barrier |

---

## Phase 08 DOES NOT OWN

| Concern | Owner |
| ------- | ----- |
| Evidence retrieval | **Phase 07** |
| Temporal–causal reconstruction | **Phase 06** |
| Graph walks | **Phase 05** |
| Product workflows / HITL | **Phase 09** |
| Global admin shell / RBAC | **Phase 10** (Phase **08** ships Synthesis slice) |

---

## Boundary with Phase 07 (Retrieval)

| Rule | Text |
| ---- | ---- |
| **SYN-BND-07-01** | Phase **08** MUST obtain evidence only via `execute_retrieval_query_envelope_v1` (or replay of stored retrieval receipt bytes) — never duplicate retrieval SQL. |
| **SYN-BND-07-02** | Phase **08** MUST copy `retrieval_legality_class`, `causal_legality_class`, `chronology_legality_class` from retrieval response — MUST NOT upgrade legality via LLM. |
| **SYN-BND-07-03** | `retrieval_query_replay_identity` MUST be pinned on every synthesis job and stored on artifact header. |
| **SYN-BND-07-04** | Exploration retrieval (`non_authoritative: true`) MUST be rejected at authoritative synthesis ingress unless job declares `execution_partition=exploration`. |
| **SYN-BND-07-05** | Every `RD-*` omission in retrieval MUST propagate to synthesis as `SD-UPSTREAM-RD-*` or block authoritative synthesis per policy pack. |

**Handoff artifact:** Phase **07** `retrieval_query_receipt` + `retrieval_evidence_hits[]` — Phase **08** stores digest-pinned copy on job row.

---

## Boundary with Phase 09 (Products)

| Rule | Text |
| ---- | ---- |
| **SYN-BND-09-01** | Phase **09** MUST consume `SynthesisIntelligenceArtifactV1` by id + `synthesis_publication_epoch` — not re-invoke LLM for same scope. |
| **SYN-BND-09-02** | Phase **09** owns human approval, escalation, and product UX — Phase **08** provides legality + replay only. |
| **SYN-BND-09-03** | Product-specific prompts MUST NOT live in Phase **08** policy pack — they reference artifact templates in Phase **09**. |

---

## Boundary with Phase 10 (Admin)

| Rule | Text |
| ---- | ---- |
| **SYN-BND-10-01** | Phase **10** unifies navigation; Phase **08** ships **Synthesis** routes with `surface_kind` metadata. |
| **SYN-BND-10-02** | Dangerous actions (force replay, purge artifacts, disable synthesis) follow `10-admin/dangerous-action-safety-model.md`. |

---

## Dependency direction (acyclic)

```text
07 Retrieval → 08 Synthesis → 09 Products
```

Retrieval MUST NOT call synthesis. TCRE MUST NOT call synthesis.
