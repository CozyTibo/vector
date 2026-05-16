# Phase 07 — Retrieval provenance & evidence doctrine

**Status:** normative.

---

## `RetrievalProvenanceEnvelopeV1` (mandatory per hit)

| Field | Required | Source |
| ----- | -------- | ------ |
| `provenance_envelope_id` | yes | content hash |
| `tenant_id` | yes | query |
| `replay_posture` | yes | `stable` \| `partial` \| `unsafe` \| `unknown` |
| `chronology_legality_class` | when chronology hit | TCRE receipt |
| `causal_legality_class` | when edge hit | TCRE edge |
| `omission_state` | yes | `none` \| `partial` \| `excluded` |
| `continuity_posture` | when org hit | Phase 04 |
| `lineage_coverage` | when lineage | `complete` \| `gap` \| `unknown` |
| `traversal_binding_state` | when walk hit | `bound` \| `unbound` \| `stale_epoch` |
| `degradation_classes` | sorted unique | `CD-*`, `RD-*` |
| `upstream_digests` | object | See below |
| `evidence_legality_class` | yes | §Evidence classes |

### `upstream_digests` (closed keys)

| Key | When |
| --- | ---- |
| `raw_record_digest` | raw-backed hit |
| `canonical_materialization_digest` | canonical hit |
| `org_link_digest` | graph hit |
| `walk_result_hash` | OCTS hit |
| `tcre_policy_bundle_digest` | TCRE hit |
| `chronology_receipt_digest` | chronology hit |
| `causal_chain_id` | chain hit |
| `retrieval_index_entry_digest` | index-served hit |

**RULE RET‑PROV‑01:** Missing digest for declared artifact type → hit legality forced to `retrieval_degraded` minimum.

---

## Evidence legality classes

| Class | Meaning |
| ----- | ------- |
| `evidence_authoritative` | All upstream authoritative partitions + strict chronology |
| `evidence_degraded` | Upstream degraded but structurally present |
| `evidence_candidate_only` | Hint/candidate links only — MUST NOT label authoritative |
| `evidence_replay_conflict` | Identity or replay conflict poison |
| `evidence_unverifiable` | Missing pins / incomplete lineage |

---

## Retrieval omission semantics

| `retrieval_omission_class` | Meaning |
| -------------------------- | ------- |
| `omitted_cap` | Policy cap (RD-CAP-*) |
| `omitted_upstream_gap` | TCRE/graph/traversal never produced artifact |
| `omitted_legality` | Forbidden by query legality |
| `omitted_replay_unsafe` | Upstream replay unsafe |
| `omitted_exploration_partition` | Excluded from authoritative partition |
| `omitted_addressing_partial` | Ref resolved partially only |

**RULE RET‑PROV‑02:** Omissions MUST appear in `RetrievalOmissionRowV1[]` — count and class — never reduce silently.

---

## Partial retrieval legality

| Situation | Response class |
| --------- | -------------- |
| 0 hits, all omissions explained | `retrieval_partial` |
| Some hits + omissions | `retrieval_degraded` or `retrieval_partial` |
| Hits all strict | `retrieval_replay_safe` |

---

## Integration with Phase 06 completeness

Substrate completeness ledger MUST consume:

- `indexed_count`, `replay_safe_count` from retrieval index  
- `retrieval_never_indexed` when graph/TCRE exist but index empty  
- Propagation from `orphan_artifacts`, `traversal_never_executed`, `reconstruction_coverage_gap`

See [`phase-07-retrieval-completeness-doctrine.md`](./phase-07-retrieval-completeness-doctrine.md).

---

## §Replay

`retrieval_query_replay_identity` = `sha256` over:

- canonical query envelope (excluding receipt)
- active `retrieval_policy_digest`
- set of `upstream_digests` for all hits and omissions

Double-run equivalence: **G‑P07‑REPLAY‑01** (see replay spec).
