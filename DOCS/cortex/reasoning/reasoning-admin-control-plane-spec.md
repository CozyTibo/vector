# Reasoning admin control plane (Phase 06)

**Status:** normative operator / admin spec (no UI code in this repo step).

## Surfaces (mandatory at closure)

| Surface | Operator purpose |
|---------|------------------|
| **Reasoning health strip** | Chronology legality, causal legality, replay posture rollup. |
| **Temporal legality inspector** | Anchors, chains, skew flags, export order. |
| **Causal chain debugger** | DAG / list view with hop‑level lineage to raw. |
| **Replay reasoning debugger** | Inputs: walk hashes, index epoch, permutation profile → outputs diff. |
| **Chronology debugger** | Windows, half‑open intervals, silence derivation sources. |
| **Ambiguity propagation inspector** | Active ambiguity classes + blocked derivations. |
| **Receipts explorer** | Reasoning receipts + proof artifacts (hashes). |
| **Causal contradiction topology** | Partition graph from conflict doctrine. |
| **Continuity breakpoints** | Cross‑system bridge failures. |
| **Degradation topology** | Severity rollup by tenant / time window. |
| **Replay pressure** | Queue depth, job latency, equivalence failures count. |

## Actions (policy‑gated)

Examples: **rebuild chronology** for tenant+bundle, **re‑emit causal chains** (dry‑run default), **quarantine slice** — each requires confirmation phrase + scope banner per `10-admin/dangerous-action-safety-model.md`.

## RBAC

Align with admin permissions model; reasoning surfaces are **substrate** not end‑user intelligence.
