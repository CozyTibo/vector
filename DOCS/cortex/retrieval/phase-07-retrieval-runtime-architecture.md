# Phase 07 — Retrieval runtime architecture

**Status:** normative (package layout target: `vector.domains.cortex.retrieval`).

---

## Package layout

```text
vector/domains/cortex/retrieval/
  normative.py                    # PHASE07_PROGRAM_FREEZE_VERSION
  anti_goals.py
  query_contract.py               # envelope validate + FSM
  addressing.py                   # lookup id + ref resolution
  legality.py                     # classifiers
  ranking.py                      # deterministic tuple sort
  provenance.py                   # envelope builder
  temporal.py                     # scope canonicalization
  degradation.py                  # RD-* registry
  replay_equivalence.py           # G-P07-REPLAY-01
  index/                          # materialization + publish
  bindings/
    tcre_binding.py
    octs_binding.py
    graph_binding.py
    canonical_binding.py
  runtime/
    query_engine.py               # orchestrator
    retrieval_audit_repository.py
  completeness/
    retrieval_completeness_projection.py
  control_plane.py
  readiness_economics.py
  verification_harness.py
  certification_pack.py
```

---

## §Index (`cortex_retrieval_index_entries`)

| Column | Purpose |
| ------ | ------- |
| `tenant_id` | scope |
| `retrieval_lookup_id` | pk part |
| `index_epoch` | publish barrier |
| `workload_class` | discriminator |
| `artifact_kind` | chronology_receipt / causal_edge / walk / ... |
| `artifact_ref` | stable ref string |
| `artifact_digest` | sha256 body |
| `retrieval_legality_class` | denormalized for coverage |
| `upstream_digest_json` | pinned digests |

**Index build job FSM:** `QUEUED → BUILDING → PUBLISHED` (mirror OCTS index job).

**RULE RET-IDX-01:** Queries MUST NOT read partial epoch — only `published_epoch`.

---

## §TCRE binding

- Read `cortex_tcre_reconstruction_jobs` + artifacts  
- Map `materialization_id`, `causal_chain_id`, `tcre_causal_edge_id` → lookup ids  
- Surface `RD-TCRE-GAP` when job missing  

---

## §OCTS binding

- `resolve_octs_walk_store_v1` durable records  
- `retrieval_walk_ref` from walk_hash + epoch  
- `RD-TRAVERSAL-IDLE` when walks=0 and graph eligible  

---

## §Graph binding

- `CortexOrgEntity`, `CortexOrgLink` (authoritative only for authoritative partition)  
- Candidates → `evidence_candidate_only` or omission  

---

## §Lineage

- Reuse `vector.domains.cortex.lineage` chain builder  
- Terminal ref from query → expand to hits with hop cap  

---

## §Query engine orchestrator

```python
def execute_retrieval_query_v1(session, *, tenant_id, envelope) -> RetrievalQueryResultV1:
    ...
```

Phases: VALIDATE → RESOLVE → BOUND → PROVENANCE → CLASSIFY → RECEIPT

---

## §Admin HTTP

Register in `admin_cortex_retrieval.py` (routes listed in overview integration).

---

## §Celery (optional lane)

- `vector.cortex.retrieval.index_build` — tenant index rebuild  
- `vector.cortex.retrieval.verification_slice` — tenant certification  

Queue: `vector` (same as TCRE).

---

## §Migrations (planned)

- `cortex_retrieval_index_entries` (exists partially — align to spec)  
- `cortex_retrieval_query_audit`  
- `cortex_retrieval_index_epochs`  

---

## §Dependencies

| Upstream | Required for |
| -------- | ------------ |
| Phase 06 artifacts | TCRE hits |
| Phase 05 durable walks | Traversal hits |
| Phase 04 graph | Org hits |
| Phase 03 canonical | Mat hits |
| Policy pack JSON | Caps + ordering |
