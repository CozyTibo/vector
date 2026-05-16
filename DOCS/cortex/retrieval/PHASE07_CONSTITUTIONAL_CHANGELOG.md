# Phase 07 constitutional changelog

## 2026-05-16 — Architecture finalization pass (pre-implementation)

**Scope:** Specification + MASTER_TRACKER only — **no runtime code**.

### Added

- Normative tree `DOCS/cortex/retrieval/` with **30-step** program.  
- Query contract system: workload classes, envelopes, legality, caps.  
- Retrieval addressing model (`retrieval_lookup_id`, refs).  
- Provenance/evidence envelope law.  
- Temporal retrieval semantics.  
- Deterministic ranking (anti-semantic).  
- `RD-*` degradation taxonomy + substrate propagation.  
- Replay equivalence **G-P07-REPLAY-01/02**.  
- Observability + health model.  
- Admin control plane (**16 surfaces**).  
- Substrate overview integration (7th pipeline stage).  
- Runtime architecture + legality matrix.  
- Verification harness catalog + closure **RETRIEVAL-CERT-PACK-1**.  
- Implementation sequencing plan (waves 0–5).

### Boundaries

- Phase 07 explicitly **does not** own synthesis (08), products (09), or TCRE reconstruction (06).  
- Forbidden: embeddings-first retrieval, LLM ranking, NL query boxes.

### Upstream

- Hard dependency on Phase **06** TCRE doctrine + bounded runtime.  
- Hard dependency on Phase **05** OCTS durable walks (**19–23**).  
- Consumes RUNTIME-02 stable refs (`retrieval_lookup_id`, etc.).

### Tracker

- Replaced shallow 6-row Phase 07 table with **30 implementation-grade rows**.
