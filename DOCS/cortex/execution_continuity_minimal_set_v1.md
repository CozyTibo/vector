# Execution continuity minimal set v1 (Fizzer)

**Status:** Normative for Phase S2 (artifact-backed execution intelligence).  
**Supersedes:** Any implicit “execution = org graph topology” KPI.  
**Companion:** [`DOCS/audits/cortex_semantic_execution_intelligence_roadmap.md`](../audits/cortex_semantic_execution_intelligence_roadmap.md) Phase S2.

## Principle

Execution continuity is **indexed artifact continuity**, not new org `link_type` values or `ContinuityEdgeKind` rows in the org-link ledger. A class is “proven” only when the named artifacts exist in canonical materialization, TCRE output, or the retrieval index under the kinds below.

Retrieval execution index kinds (from `retrieval_semantic_mix_v1.EXECUTION_INDEX_KINDS_V1`):

| `index_kind` | Role |
|--------------|------|
| `materialization` | Canonical work-object snapshot (PR, deploy, message, …) |
| `walk` | Traversal receipt over org-entity reference graph (OCTS) |
| `causal_chain` | TCRE bounded causal chain artifact |
| `causal_edge` | TCRE pairwise causal edge (handoff, escalation, temporal link) |

Org-link rows (`org_link`, `org_entity`) are **identity scope only** (Phase S1). They do not prove delivery, coordination, or incident chains.

## Five continuity classes (Fizzer v1)

### 1. Ownership

**Question:** Who owned this work artifact?

| Proving artifacts | Connector examples | Index / substrate |
|-------------------|-------------------|-------------------|
| Canonical mat with `authored_by` / actor primitive | GitHub PR mat, Slack message mat, Linear issue mat | `materialization` |
| Identity handle for same actor (cross-system) | Slack user + GitHub login via S1 promotion | S1 auth edge (supporting only) |

**Not sufficient:** `org.persona_belongs_to_handle` alone without a mat tying the handle to the work object.

### 2. Work thread

**Question:** What issue/PR/review thread is this part of?

| Proving artifacts | Connector examples | Index / substrate |
|-------------------|-------------------|-------------------|
| Issue / PR / review canonical mats | `pull_request`, Linear `issue`, GitHub `timeline_mutation` | `materialization` |
| Chronology segment from TCRE | Review → comment ordering | `causal_chain` + chronology mats |

**Not sufficient:** Walk hops that only traverse Notion-handle stars without execution mats on the island.

### 3. Delivery

**Question:** How did merged code reach production?

| Proving artifacts | Connector examples | Index / substrate |
|-------------------|-------------------|-------------------|
| Merge / deployment canonical mats | GitHub `deployment`, workflow_run, merge event | `materialization` |
| TCRE temporal / delivery edges | merge → deploy, deploy → rollback | `causal_edge` |

**Not sufficient:** Graph projection `edge_count` or auth link row growth.

### 4. Coordination

**Question:** How was work handed off or escalated across people/systems?

| Proving artifacts | Connector examples | Index / substrate |
|-------------------|-------------------|-------------------|
| Slack / Linear message mats | Slack `message`, Linear comment | `materialization` |
| TCRE coordination edges | `handoff`, `escalation` causal_edge artifacts | `causal_edge` |

**Not sufficient:** `ContinuityEdgeKind` schema entries not indexed in retrieval.

### 5. Incident

**Question:** What failed, and was it rolled back?

| Proving artifacts | Connector examples | Index / substrate |
|-------------------|-------------------|-------------------|
| Deploy + failure / rollback mats | Failed deploy, rollback event, alert message | `materialization` |
| TCRE negative / rollback edges | `negative_signal`, rollback temporal edge | `causal_edge` |

## Anti-patterns (explicit non-goals)

1. **Do not** add execution semantics as new org `link_type` values.
2. **Do not** treat `ContinuityEdgeKind` (14 schema-only types) as progress until retrieval indexes them.
3. **Do not** use phase 04 monotonic `edge_count` as an execution continuity signal.
4. **Do not** infer PR→deploy chains from org-link topology alone.

## V0 acceptance (one real PR chain)

For the Execution Reality Reconstruction V0 milestone, one chosen PR must exhibit:

1. **Ownership** — PR mat + identity scope for author (S1 + mat).
2. **Work thread** — PR + review/timeline mats in retrieval.
3. **Delivery** — merge/deploy mats + ≥1 indexed `causal_edge` on the delivery path (S2.4 + S3 publish).
4. **Retrieval lineage** — published epoch mix passes semantic gate (`execution_index_pct ≥ 60%`, `org_link_pct ≤ 30%`).

Coordination and incident classes are stretch goals for V0; ownership + work thread + delivery are the critical path.

## Code references

| Concern | Module |
|---------|--------|
| Retrieval mix gate | `retrieval/retrieval_semantic_mix_v1.py` |
| TCRE → index bind | `retrieval/retrieval_tcre_binding.py` |
| Canonical drain priority | `canonical/forward_progress/candidate_selection.py` |
| Walk / TCRE substrate | `substrate_pipeline/substrate_traversal_execution.py`, `reasoning/runtime/reasoning_runtime_orchestrator.py` |

## Rollback flags (S2)

| Flag | Effect |
|------|--------|
| `CORTEX_CANONICAL_EXECUTION_KIND_PRIORITY=0` | Revert to FIFO drain ordering (S2.2) |
| `CORTEX_RETRIEVAL_INDEX_TCRE_CAUSAL_EDGES=0` | Skip `causal_edge` index rows (S2.4) |
