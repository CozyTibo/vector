# Negative execution signal spec

**Status:** specification.  
**Doctrine:** [execution-reduction-doctrine.md](./execution-reduction-doctrine.md).  
**Contracts:** `NegativeExecutionSignal`, `NegativeSignalKind`, `CoordinationFailurePattern`, `FollowThroughGap`, `ExecutionSilenceWindow`.

---

## 1. Principle

Negative signals model **absence and coordination failure as operational facts**: unanswered requests, unresolved blockers, stalled threads, missing ownership, dependency silence, etc.

They are **not**:

- People-performance scores.  
- Emotional or motivational judgments.  
- “This person is bad at responding.”

Copy in admin UIs must say **coordination state**, not character.

---

## 2. `NegativeSignalKind` usage (contract-aligned)

Each row: kind → **deterministic trigger** (all require `causal_event_ids` + lineage).

| Kind | Operational fact (examples) |
|------|------------------------------|
| `unanswered_request` | `request` / `unresolved_ask` with no linked `acknowledgment` / `status_confirmation` before silence threshold. |
| `ignored_escalation` | `escalation` followed by silence window with no `acknowledgment` from targeted handles. |
| `stale_blocker` | `blocker` older than policy without resolution template or dependency activity. |
| `ownership_vacuum` | Ask or commitment without `ownership_claim` and without assignee resolution. |
| `abandoned_coordination_thread` | Thread silence after active coordination window + no new events. |
| `missing_acknowledgment` | Explicit policy requiring ack (e.g. @here) with none recorded. |
| `repeated_follow_up` | Retry count ≥ N from `slack_coordination_state` reducer. |
| `dependency_without_owner` | `dependency_reference` with no owning handle on resolution path. |
| `pr_without_social_response` | GitHub PR ref cited in Slack with no in-thread follow-up (cross-system rule pack). |
| `silent_delivery_drift` | `delivery_promise` due with no `status_confirmation` / completion ref. |
| `unresolved_commitment` | `CommitmentLifecycleState` in {`active`, `blocked`, `escalated`, `stalled`} past policy horizon. |
| `escalation_without_resolution` | Escalation active with no downstream `completed` / de-escalation template. |

New kinds require contract enum bump + this doc update.

---

## 3. Severity (`severity_derivation`)

Only values: `rule_severity_v1`, `rule_severity_v2`, `connector_native`.

**Rule tables** map (signal_kind, duration_seconds bucket, thread depth) → severity tier. No learned weights.

---

## 4. Causal graph

- `causal_event_ids` lists **positive** coordination events that define the obligation (ask, blocker, escalation, commitment).  
- Negative signal **does not** replace those events; it references them.  
- `affected_entity_refs`: `NormalizedReference` to tickets, PRs, channels (as stable refs)—not “the team.”

---

## 5. Duration fields

`duration_seconds` on `NegativeExecutionSignal`:

- For silence-based signals: `end_iso - start_iso` from `ExecutionSilenceWindow` or message ts difference.  
- Must be `null` when signal is instantaneous (e.g. single-message detection of vacuum) unless policy defines instant as zero vs null—pick one in implementation and test.

---

## 6. `CoordinationFailurePattern`

Bundles multiple `signal_id` into a named `pattern_id` when:

- All members share same `thread_key` or same `NormalizedReference`, and  
- `derivation_rule_id` defines the bundle (e.g. “unanswered + escalation + silence”).

Patterns are **diagnostic**, not scoring.

---

## 7. Escalation propagation (negative lens)

1. Detect escalation event `E`.  
2. Build targeted handle set from structured mentions.  
3. If no ack from **any** targeted handle within `T_esc`, emit `ignored_escalation` or `escalation_without_resolution` per precedence table.  
4. Propagation to parent channel threads only when raw shows cross-post or explicit link—not guessed.

---

## 8. Silence and negative derivation

Silence alone is insufficient unless a **prior obligation** exists:

- Ask, blocker, commitment due, or escalation.  
- Otherwise silence is ambient noise, not a signal.

---

## 9. Forbidden derivations

Never emit negative signals for:

- Low message count “because channel is quiet.”  
- User offline / timezone without explicit policy.  
- Sentiment heuristics.

---

## 10. Replay invariants

- **N1:** Removing unrelated messages does not flip a signal’s presence if causal ids unchanged.  
- **N2:** Signal `signal_id` deterministically derived from `(kind, causal_event_ids sorted, window bounds, extraction_contract_id)`.  
- **N3:** Late arrival of ack **removes** derivable signal in full replay (signal not emitted) rather than mutating old signal rows—append-only store may tombstone via new run id per ingestion policy.

---

## 11. Admin / substrate debugging

Show: causal event drill-down, silence interval, rule id, severity table version, and “why not fired” for nearby candidates (debug mode only).
