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

### Step 10 - Baseline Phase closure trust gate runtime
Establish executable binary closure gate runtime per `binary-closure-gates.md` (baseline gate set).

### Step 11 - Progressive trust enforcement
Implement trust-aware enforcement policy modes with catastrophic-only hard block at first pass.

### Step 12 - Unified verification semantics
Unify closure, trust, control-plane, and aggregate verification into one canonical gate computation path.

### Step 13 - Replay divergence hardening
Harden D0-D5 replay proof matrix and denial-path behavior for forbidden divergence classes.

### Step 14 - Trust-signal hardening
Add proof-quality/freshness semantics so operator trust surfaces distinguish measured vs inferred vs stale.

### Step 15 - Critical integrity hardening
Strengthen reconstruction-critical continuity validation and selective integrity constraints where safe.

### Step 16 - Operational trust proof pass
Run adversarial runtime proof suite (replay/corruption/temporal/stale/denial/recovery) before declaring Phase 02 complete.

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

These closure criteria are enforced progressively:
- Step 10 establishes binary closure gate runtime.
- Steps 11-15 calibrate enforcement truthfulness, replay proof depth, and integrity strength.
- Step 16 is final operational proof pass before closure claim.
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

## Enforcement Readiness Model (Calibrated, Non-Brittle)
Progressive trust enforcement is required before full fail-closed operation:
- `healthy`: allow operations,
- `degraded`: allow + warning,
- `unverifiable`: allow + explicit risk flag,
- `unsafe`: admin-only or strongly warned operation,
- `catastrophic`: hard-block operation.

Initial hard blocking is restricted to catastrophic trust failures (lineage impossibility, nondeterministic reconstruction, replay lineage break, invalid revision continuity). Global fail-closed posture is deferred.

## Replay Proof Obligations (Runtime, not narrative)
- complete D0-D5 replay scenario coverage,
- deterministic classifier reproducibility for fixed snapshots,
- explicit forbidden divergence denial-path validation,
- replay-trust transition assertions under divergence and recovery.

## Operational Proof Requirements (Step 16)
- adversarial replay and corruption simulations,
- reconstruction edge-window validation,
- temporal ordering stress cases,
- stale-verification and freshness-label correctness,
- denial-path and remediation/recovery flow validation.

## Implementation Confidence (Updated)
- Architecture confidence: high.
- Operational trust confidence (current): moderate.
- Post-Step-16 target: operationally trustworthy with calibrated enforcement readiness.
