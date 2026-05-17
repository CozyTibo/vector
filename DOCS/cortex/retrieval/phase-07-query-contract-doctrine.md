# Phase 07 — Query contract doctrine

**Status:** normative.  
**Schema authority:** `DOCS/cortex/retrieval/schemas/` (to be generated at implementation; shapes frozen here).

---

## §1 Query workload classes (closed enum)

| Class ID | Purpose | Typical upstream |
| -------- | ------- | ---------------- |
| `execution_continuity` | Materialization + chronology state at anchor | TCRE job / mat id |
| `chronology_window` | Half-open interval of chronology receipts | `chronology_window_ref` |
| `ownership_continuity` | Org entity + authoritative link neighborhood | Phase 04 graph |
| `causal_chain` | Deterministic chain by `causal_chain_id` | TCRE |
| `causal_edge` | Single `tcre_causal_edge_id` + evidence | TCRE |
| `degradation_survey` | `CD-*` / `RD-*` rollup for scope | TCRE + retrieval |
| `dependency_propagation` | Escalation/blocker edges from policy rows | TCRE |
| `replay_divergence` | Twin job diff / equivalence failure | TCRE RUNTIME‑02 |
| `escalation` | Coordination escalation edges (bounded) | TCRE |
| `traversal_lineage` | Walk receipt + hop lineage | OCTS |
| `replay_equivalence` | Double-run retrieval proof | Retrieval + TCRE |
| `lineage_explorer` | Artifact lineage chain terminal→root | Phase 07 lineage |
| `continuity_topology` | Continuity graph projection snapshot | Phase 07 continuity |
| `materialization_as_of` | Canonical + chronology at `t_as_of` | Phase 03 + TCRE |

**RULE RET‑QC‑01:** New workload classes require normative index amendment + **G‑P07‑QC‑01** gate update.

---

## §2 Retrieval intent classes

Intents refine **operator goal** within a workload class (not NL search):

| Intent | Meaning |
| ------ | ------- |
| `inspect` | Single-address lookup — max 1 primary hit |
| `enumerate` | Bounded list in deterministic order |
| `prove` | Emit equivalence / replay receipt set |
| `audit` | Omission-forward — list exclusions explicitly |
| `diff` | Structural compare two pinned scopes (replay twin) |

---

## §3 Lawful query envelope (`RetrievalQueryEnvelopeV1`)

Required fields:

| Field | Type | Law |
| ----- | ---- | --- |
| `schema_version` | int | `1` |
| `tenant_id` | uuid | MUST match auth scope |
| `workload_class` | enum | §1 |
| `intent` | enum | §2 |
| `execution_partition` | `authoritative` \| `exploration` | Mirror OCTS EX‑partition |
| `temporal_scope` | object | See temporal doctrine |
| `addressing` | object | At least one stable ref (§ addressing model) |
| `selection_policy` | object | Caps + ordering profile id |
| `replay_pins` | object | Optional: `tcre_policy_bundle_digest`, `octs_engine_build_ref`, `retrieval_policy_digest` |
| `idempotency_key` | string? | Tenant-scoped dedup |

**RULE RET‑QC‑02:** Queries without resolvable addressing MUST fail **`addressing_unresolved`** (400) — never empty 200.

---

## §4 Query execution contract

Execution phases (deterministic FSM):

1. **VALIDATE** — schema + anti-goals + legality pre-check  
2. **RESOLVE** — addressing → internal row keys (index + durable stores)  
3. **BOUND** — apply caps; compute omissions for overflow  
4. **PROVENANCE** — attach envelope per hit  
5. **CLASSIFY** — aggregate `retrieval_legality_class`  
6. **RECEIPT** — emit `RetrievalQueryReceiptV1` with canonical digest  

**RULE RET‑QC‑03:** Phase order fixed; implementations MUST NOT skip PROVENANCE for performance.

---

## §5 Query legality classes

See [`retrieval-legality-matrix.md`](./retrieval-legality-matrix.md). Summary:

| Class | Meaning |
| ----- | ------- |
| `retrieval_replay_safe` | All hits authoritative; replay pins satisfied |
| `retrieval_degraded` | Hits returned with non-strict upstream legality or partial coverage |
| `retrieval_partial` | Some addressing resolved; omissions present |
| `retrieval_unverifiable` | Upstream replay unsafe / missing pins |
| `retrieval_forbidden` | Anti-goal or policy violation — no hits |

---

## §6 Bounded caps (defaults in policy pack)

| Cap | Default | Breach behavior |
| --- | ------- | ---------------- |
| `max_hits` | 100 | Omission `RD-CAP-HITS` |
| `max_chronology_rows` | 500 | Omission `RD-CAP-CHRON` |
| `max_edges` | 200 | Omission `RD-CAP-EDGE` |
| `max_lineage_hops` | 64 | Omission `RD-CAP-LINEAGE` |
| `max_wall_ms` | 30_000 | Abort `retrieval_timeout` (503) |
| `max_response_json_bytes` | 256 KiB | 413 `retrieval_response_too_large` |

---

## §Ingress (observed vs derived)

Retrieval MAY read:

- **Observed:** raw rows, canonical materializations, authoritative links, OCTS walk records, TCRE artifacts.  
- **Derived:** retrieval index rows **only** when `index_epoch` published per Phase 07 index law.

Retrieval MUST NOT read: LLM caches, embedding tables, synthesis outputs, operator notes.

### Ingress table (runtime: `build_retrieval_ingress_law_catalog_v1`)

| Provenance class | Artifact kinds (representative) | `index_epoch` required | Authoritative partition |
| ---------------- | ------------------------------- | ---------------------- | ----------------------- |
| **observed** | `raw_record`, `canonical_materialization`, `authoritative_link`, `octs_walk_record`, `tcre_artifact`, `causal_chain`, `chronology_receipt` | No | Candidate links → `evidence_candidate_only` |
| **derived** | `retrieval_index`, `retrieval_index_entry` | **Yes** (published epoch only) | Same |
| **forbidden** | `llm_cache`, `embedding_table`, `synthesis_output`, `operator_notes`, `semantic_index` | N/A (reject ingress) | N/A |

**Degradation:** derived read without published epoch → **`RD-INDEX-STALE`** (never silent success).

**Code:** `vector.domains.cortex.retrieval.retrieval_ingress` — **G‑P07‑INGRESS‑01..04**.
