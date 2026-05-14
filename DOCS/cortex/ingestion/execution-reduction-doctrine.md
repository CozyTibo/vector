# Execution reduction doctrine (Phases 01–03)

**Status:** normative doctrine (spec-first).  
**Scope:** deterministic reconstruction of **execution coordination mechanics**, not conversational “meaning.”  
**Code anchor:** `backend/src/vector/domains/cortex/ingestion/execution_reconstruction_contracts.py` (`EXECUTION_RECONSTRUCTION_CONTRACT_VERSION = 1`).

---

## 1. Strategic objective

Cortex is not optimizing for “understanding conversations.” It is optimizing for **deterministic reconstruction of execution coordination reality**: asks, acknowledgements, blockers, ownership, retries, follow-ups, silence, escalations, commitments, dependency references, handoffs, confirmations, and **execution drift** evidenced by operational facts.

The next bottleneck is **evidence quality**: high-fidelity, bounded, replay-safe extraction from real activity (Slack first), not more graph surface area.

---

## 2. Constitutional rules

### 2.1 Required properties

| Property | Meaning |
|----------|---------|
| **Deterministic derivation** | Same ordered raw inputs + same `extraction_contract_id` + same rule pack version ⇒ same emitted artifacts (including ids where derived by canonical hashing). |
| **Replayability** | Re-running ingestion/reconstruction on a fixed raw slice reproduces artifacts; no hidden RNG, no wall-clock–dependent labels except where explicitly encoded as observed timestamps from evidence. |
| **Provenance lineage** | Every `ConversationExecutionEvent`, edge, window, commitment, and negative signal carries **non-empty** `source_raw_record_ids` and/or explicit `EvidenceLineageHop` chain per contract validators. |
| **Explainability** | Every coordination label is attributable to: connector-native field, explicit rule id, pattern id, temporal derivation, or cross-reference—not to an opaque model. |
| **Evidence traceability** | `DeterministicConfidenceSource` and `extraction_contract_id` are mandatory semantics for “why this label exists.” |
| **Bounded extraction** | Only `ExecutionCoordinationKind` (and contract-approved extensions via version bump) may label primary events; unknown behavior remains `uncertainty` / `coordination_gap` / explicit omission—not free-text inference. |
| **Temporal continuity** | Ordering uses ingestion-observable timestamps and monotonic cursors where available; gaps are **declared** (`TemporalAnchorChain.replay_safe_ordering`), not smoothed by narrative. |

### 2.2 Forbidden classes (hard boundary)

The execution reduction layer **must not** emit or depend on:

- Semantic summarization of threads or “what was discussed.”
- Embeddings, vector similarity, or cluster-derived “themes.”
- LLM-driven execution state, “importance,” or motivational/psychological attributes.
- Probabilistic graph semantics or opaque confidence (all confidence is **source-tagged**, not calibrated belief).
- Autonomous orchestration or agentic planning over Slack.
- People-performance judgments disguised as “insights.” **Negative signals are coordination facts**, not HR scores.

---

## 3. Good vs bad extraction (normative examples)

**Evidence (Slack message text is only one input; structure matters).**

*Message:* “I’ll take care of this tomorrow after API review.”

**Allowed** (examples; each requires rule id + raw ids):

- `ownership_claim` — explicit self-assignment language matched by pattern/rule pack.
- `delivery_promise` — time-bound completion language tied to rule id.
- `dependency_reference` — “after API review” linked only if resolver maps to a **stable handle** (e.g. URL, ticket id, channel+ts) per cross-reference rules—not guessed intent.

**Forbidden** labels (never stored as coordination truth):

- “high confidence engineer,” “motivated,” “priority task,” “likely frustrated,” “team tension,” “important discussion.”

---

## 4. Artifact family (contract names)

Downstream reducers **emit** instances of (non-exhaustive; see Python contracts):

- `ConversationExecutionEvent`
- `ExecutionCoordinationEdge`
- `ExecutionThreadState`
- `ExecutionInteractionWindow`
- `ExecutionCommitment` + `CommitmentLifecycle` + `CommitmentDriftSignal`
- `NegativeExecutionSignal` + `FollowThroughGap` + `ExecutionSilenceWindow`
- Temporal: `TemporalAnchor`, `TemporalAnchorChain`, `ExecutionChronologyWindow`, `CrossSourceTemporalReference`, `ExecutionLatencyEnvelope`

Cross-system stitching (Slack ↔ GitHub ↔ Linear) uses **explicit references, stable handles, temporal overlap, shared execution references** per `IdentityLinkDerivation`—never probabilistic identity guessing.

---

## 5. Bounded ambiguity

When evidence is insufficient for a discrete label:

1. Prefer **no event** over a weak event; or  
2. Emit `uncertainty` / `coordination_gap` with `confidence_source = UNRESOLVED` and minimal lineage; or  
3. Emit **negative space** (`NegativeExecutionSignal`, silence window) when absence is itself rule-defined.

Ambiguity is **bounded**: open sets are listed in specs; everything else is out of scope until a contract version bump.

---

## 6. Replay invariants (summary)

- **I1 — Raw grounding:** No coordination event without positive integer `source_raw_record_ids` (validator-enforced).
- **I2 — Stable identity:** `event_id` derived from canonical sorted payload + `extraction_contract_id` (see `derive_conversation_execution_event_id`).
- **I3 — Monotonic merge:** Thread-local ordering respects Slack message order within a channel/thread key; late arrivals flagged, not silently re-authored.
- **I4 — Negative honesty:** Silence/stale/unanswered derived only from **observed timestamps and explicit ask/blocker state**, not from “tone.”
- **I5 — No retroactive emotion:** State transitions on commitments and threads use evidence timestamps only.

---

## 7. Module layout (implementation placeholder — not built in this doc pass)

Planned package (implementation follows specs):

`backend/src/vector/domains/cortex/ingestion/execution_reducers/`

- `slack_execution_reducer.py` — message/thread → events + edges  
- `slack_execution_windows.py` — `ExecutionInteractionWindow`, silence slices  
- `slack_commitment_reconstruction.py` — `ExecutionCommitment`, lifecycle history  
- `slack_negative_signal_derivation.py` — `NegativeExecutionSignal`, `FollowThroughGap`  
- `slack_coordination_state.py` — `ExecutionThreadState` fold  
- `slack_temporal_reconstruction.py` — anchors, chains, latency envelopes  
- `slack_execution_patterns.py` — shared pattern tables (pure data + rule ids)

---

## 8. Admin / debugging (substrate-only)

Operator surfaces must expose **reconstruction artifacts and lineage**, not end-user “intelligence.” See sibling specs for required views: reduction outputs, commitments, silence, escalation chains, provenance, temporal ordering, replay equivalence checks, negative-signal derivation traces.

---

## 9. Related documents

| Document | Role |
|----------|------|
| [slack-execution-reduction-spec.md](./slack-execution-reduction-spec.md) | Slack-specific inputs, keys, reducer responsibilities |
| [execution-temporal-reconstruction-spec.md](./execution-temporal-reconstruction-spec.md) | Time, silence, latency, handoff timing |
| [execution-commitment-reconstruction-spec.md](./execution-commitment-reconstruction-spec.md) | Lifecycle, drift, cross-system evidence |
| [negative-execution-signal-spec.md](./negative-execution-signal-spec.md) | Absence and coordination failure (operational facts) |
| [execution-thread-state-spec.md](./execution-thread-state-spec.md) | Per-thread deterministic fold |

---

## 10. Change control

Any new `ExecutionCoordinationKind`, `NegativeSignalKind`, or lifecycle state requires:

1. Contract version strategy (bump `EXECUTION_RECONSTRUCTION_CONTRACT_VERSION` or additive extension policy).  
2. Validator updates in `execution_reconstruction_contracts.py`.  
3. Negative tests proving old replays stay stable or migrate under explicit migration rules.
