# Phase 02 Trust-State Taxonomy

## Purpose
Define explicit runtime trust states for raw organizational memory.

These states are operator-facing and must be machine-derivable.
They replace vague "healthy/unhealthy" language.

## States

| State | Exact Meaning | Runtime Criteria | Operator Implication | Allowed System Behavior |
| ----- | ------------- | ---------------- | -------------------- | ----------------------- |
| healthy | Raw evidence continuity and verification coverage are intact for declared scope. | Replay invariants pass, provenance continuity pass, corruption checks pass, reconstruction checks pass. | Scope can be trusted for replay and reconstruction under declared guarantees. | Full replay/retrieval/verification allowed. |
| replay-safe | Replay boundaries are deterministic and isolated for scope. | Replay isolation checks pass; lineage and ordering checks pass. | Replay is trusted for preserved evidence. | Replay allowed with normal policy controls. |
| reconstruction-safe | "As-of" evidence reconstruction is trustworthy for declared window. | Temporal ordering + revision continuity checks pass for requested window. | As-of retrieval can be used as evidence baseline. | Temporal inspection and replay allowed. |
| partial | Scope has usable evidence, but not full continuity across expected window/streams. | Coverage checks show known missing windows/streams without corruption proof. | Use with explicit caveat labels; do not assume completeness. | Retrieval allowed; replay may be scoped/limited. |
| degraded | Integrity/continuity checks detect bounded issues. | One or more trust checks fail but scope remains inspectable. | Investigation required before high-trust usage. | Read-only inspection + constrained replay only. |
| unverifiable | Trust cannot be established due to missing verification evidence. | Required checks cannot execute or required metadata is absent. | No trust claim allowed. | Read-only diagnostic access; block trust-claiming actions. |
| replay-diverged | Replay output diverges from declared equivalence expectations. | Replay equivalence checks fail outside acceptable divergence classes. | Replay output requires investigation and approval before use. | Replay publish blocked for affected scope. |
| continuity-broken | Lineage/revision continuity is broken for scope. | Provenance chain break, missing revision links, or ordering anchors broken. | Historical continuity claims invalid for affected scope. | Quarantine affected scope from trusted replay/reconstruction. |
| corrupted | Evidence or integrity metadata is corrupted. | Hash/checksum mismatch, corrupted payload/index/pointer evidence. | Immediate trust downgrade and incident response. | Block replay publication; allow recovery workflows only. |
| lineage-incomplete | Evidence exists but lineage is incomplete for proof obligations. | Required provenance fields or lineage links missing for scope. | Evidence may be inspectable but not audit-complete. | Restricted retrieval with explicit lineage caveats. |

## State Transition Rules
- Transitions to degraded/unverifiable/corrupted must be explicit and timestamped.
- No automatic transition to healthy without passing closure checks.
- Unknown state is treated as unverifiable.

## Progressive Enforcement Semantics (Step 11)
Trust state drives calibrated runtime behavior:
- `healthy` / `replay-safe` / `reconstruction-safe`: allowed.
- `partial` / `degraded`: allowed with explicit warnings.
- `unverifiable`: allowed with elevated risk flags and operator acknowledgment.
- `unsafe` (derived policy state): admin-only or strongly warned path.
- catastrophic states (`corrupted`, hard lineage/reconstruction break): blocked.

This is enforcement-readiness posture, not global fail-closed mode.

## Closure Dependency
Phase 02 closure requires trust-state transitions to be implemented and testable in admin/runtime flows.

Transition calibration and severity semantics are defined in `trust-state-transition-semantics.md`.
