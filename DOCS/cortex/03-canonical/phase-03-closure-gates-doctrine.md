# Phase 03 — Verification & Closure Gates (Binary PASS/FAIL)

**Status:** normative pre-implementation gates. **Gate semantics** are testable once registry/oracle/CI contracts are operational—**see existential infrastructure below** for what “Phase 03 operational closure” requires beyond narrative docs.

## Existential deterministic infrastructure (operational closure prerequisites)

Phase **03** cannot claim **operational closure** (certification-ready; trusted broad materialization) unless **all** are true as **running operational contracts**, not doctrine text alone:

| Prerequisite | Authoritative doctrine |
| ------------ | ---------------------- |
| Registry governance operationalized (lifecycle, hashes, promotions, rollback/freeze) | `phase-03-mapping-bundle-registry.md` |
| Bundle pins enforced (no floating mappings / no implicit latest) | `phase-03-bundle-pinning-doctrine.md` |
| Oracle vectors institutionalized (manifests + promotion-bound oracle PASS) | `phase-03-oracle-vectors-doctrine.md` |
| CI drift enforcement active (fail-closed promotion; reproducible reports) | `phase-03-ci-deterministic-enforcement-doctrine.md` |

These prerequisites **materialize** gates **G-P03-09, G-P03-10, G-P03-11, G-P03-12** as enforceable—not aspirational.

## Gate posture

- **PASS** means automated verification **and** **operator-visible deterministic proof** obligations are satisfied for the declared slice (substrate metrics + receipts—not semantic dashboards). Operator visibility gates (**G-P03-15–G-P03-21**) apply to Phase 03 closure.
- **FAIL** blocks promotion; waivers require explicit risk acceptance recorded outside this doc.

## Gate catalog (substrate + mapping hardening + operator visibility)

| ID | Name | PASS criteria (high level) |
| -- | ---- | -------------------------- |
| **G-P03-01** | Determinism | Same raw snapshot + **pinned** mapping bundle + engine build ⇒ identical logical keys + ordering |
| **G-P03-02** | Provenance integrity | Every canonical row has ≥1 raw evidence pointer + field lineage when field populated |
| **G-P03-03** | Rebuild equivalence | Canonical rebuild matches stored rows within **C0–C2** only; C3+ hard FAIL |
| **G-P03-04** | Ambiguity persistence | No silent drops; competing mapping rules either resolve by priority table or emit ambiguity |
| **G-P03-05** | Traceability | Raw→canonical forward index + canonical→raw reverse walk complete for slice |
| **G-P03-06** | Temporal continuity | Late-arriving + supersession fixtures reproduce deterministic ordering |
| **G-P03-07** | Anti-goal hygiene | Static/policy checks forbid semantic/managerial/LLM fields & intents per anti-goals |
| **G-P03-08** | Corruption detection | Duplicate logical keys / missing lineage / orphan canonical rows = FAIL |
| **G-P03-09** | Registry integrity | Every **approved** bundle has ownership, compatibility line, artifact hashes, changelog |
| **G-P03-10** | Key stability | Logical key derivations match oracle vectors per class; no clock/random dependence |
| **G-P03-11** | Remap safety | Regeneration under declared compatible bump matches expected C2 receipts; undeclared drift fails |
| **G-P03-12** | Verification engine | Invariant suite emits signed report artifact; can be re-run in CI and admin |
| **G-P03-13** | Remediation safety | Policy-gated actions never fabricate facts; always leave audit trail |
| **G-P03-14** | Ops certification | Stabilization pass + operator runbook executed; evidence pack archived (**Step 18**) |

### Operator visibility & proof-surface gates (no opaque trust)

| ID | Name | PASS criteria (high level) |
| -- | ---- | -------------------------- |
| **G-P03-15** | No hidden rebuild drift | Every rebuild/regeneration affecting scoped canonical rows emits **operator-visible** divergence summary (C-class ledger); no silent reconcile |
| **G-P03-16** | No opaque canonical generation | Object inspector can display **logical key + bundle id + rule ids + raw evidence refs** for sampled objects in certified slice |
| **G-P03-17** | Transform lineage verifiable | Field-level lineage present where fields populated; missing lineage fails gate (aligned with G-P03-02 but operator-audited) |
| **G-P03-18** | Ambiguity visibility | Unresolved ambiguity backlog visible with rates/thresholds; **explosion warnings** fire when policy exceeded |
| **G-P03-19** | Mapping invalidation visible | Bundle bumps / invalidation scopes surface affected connectors/scopes + remap risk labels—no invisible staleness |
| **G-P03-20** | Replay generation auditable | Regeneration generations / job receipts visible; cannot certify with **unverifiable** replay metadata |
| **G-P03-21** | Certification w/ proof artifacts | Step **18** certification requires archived **operator-visible** verification matrix **including G-P03-15–G-P03-20** + rebuild/ambiguity snapshots per `phase-03-canonical-control-plane-doctrine.md` |

## Relationship to Phase 02 gates

Canonical gates assume Phase 02 raw memory gates relevant to substrate trust are satisfied or explicitly scoped down (documented).

## References

- Bundle pinning: `phase-03-bundle-pinning-doctrine.md`
- Oracle vectors: `phase-03-oracle-vectors-doctrine.md`
- CI enforcement: `phase-03-ci-deterministic-enforcement-doctrine.md`
- Mapping bundle registry: `phase-03-mapping-bundle-registry.md`
- Implementation readiness audit: `phase-03-implementation-readiness-audit.md`
- Implementation sequencing: `implementation-plan.md`
- Canonical control plane obligations: `phase-03-canonical-control-plane-doctrine.md`
