# Execution thread state spec

**Status:** specification.  
**Doctrine:** [execution-reduction-doctrine.md](./execution-reduction-doctrine.md).  
**Slack mapping:** [slack-execution-reduction-spec.md](./slack-execution-reduction-spec.md).  
**Contract:** `ExecutionThreadState` in `execution_reconstruction_contracts.py`.

---

## 1. Role of `ExecutionThreadState`

`ExecutionThreadState` is the **deterministic fold** of all `ConversationExecutionEvent`, `ExecutionCoordinationEdge`, windows, and negative signals for one `thread_key`. It is the operator-facing summary of **coordination mechanics** for a thread—not a summary of conversation content.

---

## 2. Field semantics

| Field | Deterministic meaning |
|-------|------------------------|
| `thread_key` | Same as events’ `source_thread_key`. |
| `open_asks` | List of `event_id` for `request` / `unresolved_ask` not closed by ack / resolution / explicit cancel template. **Sorted** lexicographically by `event_id`. |
| `unresolved_blockers` | `event_id` for `blocker` without paired resolution event per rule table. Sorted. |
| `stale_coordination` | `event_id` referenced by `stale_blocker`, `abandoned_coordination_thread`, or silence policy—subset of asks/blockers. Sorted. |
| `escalation_chain_event_ids` | All `escalation` events in thread, `temporal_successor` order, then by `event_id` for tie-break. |
| `acknowledgment_state` | `none`: no ack events. `partial`: some asks acked, others not. `complete`: all current asks have ack path. `contradicted`: ack + denial on same subject per rule. |
| `ownership_continuity_ok` | `true` iff every open ask has an owner handle or ownership_claim path; else `false`. |
| `latest_execution_state` | Small enumerated string from fixed set (e.g. `quiet`, `active_coordination`, `blocked`, `escalated`, `stalled`) derived by **priority table** over current signals—not free text. |
| `last_meaningful_interaction_iso` | Latest `observed_at_iso` among non-ambient messages (ambient list = bot-only / reaction-only per rule pack); `null` if none. |
| `silence_duration_seconds` | If last obligation ts `T_req` and last response ts `T_resp` (or horizon), `T_now - T_req` per temporal spec; `null` if no open obligation. |
| `retry_count` | Integer count of `retry` / `follow_up` events linked to same open ask root. |

**Naming note:** `last_meaningful_interaction_iso` is legacy naming in the TypedDict; semantically it is **last coordination-relevant interaction** under rule pack `meaningful_interaction_v1`—never “semantic meaningfulness.” A future contract version may alias the field; until then, document the rule id in reducer output metadata (separate diagnostics field if needed).

---

## 3. Fold algorithm (normative)

Input: ordered list of events `E` for `thread_key`, edges `G`, windows `W`, negative signals `N`.

1. Sort `E` by `(observed_at_iso, raw_record_id tie-break)`.  
2. Build adjacency from `ExecutionCoordinationEdge` restricted to kinds that affect state (`temporal_successor`, `blocks`, `escalation_of`, `handoff`).  
3. Single forward pass maintaining:  
   - Open ask set (add on request; remove on ack linked by edge or template).  
   - Blocker set.  
   - Escalation list append-only.  
4. Post-pass: compute `acknowledgment_state` from ask/ack pairing table.  
5. Merge `N` to populate `stale_coordination` and silence duration.  
6. Emit `ExecutionThreadState` with all list fields sorted.

**Determinism:** Same `E,G,W,N` ⇒ identical output. Order of reducer internal iteration must not depend on hash map enumeration—sort keys explicitly.

---

## 4. `latest_execution_state` priority table (example — freeze in implementation data)

Higher row wins (first match):

1. `escalated` if any open escalation without resolution.  
2. `blocked` if `unresolved_blockers` non-empty.  
3. `stalled` if any `stale_coordination` or `FollowThroughGap` open.  
4. `active_coordination` if open asks or active commitments.  
5. `quiet` otherwise.

Exact strings and precedence must live in versioned data with `derivation_rule_id`.

---

## 5. Relationship to other artifacts

- **Thread state** does not duplicate full event payloads; it references `event_id` only.  
- **Negative signals** may be derived from thread state **or** thread state may incorporate signals—choose one direction in implementation to avoid cycles (recommended: events → signals → thread state in that order).

---

## 6. Cross-thread fields

Default `ExecutionThreadState` is **per thread_key**. Cross-thread aggregates are **out of scope** for this contract object; use separate admin queries or future `CanonicalExecutionEntity` scopes.

---

## 7. Bounded ambiguity

- If ack could close multiple asks: **closest temporal predecessor** ask in same thread wins; if ambiguous tie, close **lowest lexicographic** `event_id` and record `coordination_gap` on others (optional).  
- Contradicted ack/deny sets `acknowledgment_state = contradicted` and does not auto-resolve.

---

## 8. Replay invariants

- **S1:** Reordering non-concurrent messages with same ts uses raw_record_id tie-break consistently with events.  
- **S2:** Thread state idempotent: folding already-folded events + append-only new tail equals full refold.  
- **S3:** `silence_duration_seconds` recomputed from same policy inputs only.

---

## 9. Testing obligations

- Matrix tests for ack_state transitions.  
- Contradiction case: ack + deny.  
- Multi-ask partial ack.

---

## 10. Admin / substrate debugging

Show: open asks as links to events, blocker graph, escalation chain timeline, ownership path, and raw lineage for `last_meaningful_interaction_iso` rule hits.
