# Cortex Capability Validation Layer

This directory defines the long-horizon organizational cognition capabilities that Cortex architecture must eventually support.

These documents are **architectural validation anchors**: each capability is specified in operational terms, mapped to required architecture primitives, and assessed against current maturity.

## Why This Exists

Cortex design depth (ingestion, replay, provenance, canonicalization, identity continuity, temporal memory, and governance) must be validated against real end-state cognition workflows.

This layer answers two recurring architecture questions:

1. **Can current Cortex architecture realistically enable capability X?**
2. **If not, which missing primitives block it (phase, ontology, temporal, linkage, replay, provenance, queryability)?**

## How To Use

- Use `capability-framework.md` for capability definitions and evaluation criteria.
- Use `capability-readiness-matrix.md` for portfolio-level maturity status.
- Use `architecture-capability-mapping.md` to trace each capability to required phases and primitives.
- Use scenario docs to validate whether concrete workflows are architecturally feasible.
- Use `unresolved-capability-gaps.md` to prioritize missing infrastructure before claiming capability readiness.

## File Index

- Core framework:
  - `capability-framework.md`
  - `architecture-capability-mapping.md`
  - `capability-readiness-matrix.md`
  - `unresolved-capability-gaps.md`
- Scenario set:
  - `copilots.md`
  - `organizational-search.md`
  - `execution-intelligence.md`
  - `onboarding-intelligence.md`
  - `incident-analysis.md`
  - `strategic-analysis.md`
  - `delivery-reconstruction.md`
  - `organizational-memory.md`
  - `dependency-intelligence.md`
  - `decision-lineage.md`
  - `initiative-continuity.md`
  - `operational-debugging.md`
  - `ambiguity-investigation.md`
  - `replay-driven-analysis.md`
  - `historical-org-reconstruction.md`
