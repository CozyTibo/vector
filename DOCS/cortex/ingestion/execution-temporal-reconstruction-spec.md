# Execution temporal reconstruction spec

**Status:** specification.  
**Doctrine:** [execution-reduction-doctrine.md](./execution-reduction-doctrine.md).  
**Contracts:** `TemporalAnchor`, `TemporalAnchorChain`, `ExecutionInteractionWindow`, `ExecutionChronologyWindow`, `CrossSourceTemporalReference`, `ExecutionLatencyEnvelope`, `ExecutionSilenceWindow`.

---

## 1. Principle

Execution coordination is **fundamentally temporal**. Temporal reconstruction must be **deterministic**: intervals, anchors, and ordering labels are derived from **observed timestamps and monotonic cursors** in raw evidence—not from narrative smoothing or model-imputed “when things really happened.”

---

## 2. Time bases

| Basis | Use |
|-------|-----|
| **Message observed time** | Slack `ts` (converted to ISO) as primary `observed_at_iso` on events. |
| **Ingestion order** | Tie-break only when two messages share identical ts (document connector tie-break: raw row id ascending). |
| **Monotonic cursor** | Export sequence, `event_id`, or API cursor when present → `TemporalAnchor.monotonic_cursor`. |

Wall-clock “processing time” must not alter coordination semantics unless stored as its own diagnostic field (out of scope for reconstruction truth).

---

## 3. `TemporalAnchor` and `TemporalAnchorChain`

### 3.1 Anchor construction

Each anchor binds:

- `observed_at_iso`  
- `connector_origin`, optional `raw_record_id`  
- Stable `anchor_id` derived from `(chain_id, index, raw_record_id|reference fingerprint)` per hashing rules in implementation plan.

### 3.2 `replay_safe_ordering`

| Value | Meaning |
|-------|---------|
| `strict` | All adjacent pairs in chain orderable by (iso, monotonic_cursor, raw_record_id). |
| `partial` | Some pairs equal on time; tie-break applied; documented in lineage. |
| `unresolved` | Contradictory or missing evidence—**no** forced total order; downstream must not pretend strictness. |

---

## 4. `ExecutionInteractionWindow`

**Kinds:** `coordination`, `escalation`, `silence`, `dependency_response`, `handoff`, `ack_sla`.

Rules:

- Windows are **half-open** `[start_iso, end_iso)` unless contract explicitly closes for a given `window_kind` (document per kind).  
- `window_id` = deterministic hash of `(thread_key, window_kind, start_iso, end_iso|sentinel, extraction_contract_id)`.  
- Overlapping windows **allowed** if kinds differ; reducer must document precedence for metrics (e.g. escalation window wins for “active escalation” boolean in thread state).

### 4.1 Silence windows

Derived only when:

1. A prior **ask**, **blocker**, or **escalation** event exists with `observed_at_iso = T0`, and  
2. No qualifying response events (rule table: ack, status_confirmation, blocker resolution template) before `T1`, and  
3. `T1` is either next message ts or policy horizon (e.g. “open silence to channel last message ts”).

Emit `ExecutionSilenceWindow` with `silence_kind`:

- `thread` — silence inside one `thread_key`.  
- `dependency_wait` — silence after `dependency_reference` until linked ref activity (cross-system only when ref resolves).  
- `cross_system` — explicit chain only; never inferred from similarity.

---

## 5. Coordination latency

`ExecutionLatencyEnvelope` is built from **finite populations** of deltas:

- Ask → first ack in-thread (ms).  
- Blocker posted → first “unblocked” or resolver template (ms).  
- Dependency ref cited → first related GitHub/Linear raw (ms) when **same NormalizedReference**.

Fields `p50_ms`, `p95_ms`, `max_ms`, `sample_count` are **deterministic quantiles** over sorted samples for a fixed window. `derivation_rule_id` identifies the quantile definition.

---

## 6. `ExecutionChronologyWindow` and cross-source skew

`ExecutionChronologyWindow` labels intervals used for **merge diagnostics** (not for rewriting Slack times).

`CrossSourceTemporalReference`:

- `skew_detected` when signed delta exceeds connector-configured threshold.  
- `late_arrival` when raw row `fetched_at` ordering disagrees with source-native ts ordering.

---

## 7. Continuity stitching (temporal)

Stitch threads only when:

1. **Explicit** URL or ticket id appears in both, or  
2. `IdentityContinuityRecord` with allowed `IdentityLinkDerivation` (explicit linkage, temporal overlap with **same normalized ref**, shared execution reference, stable org anchor).

Temporal overlap **alone** without shared ref is **weak** and may only produce `unresolved` chain or gap records—never merged “truth.”

---

## 8. Handoff timing and retry cadence

- **Handoff:** edge timestamps = source message ts of handoff message; window `[claim_ts, next_owner_ack_ts)`.  
- **Retry cadence:** count only messages matching retry template **and** linked by reducer to same `open_asks` event id via `temporal_successor` path.

---

## 9. Commitment aging (temporal view)

For each `ExecutionCommitment` with `expected_completion_iso`:

- `FollowThroughGap` when `now_evidence_iso` (latest raw in scope) exceeds expected by policy without completion signal.  
- “Aging” is a **duration**, not a judgment label.

---

## 10. Forbidden temporal behavior

- Imputing missing timestamps.  
- Shifting user messages to “fix” ordering.  
- Inferring work hours, timezone intent, or “business day” adjustments unless encoded as explicit tenant policy with rule id (future; default none).

---

## 11. Replay invariants

- **T1:** Replaying the same raw sequence yields identical window set and anchor chain ids.  
- **T2:** Inserting a new message at end only extends windows; does not change prior window ids.  
- **T3:** `unresolved` ordering never upgrades to `strict` without new evidence.

---

## 12. Admin / substrate debugging

Show: anchor chains per thread, silence windows on timeline, latency envelope inputs (histogram bucket counts), skew flags, and `derivation_rule_id` for each window.
