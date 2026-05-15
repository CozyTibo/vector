# Reasoning runtime legality matrix (Phase 06)

**Status:** normative matrix (mirror role of `05-traversal/phase-05-runtime-legality-matrix.md`).

## Predicates (production gates)

| Predicate | Required evidence |
|-----------|-------------------|
| **R‑LEG‑01** | Phase **05** production runtime predicate satisfied for any walk‑ingesting reducer path. |
| **R‑LEG‑02** | Phase **06** **G‑P06‑ANTI‑01** green in CI. |
| **R‑LEG‑03** | Chronology legality not `unresolved` for **strict** causal mode jobs (or job explicitly labeled degraded mode). |
| **R‑LEG‑04** | Redis / queue isolation for reasoning jobs documented — no cross‑tenant lease bleed. |
| **R‑LEG‑05** | Operator dangerous actions behind phrase + audit log. |

## Forbidden deployments

- Reasoning workers without Phase **05** ingress validation when consuming walks.  
- Multi‑tenant shared mutable cache for causal graphs without tenant key partition.

## Waivers

Only via future `waivers/reasoning_verification_waivers.yaml` — mirror Phase **05** waiver discipline.

## Status today

**All predicates:** **Blocked — spec only** until implementation program opens.
