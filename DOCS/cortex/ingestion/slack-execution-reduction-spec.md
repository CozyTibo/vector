# Slack execution reduction spec

**Status:** specification (implementation follows).  
**Parent doctrine:** [execution-reduction-doctrine.md](./execution-reduction-doctrine.md).  
**Contracts:** `execution_reconstruction_contracts.py`.

---

## 1. Purpose

Evolve Slack ingestion from **message capture** to **execution coordination reconstruction**: bounded, schema-first emission of `ConversationExecutionEvent`, `ExecutionCoordinationEdge`, `ExecutionThreadState`, `ExecutionInteractionWindow`, commitment artifacts, negative signals, and temporal structures—**without** semantic summarization or ML inference.

---

## 2. Inputs (allowed evidence)

| Input | Use |
|-------|-----|
| Raw Slack records (stored rows) | **Primary** ground truth; every event cites `source_raw_record_ids`. |
| Connector-native structured fields | User ids, team ids, channel ids, thread_ts, message ts, reply hierarchy, reactions **as facts** (not emotional interpretation). |
| Normalized references (`NormalizedReference`) | Phase 3.5 handles: URLs, ticket ids, repo/issue refs when present in text or attachments per resolver rules. |
| Frozen pattern / rule packs | Regex/keyword/grammar tables versioned under `extraction_contract_id` (not model names). |

**Out of scope for v1 reducers:** free-form summarization, embedding nearest-neighbor, cross-tenant statistics as labels.

---

## 3. Thread and message keys

- **`source_thread_key`:** Deterministic string from `(connection_id, channel_id, thread_ts | root_ts)` per connector mapping doc (stable across replays).  
- **`source_message_keys`:** Ordered list of contributing message identifiers (e.g. `channel:ts` or API ids) for the event—minimal set that suffices for lineage.

Replay invariant: keys derive **only** from raw payload fields + connection scope, never from wall-clock “now.”

---

## 4. Deterministic extraction rules (Slack)

### 4.1 Ask family → `request` / `unresolved_ask` / `dependency_reference`

| Pattern class | Example cue (rule-defined, not open-ended) | `ExecutionCoordinationKind` |
|---------------|---------------------------------------------|-------------------------------|
| Explicit request | Imperative + assignee @mention or “can someone” templates | `request` |
| Dependency ask | Blocked on external ref (URL, Jira, Linear) | `dependency_reference` |
| Unblock ask | Template pack for “unblock”, “waiting on” | `request` |

**Rule:** If the message is both ask and commitment language, **split** into multiple events only when separate rule ids fire; otherwise single event with **higher-precedence** table (specify in `slack_execution_patterns.py` data: precedence order is data, not code branch magic).

### 4.2 Acknowledgement family → `acknowledgment` / `status_confirmation`

- Short affirmative replies to a prior ask in-thread link by **temporal_successor** edge + `source_message_keys` including parent.  
- “LGTM”, “on it”, “ack” templates → `acknowledgment` with `EXPLICIT_RULE_ID`.  
- Explicit state flips (“deployed”, “merged”) with URL → `status_confirmation` + `normalized_references`.

### 4.3 Blocker → `blocker`

- “blocked on”, “can’t proceed until”, “waiting for” + reference or named dependency.  
- No blocker event if only vague delay with no dependency token unless `coordination_gap` with `UNRESOLVED`.

### 4.4 Escalation → `escalation`

- @here / @channel / “escalating” / explicit manager ping per rule pack.  
- Escalation **propagation** across messages is **edge** `escalation_of` (see §6).

### 4.5 Ownership → `ownership_claim` / `execution_handoff`

- Self-claim: “I’ll take this”, “mine”, “I own” per patterns.  
- Handoff: explicit “passing to @user” with both handles present in structured fields.

### 4.6 Retry / follow-up → `retry` / `follow_up`

- Same ask restated after silence window (see temporal spec).  
- Bump `retry_count` in `ExecutionThreadState` only from **countable** rule matches tied to prior ask `event_id`.

### 4.7 Delivery / commitment language → `delivery_promise` / `commitment`

- Time-bound promises → `delivery_promise` + optional `ExecutionCommitment` when lifecycle rules fire (commitment spec).  
- “Done”, “shipped”, “merged” with evidence ref → feeds commitment resolution, not a new vague “success” label.

### 4.8 Negative space (derivation, not message class)

- Unanswered ask, ignored escalation, stalled blocker → **`NegativeExecutionSignal`** per [negative-execution-signal-spec.md](./negative-execution-signal-spec.md), not a positive coordination kind pretending to be psychology.

---

## 5. Confidence and provenance

Every `ConversationExecutionEvent` must set:

- `confidence_source` ∈ `DeterministicConfidenceSource`  
- `extraction_contract_id` = stable id of the Slack rule pack version (e.g. `slack_exec_rules_v2026_05_01`)  
- `evidence_lineage` including at least one `raw_record` hop

Forbidden: numeric “0.95 confidence” without a declared source enum.

---

## 6. Edges (`ExecutionCoordinationEdge`)

| `edge_kind` | Slack use |
|-------------|-----------|
| `temporal_successor` | Message N → N+1 in same `thread_key` (same channel + thread_ts ordering by ts). |
| `escalation_of` | Escalation event → prior blocker/request event in same thread. |
| `blocks` | Blocker event → blocked request/commitment id. |
| `depends_on` | Dependency reference → normalized ref target (if resolved). |
| `handoff` | Ownership transfer pair. |
| `same_thread` | Coarse clustering only when finer edge missing (prefer specific kinds). |

`derivation_rule_id` required on each edge.

---

## 7. Reducer module responsibilities (file map)

| Module | Responsibility |
|--------|----------------|
| `slack_execution_reducer.py` | Raw message batch → ordered `ConversationExecutionEvent` list + `ExecutionCoordinationEdge`. |
| `slack_execution_windows.py` | `ExecutionInteractionWindow` (coordination / escalation / silence / dependency_response / handoff / ack_sla). |
| `slack_commitment_reconstruction.py` | `ExecutionCommitment`, `CommitmentLifecycle`, drift signals from Slack evidence. |
| `slack_negative_signal_derivation.py` | `NegativeExecutionSignal`, `FollowThroughGap`, `CoordinationFailurePattern` assembly. |
| `slack_coordination_state.py` | Deterministic fold → `ExecutionThreadState`. |
| `slack_temporal_reconstruction.py` | `TemporalAnchorChain`, silence windows, latency envelopes. |
| `slack_execution_patterns.py` | Declarative pattern tables + precedence; **no** inline ad-hoc regex in reducers. |

---

## 8. Cross-thread linkage (bounded)

Allowed:

- Same `NormalizedReference` appearing in two threads → `CrossSourceTemporalReference` / future cross-thread edge (contract extension gated).  
- Explicit URL posted in thread A and thread B.

Forbidden:

- “These two threads feel related” without shared ref or explicit user link.

---

## 9. Replay and ordering

- Process messages in **strict ts order** per `(channel_id, thread_ts)`.  
- Edits / deletes: follow raw-store policy; reducers consume **versioned** raw facts only.  
- Late-arriving messages insert with correct temporal edges; **no rewriting** of historical `event_id` hashes—new events get new ids.

---

## 10. Testing obligations (when implemented)

- Golden-thread fixtures: small JSONL of raw Slack rows → expected sorted event ids + edges.  
- Property: removing a non-cited raw row from input does not change unrelated events’ ids (lineage isolation).  
- Negative tests: forbidden phrases must **not** produce coordination kinds (e.g. “frustrated” → no event).

---

## 11. Admin / substrate debugging

Surfaces must list: emitted events per `thread_key`, edges, windows, negative signals, and **full lineage hop list** drill-down to raw ids. Not a user dashboard—operator substrate.
