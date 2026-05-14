# Cross-system continuity law (deterministic operational evidence)

**Status:** normative law — **no new phases**; constitutional substrate for **Phases 01–05** continuity across operational systems.  
**Scope:** deterministic reconstruction of **execution continuity** and **storylines** from **evidence chains** — not semantic similarity, not “same topic,” not probabilistic entity resolution.  
**Code anchors:** `execution_reconstruction_contracts.py` (`NormalizedReference`, `IdentityLinkDerivation`, `TemporalAnchor`, `TemporalAnchorChain`, `CrossSourceTemporalReference`, `CanonicalWorkstream`, `OwnershipContinuityLedger`); `reference_schema` for normalized refs; Phase 04 graph projection / Phase 05 import boundary doctrine for ingress constraints.

**Explicit non-goals:** embeddings, LLM reasoning, probabilistic matching, agents, semantic “same work” inference, ingestion redesign, DB redesign, UI redesign, graph exploration features.

---

## 1. Philosophy

**Execution continuity** is reconstructed only from **operational evidence chains**: explicit references, stable handles, temporal envelopes, and replay-lineage-carrying artifacts.

Continuity is **lawful** or **absent**. It is never **simulated** from conversational proximity or topic.

---

## 2. Continuity primitives (vocabulary)

| Primitive | Definition |
|-----------|------------|
| **Continuity anchor** | A `TemporalAnchor` + optional `NormalizedReference` that is admissible as a tie point across systems. |
| **Continuity bridge** | A deterministic record linking two anchors **only** via allowed linkage classes (§3). |
| **Continuity lineage** | Ordered `EvidenceLineageHop` sequence proving a bridge — includes `raw_record_id` / `reference` / `rule_id`. |
| **Continuity hop** | Single hop in lineage (`raw_record`, `normalized_reference`, `derived_window`, `cross_link`). |
| **Execution storyline** | Acyclic (or explicitly partitioned) directed structure over **admitted** events, commitments, and deployment refs — **not** a natural-language narrative. |
| **Evidence chain** | Minimal set of raw rows + refs closing a claimed cross-system obligation. |
| **Replay continuity segment** | Interval of evidence accepted as **replay_equivalent** for continuity purposes under golden-thread profile id. |

---

## 3. Cross-system linkage rules (deterministic only)

**Allowed linkage classes** (each requires `rule_id` + lineage):

| Class | Example pattern |
|-------|-----------------|
| `shared_canonical_reference` | Same `NormalizedReference` fingerprint in Slack + Linear + GitHub payloads. |
| `explicit_url_reference` | URL string equality after canonical URL normalization policy. |
| `issue_key_linkage` | Parsed `OWNER/REPO#n` or Linear issue id equality per connector parsers (frozen tables). |
| `deployment_reference` | Deployment id / environment ref present in both systems’ structured fields. |
| `commit_reference` | Commit SHA equality (full hash; short-hash only with disambiguation rule id). |
| `thread_escalation_reference` | Slack message cites Linear/GitHub ref **in structured attachment or parseable template** — not free-text “maybe JIRA”. |
| `temporal_continuity_envelope` | Half-open interval overlap **plus** at least one non-temporal anchor from §3 (overlap alone is insufficient). |
| `explicit_ownership_continuity` | `OwnershipContinuityLedger` entry with handles + subject ref. |
| `replay_lineage_continuity` | Same replay job / export receipt id carried across artifacts per registry policy. |

**Rule:** `IdentityLinkDerivation` values outside the enum in `execution_reconstruction_contracts.py` are **invalid** until a contract version bump.

---

## 4. Forbidden linkage

- **Embedding similarity** — any vector comparison for “related work.”  
- **Semantic topic similarity** — clustering, LDA, “thread about payments.”  
- **Inferred “same work”** — gut-feel linkage.  
- **Probabilistic relationship scoring** — “80% same incident.”  
- **Vague temporal coincidence linkage** — “events within 5 minutes” without shared ref or explicit policy `rule_id` that is **not** similarity-based.

---

## 5. Continuity strength classes

Each bridge receives a **strength** label for downstream gating (walks, certification, operator UI substrate):

| Strength | Criteria sketch |
|----------|-----------------|
| `authoritative` | Exported canonical pointer + replay receipt agrees. |
| `direct` | Single shared `NormalizedReference` + both sides’ raw ids in lineage. |
| `continuity_backed` | `IdentityLinkDerivation` in {`explicit_linkage`, `shared_execution_reference`}. |
| `partial` | `temporal_overlap` **with** shared ref; or `replay_safe_ordering` partial. |
| `weak` | Allowed derivation but missing optional anchors — must not drive traversal alone. |
| `unverifiable` | Insufficient evidence; bridge **not** admitted or explicitly quarantined per conflict doctrine. |

Strength is **declared by rule tables**, not learned weights.

---

## 6. Continuity degradation (propagation)

When a bridge is downgraded or severed:

| Surface | Effect |
|---------|--------|
| **Chronology** | `TemporalAnchorChain` may move to `partial` / `unresolved`; skew flags set. |
| **Replay legality** | May become `replay_degraded` or `replay_unverifiable` per golden-thread / Phase 05 matrices. |
| **Traversal legality** | Walks must refuse illegal hops; exploration mode receipts if applicable. |
| **Commitment continuity** | `CommitmentDriftSignal` / `FollowThroughGap` / lifecycle downgrade. |
| **Ownership continuity** | `ownership_continuity_ok` false; negative signals per `negative-execution-signal-spec.md` patterns. |

Degradation is **monotone** in severity until new authoritative evidence arrives (receipted recovery).

---

## 7. Cross-system chronology law

| Topic | Law |
|-------|-----|
| **Export ordering** | Monotonic cursors win ties per temporal reconstruction spec. |
| **Clock skew** | Surfaces as `CrossSourceTemporalReference.skew_detected`; never “fix” user clocks silently. |
| **Late ingestion** | `late_arrival` flag; historical reducer outputs immutable without migration version. |
| **Continuity windows** | `ExecutionInteractionWindow` / `ExecutionChronologyWindow` carry `derivation_rule_id`. |
| **Replay chronology reconciliation** | Phase 05 async permutation laws — continuity **does not** assume global wall-clock simultaneity. |

---

## 8. Storyline reconstruction doctrine

**When separate operational artifacts become ONE execution storyline:**

All must hold:

1. **Shared ref spine** — at least one `shared_canonical_reference` or equivalent allowed class connecting artifacts.  
2. **Temporal envelope** — `ExecutionChronologyWindow` or interaction window admits the merge (no contradiction per conflict doctrine).  
3. **Single partition id** — if ambiguity remains, `partitioned` outcomes get distinct partition ids; **never** merge partitions without supersession evidence.  
4. **Inspectable merge log** — deterministic merge `rule_id` + hash of inputs.

**Illustrative lawful merges (examples only):**

- Slack escalation message contains Linear issue URL + Linear issue updated in same replay slice → **one** storyline spine via `explicit_url_reference` + `issue_key_linkage`.  
- GitHub hotfix PR references deploy id + deployment system row carries same id → `deployment_reference`.  
- Rollback pairs deploy + revert with explicit linkage fields → storyline shows two vertices, one rollback edge — not “bad team.”

**Unlawful merges:** “Slack thread feels like the same incident as Linear” without ref spine.

---

## 9. Constitutional invariants

**X1:** Every admitted cross-system bridge has **non-empty** provenance to raw rows on **each** system side (or explicit export receipt bridging allowed gap).

**X2:** Continuity strength **never** increases without new evidence or authoritative export upgrade.

**X3:** Storyline merges **never** reduce inspectable evidence count — only add derived structure.

**X4:** Phase 05 ingress (`OrgGraphProjectionV1`) **rejects** continuity claims that violate import boundary validators — law is enforced at boundary, not “fixed” downstream.

---

## 10. Future implementation targets (documentation only)

Planned layout under `backend/src/vector/domains/cortex/continuity/`:

```
continuity/
  cross_system/                 # linkage class validators + bridge builders
  continuity_lineage/           # lineage normalization + hop audits
  chronology_reconciliation/    # skew + late arrival + export order
  continuity_verification/      # CI + corpus hooks
  storyline_reconstruction/     # partition-aware storyline DAG builders
```

No runtime code in this doctrine step.

---

## 11. Related doctrine

| Document | Role |
|----------|------|
| [`conflict-resolution-doctrine.md`](./conflict-resolution-doctrine.md) | Contradictions when bridges compete. |
| [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md) | Corpus cases for cross-system rows. |
| `DOCS/cortex/ingestion/execution-reduction-doctrine.md` | Slack / connector extraction boundary. |
| `DOCS/cortex/05-traversal/phase-05-graph-import-boundary-doctrine.md` | Ingress constraints for projected graphs. |
