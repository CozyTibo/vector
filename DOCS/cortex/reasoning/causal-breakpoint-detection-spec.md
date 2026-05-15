# Causal breakpoint detection spec (Phase 06)

**Status:** normative spec.

## Breakpoint definition

A **causal breakpoint** is an event or negative signal where **downstream causal influence** is legally truncated — e.g. resolution of blocker, completion of commitment, de‑escalation template matched.

## Detection algorithm (intent)

Single forward pass over time‑sorted execution events maintaining **active causal frontier** multiset; breakpoints append to `breakpoint_index` with deterministic ordering.

## Outputs

- `breakpoint_id` (hash).  
- `before_chain_id` / `after_chain_id` (optional split).  
- Receipt linkage.

## Non‑goals

Detecting “team slowed down” or “velocity dropped” without countable evidence.
