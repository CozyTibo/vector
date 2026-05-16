# Phase 07 — Anti-goals doctrine (forbidden retrieval cognition)

**Status:** normative.  
**Gate:** **G‑P07‑ANTI‑01** (static import / schema scan), **G‑P07‑ANTI‑02** (ingress token rejection).

---

## Constitutional boundary

Phase 07 MUST NOT become:

| Forbidden | Rationale |
| --------- | --------- |
| **Semantic / vector search** | No embeddings-first index, no approximate nearest neighbor “relevance,” no hybrid RAG. |
| **LLM ranking or re-ranking** | No model scores, logits, or “helpful ordering.” |
| **Natural-language query parsing** | Queries are **typed envelopes**, not NL→SQL/DSL translation by models. |
| **Synthesis or summarization** | No narrative answers — only **evidence bundles** (Phase 08). |
| **Organizational recommendations** | No “you should merge these teams” — retrieval returns facts + legality only. |
| **Probabilistic confidence theater** | No `0.87 relevance` floats; only **legality classes** + **bounded omission counts**. |
| **Graph exploration UX** | No force-directed “discover structure” — bounded deterministic expansion only. |
| **Authority elevation** | Retrieval MUST NOT promote candidates to authoritative links or rewrite chronology. |

---

## Allowed retrieval outputs (closed algebra)

1. **`RetrievalQueryReceiptV1`** — query execution receipt (digest, replay identity, caps applied).  
2. **`RetrievalEvidenceHitV1`** — zero or more hits, each with **`RetrievalProvenanceEnvelopeV1`**.  
3. **`RetrievalOmissionRowV1`** — explicit exclusions with class + upstream trigger.  
4. **`RetrievalDegradationRollupV1`** — sorted **`RD‑*`** codes (see degradation taxonomy).  
5. **`RetrievalLegalityPostureV1`** — aggregate class for the response.

**RULE RET‑ANTI‑01:** Any field not in the closed algebra MUST NOT appear in authoritative retrieval JSON (exploration partition may attach `non_authoritative: true`).

---

## Static enforcement

- JSON Schema **`retrieval-query-envelope-v1.schema.json`** — reject `embedding`, `similarity`, `llm`, `summary`, `recommendation` keys (**G‑P07‑SCHEMA‑01**).  
- Policy pack caps — no float “weights” except integer **tie-break ordinals** (mirror OCTS walk policy).  
- Admin UI — no free-text “ask anything” box; only form-driven query builders per workload class.

---

## Cross-phase smuggling (explicit rejects)

| Source phase | Smuggled behavior | Phase 07 response |
| ------------ | ----------------- | ------------------- |
| Phase 05 OCTS | Walk ranking as retrieval relevance | **Forbidden** — walk order is traversal policy only. |
| Phase 06 TCRE | Causal inference beyond receipts | **Forbidden** — retrieve receipts/edges, do not re-derive causality. |
| Phase 08 (future) | Retrieval that returns prose | **Forbidden** — Phase 08 consumes hits; Phase 07 does not. |
