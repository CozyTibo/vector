# Phase 08.5 — Endgoal doctrine (operational aliveness)

**Status:** normative.

---

## Target end state

Cortex tenants **continuously progress** from connected workspaces to **published retrieval index** and **synthesis artifacts** without operator rituals, while remaining **replay-safe** and **legally bounded**.

---

## Non-goals

- Semantic “understanding” beyond Phase 08 synthesis law
- Product UX (Phase 09)
- Replacing Phase 04–08 constitutional gates

---

## Operational invariants (CESP-INV)

| Id | Invariant |
| -- | --------- |
| **INV-01** | No pipeline run may remain `WAITING` on TCRE beyond `T_stall` without escalation (watchdog or alert) |
| **INV-02** | `eligible_scopes = 0` with completed TCRE + completed walks MUST classify as **starvation**, not **healthy idle** |
| **INV-03** | Published retrieval epoch with `entry_count = 0` MUST emit `retrieval_index_empty` omission + materialization report |
| **INV-04** | Resume of phase 07/08 MUST be idempotent (no duplicate publish epochs per resume receipt) |
| **INV-05** | Admin completeness cards MUST distinguish **healthy_idle** vs **operational_starvation** |
| **INV-06** | Autonomous recovery MUST NOT bypass legality (no force-publish forbidden synthesis) |

---

## Fake-green prohibition (**G-P085-ANTI-IDLE-01**)

Stages **graph, traversal, tcre, retrieval, synthesis** MUST NOT report `substrate_state = healthy` when:

- `eligible > 0` AND `processed = 0`, OR
- upstream stage reports blocking omission with `propagates_to` this stage, OR
- `continuation_status = WAITING|STALLED` for this pipeline run.

**Exception:** explicit `healthy_idle` when `eligible = 0` AND no propagating omissions AND no active pipeline wait.

---

## Maturity target

Minimum tenant class for Phase **09** entry: **`OPERATIONAL_ALIVE`** (see operational health doctrine).

---

## Operator truth requirement

Any metric shown in admin overview MUST be derivable from:

1. durable DB aggregates, OR  
2. labeled `ephemeral_process_gauge` with TTL disclaimer.

**Forbidden:** in-process counters presented as tenant historical truth without label.
