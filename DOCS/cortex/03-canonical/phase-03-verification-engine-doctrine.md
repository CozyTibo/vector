# Phase 03 — Canonical Verification Engine Doctrine

**Status:** normative. **Separation:** This engine is not the admin UI and not the mapping engine—it evaluates invariants & emits PASS/FAIL/evidence packs.

## Purpose

Provide **automated, deterministic verification** for canonical runtime slices:

- Gate enforcement (`phase-03-closure-gates-doctrine.md`),
- Continuous invariant sweeps (tenant/connector scope),
- Evidence bundles attachable to incidents (hashes, exemplar ids).

## Responsibilities

| Responsibility | Description |
| -------------- | ----------- |
| **Invariant evaluation** | Executes checks for determinism, provenance completeness, ordering, ambiguity persistence |
| **Fixture harness** | Runs frozen corpus vectors per bundle pin |
| **Divergence classification** | Computes **C0–C5** canonical rebuild divergence classes with structured receipts (`phase-03-replay-versioning-doctrine.md`) |
| **Regression sentinel** | Detects unintended logical-key drift across CI merges |

## Non-responsibilities

- Operator UX layout (control plane doc owns surfaces).
- Remediation execution (remediation doctrine)—verification **may** trigger alerts only.

## Outputs (conceptual)

- `verification_report` with gate statuses, failing exemplars, bundle pins implicated,
- `divergence_report` for rebuild jobs,
- **No semantic interpretation** of organizational facts—only structural checks.

## References

- Operator-visible gate matrix + proof artifacts: `phase-03-canonical-control-plane-doctrine.md` §G
- Closure gates: `phase-03-closure-gates-doctrine.md`
- Remediation: `phase-03-remediation-recovery-doctrine.md`
