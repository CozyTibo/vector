# Execution commitment reconstruction spec

**Status:** specification.  
**Doctrine:** [execution-reduction-doctrine.md](./execution-reduction-doctrine.md).  
**Contracts:** `ExecutionCommitment`, `CommitmentLifecycle`, `CommitmentLifecycleState`, `CommitmentDriftSignal`, `CommitmentResolutionState`, `FollowThroughGap`.

---

## 1. Objective

Reconstruct **deterministic commitment state machines** from operational evidence: Slack commitment statements, acknowledgements, GitHub/Linear activity **only when linked by explicit references or stable handles**, escalation continuity, and thread continuity—without probabilistic “did they mean it?” inference.

---

## 2. Inputs

| Source | Allowed use |
|--------|-------------|
| Slack messages | Phrases matched by `delivery_promise` / `commitment` rules; @mentions; timestamps. |
| Slack thread structure | Ordering for lifecycle transitions. |
| GitHub / Linear raw | State transitions only when `NormalizedReference` matches commitment `commitment_subject_refs` or `dependency_assumption_refs`. |
| Escalation events | Move lifecycle toward `escalated` / `stalled` per tables—never “because manager was angry.” |

---

## 3. `ExecutionCommitment` fields (semantic rules)

- `commitment_id`: deterministic hash of sorted evidence keys + `extraction_contract_id`.  
- `committed_by_handle`: `{provider, external_id}` from Slack user id mapping—no display-name-only identity.  
- `commitment_subject_refs` / `dependency_assumption_refs`: only resolver-backed references.  
- `acknowledgement_event_ids`: list of `ConversationExecutionEvent.event_id` values that are `acknowledgment` or `status_confirmation` linked by edges.  
- `expected_completion_iso`: parsed only via **explicit date/time patterns** or relative phrases mapped by fixed policy table (e.g. “tomorrow” = tenant-local midnight rule with rule id); if ambiguous → `null` + `uncertainty` event, not guessed ISO.  
- `follow_through_event_ids`: retries, pings, follow-ups tied by derivation rules.  
- `lifecycle_state`: one of `CommitmentLifecycleState`.

---

## 4. Lifecycle transitions (`CommitmentLifecycleState`)

Normative transition table (rows = from → to allowed with evidence type). Implementation must encode this table as data + tests.

| From | To | Minimum evidence |
|------|----|-------------------|
| `proposed` | `acknowledged` | Ack event in-thread referencing same subject ref or reply to proposal message. |
| `proposed` | `accepted` | Stronger acceptance template (“approved”, “go ahead”) per rule pack. |
| `acknowledged` / `accepted` | `active` | Work signal: first linked GitHub push/PR or Linear state change on same ref, or explicit “started”. |
| `active` | `blocked` | `blocker` event linked to commitment via `blocks` edge. |
| `active` | `escalated` | `escalation` event + temporal successor policy. |
| `active` | `completed` | `status_confirmation` + completion template or terminal GitHub merged / Linear done with same ref. |
| `*` | `stalled` | Silence window exceeds policy while `active` or `blocked` (temporal spec). |
| `*` | `abandoned` | Explicit abandonment language **or** thread archived + no activity policy (connector-specific, rule id required). |
| `*` | `drifted` | `CommitmentDriftSignal` emitted (scope/schedule/owner change). |
| `*` | `superseded` | New commitment event with supersession template referencing prior `commitment_id` in lineage. |

**Illegal:** Transition without at least one new `ConversationExecutionEvent` or raw-backed negative signal in lineage.

---

## 5. `CommitmentLifecycle.state_history`

Each entry: `{at_iso, state, rule_id}` sorted deterministically:

1. By `at_iso` ascending.  
2. Tie-break by `rule_id`, then by lexicographic `state`.

No concurrent “best guess” states—single current_state.

---

## 6. `CommitmentDriftSignal`

`drift_kind` ∈ `scope | owner | schedule | dependency | ack | supersession`.

Emit when:

- **Scope:** new ref added without supersession template.  
- **Owner:** `execution_handoff` edge touches same subject ref.  
- **Schedule:** new `expected_completion_iso` differs with both ISOs non-null.  
- **Dependency:** new `dependency_assumption_refs` edge.  
- **Ack:** contradiction between ack and subsequent denial template.  
- **Supersession:** explicit replacement string.

Each signal carries `evidence_lineage` and `rule_id`.

---

## 7. `CommitmentResolutionState`

- `resolved` when `completed` or definitive `abandoned` / `superseded` with evidence.  
- `unverifiable` when required cross-system evidence never arrives within policy window—**honest bound**, not failure hiding.

---

## 8. `FollowThroughGap`

Computed when:

- `expected_completion_iso` is non-null and past, and  
- No `completed` / superseding resolution, and  
- `last_evidence_iso` is last observed related activity.

`gap_seconds = last_evidence_iso - expected_completion_iso` (or null if open-ended).

---

## 9. Cross-system continuity (GitHub / Linear)

**Allowed:**

- Same URL / issue key / repo+number in Slack and in GitHub/Linear raw → merge into commitment evidence and lifecycle transitions.

**Forbidden:**

- Matching by “similar title” or fuzzy author name without stable id.

---

## 10. Bounded ambiguity

- If two commitments compete for same message: **precedence table** in `slack_execution_patterns.py` + deterministic “primary” commitment id in lineage of secondary.  
- If date parsing ambiguous: no `expected_completion_iso`; use `FollowThroughGap` only after relative policy resolves with explicit rule.

---

## 11. Replay invariants

- **C1:** Same evidence stream ⇒ same `commitment_id` and `state_history` byte-identical (canonical JSON).  
- **C2:** Out-of-order raw arrival updates only `unverifiable` or `stalled` per policy—never retroactively deletes prior valid transitions.  
- **C3:** Drift signals append-only until commitment superseded or abandoned.

---

## 12. Admin / substrate debugging

Show: lifecycle timeline, drift signals, linked raw ids, cross-system ref matches, and resolution state with reasons (`rule_id`).
