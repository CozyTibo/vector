# Reasoning runtime legality matrix (Phase 06)

**Status:** normative matrix (mirror role of `05-traversal/phase-05-runtime-legality-matrix.md`).

## Predicates (production gates)

| Predicate | Required evidence |
|-----------|-------------------|
| **R‑LEG‑01** | Phase **05** [`phase-05-runtime-legality-matrix.md`](../05-traversal/phase-05-runtime-legality-matrix.md) production predicates satisfied for any walk‑ingesting reducer path (cite exact predicate ids in deployment checklist). |
| **R‑LEG‑02** | Phase **06** **G‑P06‑ANTI‑01** green in CI. |
| **R‑LEG‑03** | **`chronology_legality_class` ∉ { `chronology_unresolved` }** for jobs labeled **strict causal mode** **or** job explicitly runs under **`max_causal_hops_degraded`** policy lane with operator banner per [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) — **never** confuse with `replay_safe_ordering` string alone. |
| **R‑LEG‑04** | Redis / queue isolation for reasoning jobs documented — no cross‑tenant lease bleed. |
| **R‑LEG‑05** | Operator dangerous actions behind phrase + audit log. |

## Forbidden deployments

- Reasoning workers without Phase **05** ingress validation when consuming walks.  
- Multi‑tenant shared mutable cache for causal graphs without tenant key partition.

## Waivers

Only via future `waivers/reasoning_verification_waivers.yaml` — mirror Phase **05** waiver discipline.

## Status today

**All predicates:** **Blocked — spec only** until implementation program opens.
