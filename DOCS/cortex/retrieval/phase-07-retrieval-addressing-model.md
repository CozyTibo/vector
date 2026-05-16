# Phase 07 — Retrieval addressing model

**Status:** normative.

---

## Design principle

Every retrieval hit MUST be reachable via a **stable, replayable address** composed from upstream digests — not surrogate auto-increment ids alone. Surrogate ids MAY exist for storage but **`retrieval_lookup_id`** MUST hash canonical addressing bodies.

---

## Core identifiers

### `retrieval_lookup_id`

- **Format:** `sha256:` + 64 hex lowercase.  
- **Body:** `RETRIEVAL-CANON-1` sorted JSON of:
  - `tenant_id`
  - `workload_class`
  - primary address key (see below)
  - `temporal_scope` canonical form
  - `replay_pins` (when authoritative)

**Use:** idempotent query dedup; index primary key; admin drill-down.

### `retrieval_window_ref`

- **Purpose:** chronology / materialization window.  
- **Body keys:** `t_as_of_unix_ns`, `materialization_id` OR `window_start_ns` + `window_end_ns` (half-open `[start, end)`).  
- **Binding:** TCRE `chronology_window_ref` from RUNTIME‑02 MUST map 1:1.

### `retrieval_chain_ref`

- **Purpose:** causal chain scope.  
- **Body keys:** `causal_chain_id` (includes `tcre_policy_bundle_digest` per Phase 06).  
- **Optional:** `breakpoint_index` upper bound for truncated inspect.

### `retrieval_walk_ref`

- **Purpose:** OCTS traversal scope.  
- **Body keys:** `walk_id`, `walk_result_hash`, `traversal_epoch`.  
- **Lineage:** links to `cortex_octs_durable_walk_records`.

### `retrieval_lineage_ref`

- **Purpose:** artifact lineage explorer terminal.  
- **Body keys:** `artifact_kind`, `artifact_ref`, `terminal_digest`.

### `provenance_envelope_id`

- **Purpose:** pointer to full `RetrievalProvenanceEnvelopeV1` blob (content-addressed).  
- **Digest:** `sha256` over envelope JSON (sorted keys).

---

## Address resolution order

1. If `retrieval_lookup_id` provided → direct index hit.  
2. Else compose canonical body from refs → compute lookup id → index hit.  
3. Else resolve refs against durable tables (walk store, TCRE artifacts, org graph).  
4. Failure → `addressing_unresolved` with per-field detail.

**RULE RET‑ADDR‑01:** Resolution MUST be deterministic — same inputs → same lookup id on all replicas.

---

## Multi-artifact joins (forbidden patterns)

| Pattern | Verdict |
| ------- | ------- |
| Ad-hoc SQL join across tenants | **Forbidden** |
| Join without declared workload class | **Forbidden** |
| Graph expansion beyond `max_hops` | **Omission**, not silent truncate |

Lawful multi-fetch: **orchestrated sub-queries** each with own receipt, merged in `RetrievalCompositeResponseV1` with stable sort by `(workload_class, primary_key)`.

---

## Continuity references

| Ref | Source |
| --- | ------ |
| `org_entity_id` | Phase 04 |
| `org_link_id` | Phase 04 authoritative link |
| `materialization_id` | Phase 03 |
| `raw_record_id` | Phase 02 |
| `tcre_job_id` | Phase 06 |

All MUST appear in provenance envelope when hit includes that artifact.
