# Phase 03 — Normative Index (Single Owner Per Concept)

**Status:** normative for Phase 03 specification and runtime contracts.  
**Purpose:** prevent split-brain semantics by assigning **exactly one authoritative doctrine** per concept. Supporting docs are illustrative or historical unless listed here as secondary normative extensions.

## How to use this index

- If two documents disagree, **the doctrine named below wins**.
- Legacy files under `03-canonical/` without an entry here are **non-normative** unless explicitly elevated by a future tracker note.
- Phase 04+ docs must not redefine Phase 03 terms without an explicit cross-phase amendment.
- **Implementation sequencing** is authoritative in `implementation-plan.md` (**Stages 1–18**) — not this index.

## Authority tiers

| Tier | Meaning |
| ---- | ------- |
| **P03-D** | Phase 03 doctrine (authoritative for Phase 03) |
| **P02-D** | Phase 02 doctrine (authoritative inputs/constraints upstream of canonicalization) |
| **P01-D** | Phase 01 doctrine (authoritative raw ingest semantics upstream of Phase 02/03) |
| **XREF** | Cross-phase boundary definition (Phase 03 consumes; Phase 04+ owns resolution semantics) |

## Concept → authoritative source

| Concept | Owner doc |
| ------- | --------- |
| Phase 03 mission, anti-goals, creep prevention | `phase-03-anti-goals-doctrine.md` |
| Canonical object taxonomy & structural primitives | `phase-03-canonical-model-doctrine.md` |
| Deterministic vs forbidden probabilistic behavior | `phase-03-deterministic-canonicalization-doctrine.md` |
| Canonical identity vs provider identity vs Phase 04 linkage | `phase-03-identity-continuity-doctrine.md` |
| Ambiguity persistence & operational ambiguity runtime | `phase-03-ambiguity-confidence-doctrine.md` |
| Replay / rebuild / regeneration / pins / divergence | `phase-03-replay-versioning-doctrine.md` |
| Provenance graph & runtime traceability | `phase-03-provenance-traceability-doctrine.md` |
| Temporal ordering & runtime continuity | `phase-03-temporal-timeline-doctrine.md` |
| Failure / degraded states taxonomy | `phase-03-failure-degradation-doctrine.md` |
| Remediation & recovery actions | `phase-03-remediation-recovery-doctrine.md` |
| Canonical query classes & anti-goals | `phase-03-canonical-query-doctrine.md` |
| **Canonical control plane / operator surfaces (authoritative)** | `phase-03-canonical-control-plane-doctrine.md` |
| Operator/admin filename stub (historical links) | `phase-03-operator-control-plane-doctrine.md` → redirects to canonical control plane |
| Verification engine (invariants, CI, divergence tooling) | `phase-03-verification-engine-doctrine.md` |
| Binary closure gates | `phase-03-closure-gates-doctrine.md` |
| **Mapping system umbrella** | `phase-03-mapping-system-doctrine.md` |
| **Mapping bundle registry & governance** | `phase-03-mapping-bundle-registry.md` |
| **Bundle pinning & deterministic bundle resolution** | `phase-03-bundle-pinning-doctrine.md` |
| **Oracle vectors & deterministic regression** | `phase-03-oracle-vectors-doctrine.md` |
| **CI deterministic drift enforcement** | `phase-03-ci-deterministic-enforcement-doctrine.md` |
| **Logical key derivation & idempotency tuples** | `phase-03-logical-key-doctrine.md` |
| **Transform + field lineage + remap** | `phase-03-transform-lineage-doctrine.md` |
| Granular implementation sequencing (Stages 1–18) | `implementation-plan.md` |
| Readiness / operational risk assessment | `phase-03-implementation-readiness-audit.md` |
| **Phase 3.5 — reference plane, continuity edges, execution primitives, bundle continuity** | `phase-35-organizational-continuity-foundation.md` (**XREF** → Phase 04+) |

## Upstream dependencies (must remain stable)

| Upstream concept | Owner doc | Relationship to Phase 03 |
| ---------------- | --------- | ------------------------ |
| Raw row identity, replay lanes, revision append semantics | `DOCS/cortex/01-ingestion/phase-01-live-idempotency-doctrine.md`, `phase-01-runtime-correctness-hardening-doctrine.md` | Canonical inputs are **raw memory** artifacts |
| Raw memory contracts, lineage, temporal ordering, replay divergence classes | `DOCS/cortex/02-raw-store/*` + Phase 02 tracker | Canonicalization consumes Phase 02 outputs/trust signals |

## Supporting (non-authoritative unless elevated)

- `canonicalization-model.md` — historical overview; defer to `phase-03-canonical-model-doctrine.md`.
- `canonicalization-boundary-rules.md` — defer to deterministic + anti-goals doctrines.
- `canonicalization-replay-model.md` — superseded by `phase-03-replay-versioning-doctrine.md`.
- `ontology-mapping-strategy.md` — design input until referenced by registry gates.

## Document control

- **Owner:** Cortex architecture / canonicalization working group.
- **Change rule:** updates that rename authoritative owners **must** update this index in the same change.
