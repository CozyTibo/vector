# Phase 08.5 — Traversal completion doctrine

**Status:** normative.  
**Implements:** Steps 14–17 · **G-P085-WALK-01..04**.

---

## Automatic walk scheduling (**G-P085-WALK-01**)

After phase **05** completes (or graph density ≥ G1):

- Enqueue `schedule_octs_walks_for_tenant_v1` with bounded fanout
- Priority: connected components with highest `graph_density_score`
- Cap: `CORTEX_TRAVERSAL_MAX_WALKS_PER_PASS` (default 32)

**Continuation:** `waiting_on = TRAVERSAL_COMPLETION` when batch async (future).

---

## Retry & frontier healing (**G-P085-WALK-02**)

| Failure | Retry policy |
| ------- | ------------ |
| transient store error | exponential backoff, max 3 |
| legality `walk_incomplete` | no retry; explain |
| frontier collapse | frontier_heal pass |

---

## Stalled traversal recovery (**G-P085-WALK-03**)

Detect: `pending_walks > 0` AND `last_walk_completed_at > T_stall`.

Actions: re-enqueue pending walks, cancel poison walks to DLQ.

---

## Explainability (**G-P085-WALK-04**)

Operator panel MUST answer:

- Why walks pending?
- Why walk terminated early?
- Replay posture per walk
- Upstream graph omissions causing block

**Metrics:** `walks_completed_rate`, `walks_pending_gauge`, `traversal_density_score`.

---

## Traversal density

`traversal_density = completed_walks_with_payload / eligible_graph_frontiers`

Target for **OPERATIONAL_ALIVE:** ≥ **0.5** when graph at G1+.
