# Golden-thread replay corpus (constitutional substrate verification)

**Status:** normative specification — **no new phases**; hardens verification across **existing Phases 01–05** execution reconstruction.  
**Scope:** deterministic replay-validation infrastructure for reducers, chronology, continuity, and traversal legality — **not** conventional unit-test culture.  
**Code anchors (non-exhaustive):** `backend/src/vector/domains/cortex/ingestion/execution_reconstruction_contracts.py` (`EXECUTION_RECONSTRUCTION_CONTRACT_VERSION`); Phase 05 replay / equivalence / integrity matrices under `DOCS/cortex/05-traversal/`.

**Forbidden in this layer:** embeddings, LLM reasoning, probabilistic matching, agents, semantic ownership inference, ingestion redesign, DB/UI redesign, graph exploration product features.

---

## 1. Objectives

| Objective | Meaning |
|-----------|---------|
| **Deterministic replay validation** | Re-running reconstruction over a frozen **raw evidence bundle** + fixed `extraction_contract_id` / reducer version yields **byte-identical** canonical artifacts where the spec demands equality (ids, sorted lists, hashes). |
| **Reconstruction equivalence guarantees** | Declared equivalence classes (entities, commitments, negative signals, windows) match **expected** sets in the corpus; mismatches are **failures**, not “tuning.” |
| **Reducer regression detection** | Any change to pattern tables, rule ids, ordering, or merge logic must **surface** as corpus diffs before merge. |
| **Chronology stability** | `TemporalAnchorChain.replay_safe_ordering` and half-open windows behave per spec under permutations allowed by async doctrine — **no silent reordering** of committed historical ordering. |
| **Continuity preservation** | Continuity closures and cross-system bridges that are **provenance-backed** in the input remain present or **explicitly degraded** with receipts — never dropped without lineage. |
| **Drift detection** | `CommitmentDriftSignal`, `NegativeExecutionSignal`, and degradation classes move only as prescribed when evidence or reducer version changes. |
| **Invariant preservation across reducer evolution** | Version bumps (`reconstruction_version`, contract version) carry **migration rules**; golden threads prove old invariants still hold or **honestly** report `replay_unverifiable` / `replay_degraded`. |

This is **constitutional substrate replay validation**, not “tests pass locally.”

---

## 2. Replay corpus structure

### 2.1 Corpus artifact (top-level)

A **corpus** is a versioned directory or archive containing:

- `corpus_manifest.json` — metadata (see §3).  
- `cases/<corpus_case_id>/` — one folder per scenario (see §6).  
- `shared/` — optional shared raw snippets referenced by id.  
- `schemas/` — JSON Schema pointers for manifest + case payloads (normative when frozen).

### 2.2 Supported evidence shapes (inputs)

Each case’s **raw evidence bundle** may combine, under explicit `source_systems`:

- **Slack thread timelines** — ordered messages with connector-native ids.  
- **Cross-system coordination** — Slack + GitHub + Linear raw rows with **shared** `NormalizedReference` keys only.  
- **Incident escalations** — templates matching `ExecutionCoordinationKind` / `NegativeSignalKind` without narrative labels.  
- **Ownership transitions** — explicit handoff / claim events with handles.  
- **Silence windows** — gaps between obligation and response timestamps.  
- **Commitment drift** — scope/schedule/owner deltas with `CommitmentDriftSignal` expectations.  
- **Reopen / retry cycles** — `retry`, `follow_up`, `unresolved_ask` sequences.  
- **Deployment rollback chains** — refs to deploy + revert artifacts where connector provides them.  
- **Fragmented thread continuity** — split threads linked only by **allowed** cross-system rules (see `cross-system-continuity-law.md`).  
- **Late-arriving events** — raw rows appended with timestamps violating naive total order.  
- **Contradictory evidence** — ack vs denial, conflicting anchors — expects **degraded / conflicted** legality, not merged truth.

---

## 3. Corpus artifact model (`corpus_manifest.json` + per-case header)

### 3.1 Required manifest fields

| Field | Description |
|-------|-------------|
| `corpus_id` | Stable string id for the whole bundle. |
| `corpus_schema_version` | Integer; bump when manifest layout changes. |
| `reconstruction_version` | Reducer + rule-pack semantic version (e.g. `slack_exec_rules_v2026_05_13`). |
| `execution_reconstruction_contract_version` | Must match `EXECUTION_RECONSTRUCTION_CONTRACT_VERSION` in code (today `1`). |
| `cases` | Ordered list of `{ "corpus_case_id": "…" }` entries (order defines CI run order). |

### 3.2 Per-case header (`case.json`)

| Field | Description |
|-------|-------------|
| `corpus_case_id` | Unique within corpus. |
| `reconstruction_version` | May pin stricter than manifest for regression pinning. |
| `source_systems` | E.g. `["slack"]`, `["slack","github","linear"]`. |
| `raw_evidence_bundle_refs` | List of `{ "kind": "fixture_file|inline|uri", "ref": "…" }` — **no** opaque blobs without hash. |
| `replay_ordering` | Explicit permutation / late-arrival profile id (e.g. `strict_ts`, `permute_independent_jobs`, `late_github_arrival`). |
| `expected_canonical_execution_entities` | Optional: list of entity ids / shapes under `CanonicalExecutionEntity` contract. |
| `expected_commitments` | List of `commitment_id` + terminal `CommitmentLifecycleState` + optional drift ids. |
| `expected_negative_signals` | List of `{ "signal_kind", "signal_id_or_derivation_key" }`. |
| `expected_continuity_windows` | Intervals / bridge ids per continuity law doc. |
| `expected_chronology_windows` | `ExecutionChronologyWindow` / `ExecutionInteractionWindow` expectations. |
| `expected_causal_chains` | Ordered `ExecutionCoordinationEdge` expectations (`edge_kind`, endpoints). |
| `expected_degradation_classes` | Strings aligned with operator substrate (e.g. `stale_verification`, `replay_skew`) — **enumerated in corpus schema**, not free text. |
| `expected_replay_legality_state` | One of §5 classes. |
| `expected_ambiguity_classes` | Bounded ambiguity buckets (e.g. `ownership_parallel_assignees`, `chronology_partial_order`). |

---

## 4. Replay invariants (constitutional)

**R1 — Entity stability:** Same raw evidence bundle + same `reconstruction_version` ⇒ identical set of **canonical execution entity ids** (where entities are asserted non-optional for the case).

**R2 — Continuity closure:** Reducer-internal sort orders (e.g. lexicographic on `event_id`) **must not** change continuity equivalence classes; only **new evidence** or **explicit rule** changes may.

**R3 — Late arrival:** Late-arriving evidence **may** set `replay_safe_ordering` to `partial` or `unresolved` and emit degradation receipts; it **must not** silently rewrite previously emitted **historical** chronology labels for already-accepted events without a versioned supersession rule.

**R4 — Cross-system linkage:** Any cross-system edge **must** cite `EvidenceLineageHop` with `cross_link` or `normalized_reference` per `execution_reconstruction_contracts.py` — no similarity edges.

**R5 — Walk / index replay (Phase 05):** For corpus slices that include `OrgGraphProjectionV1` ingress, replay-safe walks (where applicable) remain **deterministic** across reruns per `phase-05-walk-replay-doctrine.md` / equivalence doctrine — corpus records **expected walk hashes or structural slices** where in scope.

**R6 — Negative honesty:** Absence-derived signals (`NegativeExecutionSignal`, silence windows) must reappear on replay unless **authoritative** resolving evidence is added to the bundle.

**R7 — Provenance non-loss:** Every expected artifact lists **minimum** `source_raw_record_ids` or lineage hop count floor — validators reject “simplified” outputs.

---

## 5. Replay legality classes

Normative classes for `expected_replay_legality_state`:

| Class | Meaning |
|-------|---------|
| `replay_equivalent` | Full deterministic match to expected artifacts; ordering `strict` where required. |
| `replay_degraded` | Match under declared degradation (e.g. partial order, stale verification); **no silent success**. |
| `replay_partial` | Subset of artifacts verifiable; remainder explicitly `unverifiable` with receipts. |
| `replay_unverifiable` | Honest boundary — missing anchor, missing ref, or policy forbids closure. |
| `replay_conflicted` | Contradictory evidence remains inspectable; conflict receipts emitted; **no** merged narrative resolution. |

---

## 6. Golden-thread scenario families

Each family has **multiple** `corpus_case_id` variants (minimal, hostile, late-arrival). Families:

1. **Escalation thread** — `escalation` + `NegativeSignalKind.ignored_escalation` / `escalation_without_resolution` paths.  
2. **Incident mitigation** — blocker → ack → status_confirmation with dependency refs.  
3. **Scope change** — `CommitmentDriftSignal` `scope` / supersession.  
4. **Delayed follow-through** — `FollowThroughGap`, `silent_delivery_drift`.  
5. **Blocked dependency** — `dependency_reference` + `stale_blocker`.  
6. **Ownership handoff** — `execution_handoff` edges + ledger entries.  
7. **Silent failure** — silence window + unanswered request without sentiment.  
8. **Reopen loop** — `retry` / `repeated_follow_up` with bounded counts.  
9. **Hotfix coordination** — Slack + GitHub explicit refs only.  
10. **Deployment rollback** — deploy + rollback refs when fixtures supply them.  
11. **Cross-system escalation** — Slack escalation referencing Linear issue key in message body **and** Linear raw row with same `NormalizedReference`.

---

## 7. Required verification outputs (normative receipts)

Reducers and replay harness **must** emit (or derive for diff) **machine-checkable receipts** — names are normative targets; wire to existing receipt/hash patterns where present:

| Receipt | Role |
|---------|------|
| **Reconstruction receipt** | Hash over sorted `ConversationExecutionEvent` ids + `coordination_kind` + `extraction_contract_id`. |
| **Continuity receipt** | Hash over continuity bridges / anchor chains admitted for the case. |
| **Chronology receipt** | Hash over `TemporalAnchorChain` + interaction windows **including** `replay_safe_ordering`. |
| **Degradation receipt** | Enumeration of degradation classes + rule ids applied. |
| **Replay legality receipt** | One of §5 + pointer to walk/index replay artifacts when Phase 05 slice included. |
| **Ambiguity receipt** | Bounded ambiguity classes still open + `DeterministicConfidenceSource.unresolved` counts. |

Receipts are **substrate evidence**, not user-facing analytics.

---

## 8. Forbidden behavior

- **Silent continuity mutation** — changing continuity set without new evidence or explicit supersession rule id.  
- **Hidden chronology rewrites** — altering `observed_at_iso` semantics or retroactive ordering without degradation propagation.  
- **Probabilistic replay equivalence** — “mostly the same” is invalid.  
- **Semantic reinterpretation during replay** — no LLM pass, no “what they meant.”  
- **Non-deterministic reducer side effects** — wall-clock, random ids not derived from canonical payload, environment-dependent locale for ordering.

---

## 9. Future package targets (documentation only — **not implemented** in this step)

Planned layout under `backend/src/vector/domains/cortex/verification/`:

```
verification/
  replay_corpus/           # loaders, manifest validation, fixture hashing
  replay_equivalence/      # diff engines, golden diff reporters
  chronology_verification/ # anchor chain + window validators
  continuity_verification/ # bridge + lineage validators vs corpus
  reducer_regression/      # CI wiring, version pins
  golden_threads/          # curated case data + expected artifacts
```

Implementation **must** remain bounded, deterministic, and CI-friendly — no orchestration product, no new runtime services in this doctrine step.

---

## 10. Related doctrine

| Document | Relationship |
|----------|----------------|
| [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md) | Contradictions inside corpus cases. |
| [`../continuity/cross-system-continuity-law.md`](../continuity/cross-system-continuity-law.md) | Lawful cross-system rows in corpus bundles. |
| [`../ingestion/execution-reduction-doctrine.md`](../ingestion/execution-reduction-doctrine.md) | Reducer constitutional rules. |
| `DOCS/cortex/05-traversal/phase-05-replay-integrity-matrix.md` | Walk / async replay constraints where corpus includes OCTS slices. |
