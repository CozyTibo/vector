# Governance Escalation Model

## Purpose
Define when architectural changes require elevated review to prevent drift and silent contract breakage.

## Escalation Levels
- Level 0: editorial clarifications only (no semantic changes).
- Level 1: schema or phase-local semantic changes.
- Level 2: cross-phase contract or temporal/provenance semantics changes.
- Level 3: invariant/AI-boundary/replay model changes.

## Required Reviews By Change Type

### Schema semantics change
- Trigger examples:
  - renaming or redefining contract fields,
  - changing mutability rules.
- Required reviews:
  - schema review,
  - replay review (if replay-sensitive fields touched),
  - architecture review for cross-phase impacts.

### Provenance semantics change
- Trigger examples:
  - altering `provenance.*` requirements,
  - changing evidence linkage obligations.
- Required reviews:
  - provenance review,
  - replay review,
  - architecture review.

### Temporal semantics change
- Trigger examples:
  - ordering precedence updates,
  - validity window semantics changes.
- Required reviews:
  - temporal review,
  - replay review,
  - reasoning/synthesis downstream review.

### Ontology definition change
- Trigger examples:
  - redefining `decision`, `concern`, `ownership`, `dependency`.
- Required reviews:
  - ontology review,
  - canonical/graph/reasoning review,
  - architecture review.

### Replay model change
- Trigger examples:
  - replay isolation policy changes,
  - version pinning changes,
  - supersession publication changes.
- Required reviews:
  - replay review (mandatory),
  - schema review,
  - architecture review.

### AI boundary change
- Trigger examples:
  - allowing AI in deterministic phases,
  - relaxing confidence/provenance constraints.
- Required reviews:
  - AI-boundary review,
  - replay review,
  - architecture review,
  - ADR required.

## Escalation Workflow
1. Classify change level.
2. List affected invariants, phases, and contracts.
3. Run `drift-detection-checklist.md`.
4. Collect required review approvals.
5. Record decision and mitigation in ADR when Level 2+.
