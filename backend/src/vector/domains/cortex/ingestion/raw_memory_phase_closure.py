"""Phase 02 Step 10 — binary closure gate evaluation."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    compute_phase02_gate_g13_replay_proof_depth,
    compute_phase02_gates_g1_g7,
    compute_phase02_gates_g8_g10,
    finalize_phase02_closure_from_canonical_gates,
    merge_phase02_canonical_gates,
)


def evaluate_phase02_step10_closure_gate(
    *,
    tenant_id: uuid.UUID,
    raw_memory_contracts: dict[str, Any],
    raw_memory_persistence: dict[str, Any],
    raw_memory_temporal: dict[str, Any],
    raw_memory_replay: dict[str, Any],
    raw_memory_query: dict[str, Any],
    raw_memory_failure_recovery: dict[str, Any],
    raw_memory_trust: dict[str, Any],
    raw_memory_control_plane: dict[str, Any],
    control_plane_payload: dict[str, Any],
    precomputed_gates_g1_g7: dict[str, dict[str, Any]] | None = None,
    raw_memory_replay_hardening: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate G1–G10 plus stabilization gates (G13 when replay hardening is supplied)."""
    gates_g1_g7 = precomputed_gates_g1_g7 or compute_phase02_gates_g1_g7(
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
    )
    gates_g8_g10 = compute_phase02_gates_g8_g10(
        raw_memory_trust=raw_memory_trust,
        raw_memory_control_plane=raw_memory_control_plane,
        control_plane_payload=control_plane_payload,
    )
    stabilization: dict[str, dict[str, Any]] | None = None
    if raw_memory_replay_hardening is not None:
        stabilization = {
            "G13": compute_phase02_gate_g13_replay_proof_depth(raw_memory_replay_hardening),
        }
    gates = merge_phase02_canonical_gates(
        gates_g1_g7, gates_g8_g10, stabilization_gates=stabilization
    )
    return finalize_phase02_closure_from_canonical_gates(
        tenant_id=tenant_id,
        gates=gates,
        raw_memory_trust=raw_memory_trust,
    )
