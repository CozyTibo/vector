# Phase 02 - Raw Memory Implementation Plan

## Strategic Boundary
Phase 02 is memory substrate completion, not intelligence construction.

Implementation in this phase must remain strictly inside:
- durable raw persistence,
- provenance continuity,
- temporal continuity,
- replay-safe reinterpretation foundation,
- raw queryability,
- corruption/recovery reliability.

## Required Readiness Before Coding
- Runtime contracts frozen for immutable append + provenance + temporal semantics.
- Query model frozen for expected operator/downstream access classes.
- Replay boundary rules frozen (tenant scope, connector scope, replay lineage, isolation).
- Operational closure criteria agreed up front (not retrofitted at the end).
- Trust-state taxonomy frozen (`trust-state-taxonomy.md`).
- Binary closure gates frozen (`binary-closure-gates.md`).
- Transition semantics frozen (`trust-state-transition-semantics.md`).
- Gate tolerance semantics frozen (`gate-tolerance-semantics.md`).
- API trust annotation doctrine frozen (`trust-state-api-contract-doctrine.md`).
- Continuity-gap representation doctrine frozen (`continuity-gap-representation-doctrine.md`).
- Normative ownership map frozen (`normative-index.md`).

## Phase 02 Implementation Step Set (Complete Coverage)

### Step 1 - Runtime contracts + invariants
Implement immutable/replay/reconstruction/provenance invariants from doctrine.

### Step 2 - Persistence + provenance runtime model
Implement durable raw persistence and lineage continuity model.

### Step 3 - Temporal continuity
Implement revision/supersession/deletion visibility and ordering doctrine.

### Step 4 - Replay equivalence + divergence
Implement deterministic replay and divergence-class handling.

### Step 5 - Query model + anti-goal enforcement
Implement supported evidence retrieval classes and enforce semantic/graph anti-goals.

### Step 6 - Storage + retention
Implement append-only storage boundaries, archival/rehydration, and policy retention/deletion behavior.

### Step 7 - Failure/recovery
Implement failure class representation, corruption handling, and recovery validation flows.

### Step 8 - Trust-state + API contracts
Implement trust-state transitions, gate tolerances, trust annotations, and continuity-gap representation.

### Step 9 - Runtime Memory Control Plane
Implement operator memory control plane (inspection + verification + safe actions).

### Step 10 - Final Phase closure trust gate
Close Phase 02 only when binary closure gates pass per `binary-closure-gates.md`.

## Operational Closure Criteria (Must Be Explicitly Met)
Phase 02 is complete only when we can credibly state:
"Cortex has trustworthy organizational raw memory."

That requires:
- durable preserved exhaust,
- reconstructable provenance,
- deterministic replay behavior,
- temporal continuity across revisions/deletions,
- operationally viable retrieval,
- tested corruption detection and recovery,
- admin verifiability (visibility + actions + checklist).

These closure criteria are enforced in Step 10 (final closure gate) after Runtime Memory Control Plane implementation.
Trust-state and degradation semantics for closure decisions are defined in `trust-state-taxonomy.md`.

## Runtime Closure States (Operational Truth)
Phase 02 status must distinguish:
- **structurally implemented**: contracts/models shipped,
- **operationally proven**: runtime validation and drift/corruption checks passing,
- **replay-safe**: deterministic replay boundaries + lineage proof,
- **reconstructable**: as-of preserved-evidence reconstruction works for declared scopes,
- **degraded/partial**: continuity gaps exist but are explicit and bounded,
- **unverifiable**: trust evidence missing or corrupted; no healthy claim allowed.

## Replay-Safe Clarification
Replay-safe in Phase 02 means deterministic, isolated reinterpretation over preserved evidence.
Replay-safe does not imply replay-complete omniscience over provider reality.
Normative replay equivalence/divergence classes: `replay-equivalence-doctrine.md`.

## Historical Reconstruction Clarification
Phase 02 reconstruction semantics are "what was preserved and provable," not "objective total historical truth."
Normative reconstruction guarantees and gap classes: `reconstruction-semantics-doctrine.md`.

## Phase-Specific Blockers (Current)
- Runtime closure criteria not yet codified as executable gates.
- Admin expectations for Phase 02 visibility/actions not yet fully specified.
- Temporal doctrine for revisions/supersession/deletion semantics needs stronger contract wording.
- Query-model guarantees (partition/index/hot-cold/replay retrieval) need hard commitments.

## Remaining Unclear Areas Before Implementation
- exact numeric threshold values for production calibration (semantics are now defined),
- final API field naming/enum freeze for trust annotations,
- exact Step D IA contract across Cortex Overview / Memory / Verification tabs.
