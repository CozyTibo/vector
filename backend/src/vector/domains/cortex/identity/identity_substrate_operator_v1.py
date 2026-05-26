"""Wave 2 — collapsed operator identity paths (reset cursor + mark dirty only)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.continuity_rebuild import substrate_counts
from vector.domains.cortex.identity.identity_substrate_repair_v1 import (
    reset_identity_substrate_repair_state_v1,
)

WAVE2_COLLAPSED_REPLAY_JOB_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "identity_rebuild_from_anchors",
        "identity_continuity_rebuild",
    }
)

WAVE2_DEBUG_ONLY_REPLAY_JOB_KINDS_V1: Final[frozenset[str]] = frozenset(
    {"identity_continuity_rebuild"},
)


class Wave2CollapsedReplayJobKindError(ValueError):
    """Raised when a routine API attempts a superseded replay job kind."""


def assert_primary_replay_job_kind_allowed_v1(job_kind: str) -> None:
    """Block superseded replay kinds on non-debug admin routes."""
    if job_kind in WAVE2_COLLAPSED_REPLAY_JOB_KINDS_V1:
        msg = (
            f"replay_job_kind_collapsed:{job_kind} "
            "Use POST .../cortex/operator/actions rebuild_identities (reset + mark dirty) "
            "or debug routes under .../cortex/debug/identity/."
        )
        raise Wave2CollapsedReplayJobKindError(msg)


def operator_rebuild_identities_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator rebuild: reset lease repair cursor and enqueue convergence (no replay job)."""
    counts_before = substrate_counts(session, tenant_id=tenant_id)
    anchors_total = int(counts_before.get("identity_anchors") or 0)
    repair_state = reset_identity_substrate_repair_state_v1(
        session,
        tenant_id=tenant_id,
        anchors_total=anchors_total,
    )

    from vector.domains.cortex.execution.convergence_dispatch import mark_dirty_and_enqueue_convergence_v1

    convergence_dispatch = mark_dirty_and_enqueue_convergence_v1(
        tenant_id=tenant_id,
        reason="operator:rebuild_identities",
        telemetry_trigger="operator:rebuild_identities",
    )

    return {
        "surface_kind": "operator_rebuild_identities_v1",
        "tenant_id": str(tenant_id),
        "repair_state_reset": repair_state,
        "counts_before": counts_before,
        "convergence_dispatch": convergence_dispatch,
        "enqueued": False,
        "no_replay_job": True,
        "same_repair_as_phase_03": True,
        "hint": (
            "Repair cursor reset to offset 0; convergence worker will run identity repair slices "
            "(same as phase 03). Watch Substrate truth or Runtime for progress."
        ),
    }
