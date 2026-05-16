# Phase 07 — Temporal retrieval doctrine

**Status:** normative.

---

## Temporal scope object (`temporal_scope_v1`)

| Field | Use |
| ----- | --- |
| `t_as_of_unix_ns` | Point-in-time snapshot (primary) |
| `window_start_ns` / `window_end_ns` | Half-open chronology window |
| `replay_epoch` | OCTS / TCRE traversal epoch pin |
| `export_sequence` | Canonical export pin when graph-scoped |
| `graph_as_of_unix_ns` | OCTS temporal anchor alignment |

**RULE RET‑TEMP‑01:** `t_as_of` MUST NOT rewrite history — only select artifacts **valid at** T per Phase 06 interval law.

---

## Query patterns (lawful)

| Pattern | Workload class | Behavior |
| ------- | -------------- | -------- |
| Execution state as of T | `materialization_as_of` | Latest mat ≤ T + chronology receipt at T |
| Continuity evolution | `chronology_window` | Ordered receipts in window |
| Degradation over time | `degradation_survey` | Sorted `CD-*` / `RD-*` by window |
| Ownership transitions | `ownership_continuity` | Authoritative links valid at T (+ omissions for gaps) |
| Replay epoch compare | `replay_equivalence` | Two pinned epochs — structural diff only |

---

## Replay-safe temporal semantics

| Rule | Text |
| ---- | ---- |
| **RET‑TEMP‑02** | Temporal queries MUST pin `tcre_policy_bundle_digest` when reading TCRE artifacts. |
| **RET‑TEMP‑03** | Late-arrival materializations after `t_as_of` MUST NOT appear — omission `omitted_temporal_future`. |
| **RET‑TEMP‑04** | Skew flags from Phase 06 MUST copy to hit provenance — not recompute. |

---

## Temporal legality envelope

Aggregate:

| Condition | Legality |
| --------- | -------- |
| All chronology strict in window | contributes to `retrieval_replay_safe` |
| Any `chronology_degraded` in window | floor `retrieval_degraded` |
| Window crosses replay conflict | `retrieval_unverifiable` |

---

## Forbidden

- Predicting future states  
- Interpolating timestamps not in receipts  
- “Most recent” fuzzy without deterministic tie-break (use lexicographic key from Phase 06)
