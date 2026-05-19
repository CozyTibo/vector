"""Phase 08.5 P085-34 — replay storm detection + response (**G-P085-ECON-02**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-runtime-economics-doctrine.md`` §Replay storms.
"""

from __future__ import annotations

import inspect
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.infrastructure.db.models.cortex_replay_divergence_event import (
    CortexReplayDivergenceEvent,
)
from vector.infrastructure.db.models.cortex_replay_storm_control import (
    CortexReplayStormControl,
)
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

PHASE085_REPLAY_STORM_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_REPLAY_STORM_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-runtime-economics-doctrine.md"
)

GP085_ECON02_GATE_ID_V1: Final[str] = "G-P085-ECON-02"

P085_ECON02_RULE_ID_V1: Final[str] = "P085-ECON-02"

REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1: Final[str] = "retrieval"
REPLAY_DIVERGENCE_SOURCE_SYNTHESIS_V1: Final[str] = "synthesis"

OPERATIONAL_OMISSION_REPLAY_STORM_V1: Final[str] = "replay_storm_active"


class ReplayStormHandlingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_replay_storm_divergence_spike_per_hour_v1() -> int:
    try:
        return max(1, int(get_settings().cortex_replay_storm_divergence_spike_per_hour))
    except Exception:  # noqa: BLE001
        return 3


def get_replay_storm_window_hours_v1() -> int:
    try:
        return max(1, int(get_settings().cortex_replay_storm_window_hours))
    except Exception:  # noqa: BLE001
        return 1


def _resolve_policy_digests_for_pin_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, str]:
    from vector.domains.cortex.retrieval.retrieval_legality_projection import (
        retrieval_policy_digest_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_job_envelope import (
        synthesis_policy_pack_digest_v1,
    )

    retrieval_digest = retrieval_policy_digest_v1()
    synthesis_digest = synthesis_policy_pack_digest_v1()
    tcre_digest = ""
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
        CortexTcreReconstructionJob,
    )

    latest_tcre = session.scalar(
        select(CortexTcreReconstructionJob.tcre_policy_bundle_digest)
        .where(CortexTcreReconstructionJob.tenant_id == tenant_id)
        .order_by(CortexTcreReconstructionJob.created_at.desc())
        .limit(1)
    )
    if latest_tcre:
        tcre_digest = str(latest_tcre)
    return {
        "pinned_retrieval_policy_digest": retrieval_digest,
        "pinned_synthesis_policy_pack_digest": synthesis_digest,
        "pinned_tcre_policy_bundle_digest": tcre_digest or synthesis_digest,
    }


def get_or_create_replay_storm_control_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexReplayStormControl:
    row = session.scalar(
        select(CortexReplayStormControl).where(CortexReplayStormControl.tenant_id == tenant_id)
    )
    if row is not None:
        return row
    row = CortexReplayStormControl(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        storm_active=False,
        exploration_partition_paused=False,
    )
    session.add(row)
    session.flush()
    return row


def persist_replay_divergence_event_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source: str,
    detail: dict[str, Any] | None = None,
) -> CortexReplayDivergenceEvent:
    """Durable divergence event for rolling storm rate."""
    row = CortexReplayDivergenceEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        source=source,
        detail_json=dict(detail or {}),
    )
    session.add(row)
    session.flush()
    return row


def count_recent_replay_divergences_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_hours: int | None = None,
) -> dict[str, Any]:
    """Count retrieval + synthesis divergences in rolling window."""
    hours = window_hours if window_hours is not None else get_replay_storm_window_hours_v1()
    since = datetime.now(tz=UTC) - timedelta(hours=hours)
    rows = session.execute(
        select(CortexReplayDivergenceEvent.source, func.count())
        .where(
            CortexReplayDivergenceEvent.tenant_id == tenant_id,
            CortexReplayDivergenceEvent.created_at >= since,
        )
        .group_by(CortexReplayDivergenceEvent.source)
    ).all()
    by_source = {str(src): int(cnt) for src, cnt in rows}
    retrieval = int(by_source.get(REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1, 0))
    synthesis = int(by_source.get(REPLAY_DIVERGENCE_SOURCE_SYNTHESIS_V1, 0))
    total = retrieval + synthesis
    return {
        "retrieval_count": retrieval,
        "synthesis_count": synthesis,
        "total_count": total,
        "window_hours": hours,
        "replay_divergence_rate_per_hour": float(total) / float(hours),
    }


def compute_combined_replay_divergence_rate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Combined retrieval + synthesis divergence rate (**G-P085-ECON-02**)."""
    counts = count_recent_replay_divergences_v1(session, tenant_id=tenant_id)
    threshold = get_replay_storm_divergence_spike_per_hour_v1()
    rate = float(counts["replay_divergence_rate_per_hour"])
    spike = rate >= float(threshold)
    return {
        "gate_id": GP085_ECON02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "threshold_per_hour": threshold,
        "spike_detected": spike,
        **counts,
    }


def activate_replay_storm_response_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    rate_snapshot: dict[str, Any],
) -> CortexReplayStormControl:
    """Storm response: pause exploration, pin policy digests."""
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    pins = _resolve_policy_digests_for_pin_v1(session, tenant_id=tenant_id)
    now = datetime.now(tz=UTC)
    control.storm_active = True
    control.exploration_partition_paused = True
    control.storm_detected_at = now
    control.updated_at = now
    control.pinned_retrieval_policy_digest = pins["pinned_retrieval_policy_digest"]
    control.pinned_synthesis_policy_pack_digest = pins["pinned_synthesis_policy_pack_digest"]
    control.pinned_tcre_policy_bundle_digest = pins["pinned_tcre_policy_bundle_digest"]
    control.detail_json = {
        **dict(control.detail_json or {}),
        "activation": {
            "rate_snapshot": rate_snapshot,
            "activated_at": now.isoformat(),
        },
    }
    session.flush()
    _LOGGER.warning(
        "replay_storm_activated tenant_id=%s rate=%s",
        tenant_id,
        rate_snapshot.get("replay_divergence_rate_per_hour"),
    )
    return control


def evaluate_and_activate_replay_storm_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Detect spike and activate storm controls when threshold exceeded."""
    rate = compute_combined_replay_divergence_rate_v1(session, tenant_id=tenant_id)
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    if rate.get("spike_detected") and not control.storm_active:
        control = activate_replay_storm_response_v1(
            session,
            tenant_id=tenant_id,
            rate_snapshot=rate,
        )
    return {
        "rate": rate,
        "control": replay_storm_control_to_public_v1(control),
    }


def replay_storm_control_to_public_v1(row: CortexReplayStormControl) -> dict[str, Any]:
    return {
        "tenant_id": str(row.tenant_id),
        "storm_active": bool(row.storm_active),
        "exploration_partition_paused": bool(row.exploration_partition_paused),
        "pinned_retrieval_policy_digest": row.pinned_retrieval_policy_digest,
        "pinned_synthesis_policy_pack_digest": row.pinned_synthesis_policy_pack_digest,
        "pinned_tcre_policy_bundle_digest": row.pinned_tcre_policy_bundle_digest,
        "operator_acknowledged_at": (
            row.operator_acknowledged_at.isoformat() if row.operator_acknowledged_at else None
        ),
        "operator_acknowledged_by": (
            str(row.operator_acknowledged_by) if row.operator_acknowledged_by else None
        ),
        "storm_detected_at": (
            row.storm_detected_at.isoformat() if row.storm_detected_at else None
        ),
        "saturation_resume_allowed": bool(
            row.operator_acknowledged_at is not None or not row.storm_active
        ),
        "detail_json": dict(row.detail_json or {}),
    }


def is_exploration_partition_paused_v1(session: Session, *, tenant_id: uuid.UUID) -> bool:
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    return bool(control.storm_active and control.exploration_partition_paused)


def is_saturation_blocked_by_replay_storm_v1(session: Session, *, tenant_id: uuid.UUID) -> bool:
    """TCRE saturation requires operator ack while storm is active."""
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    if not control.storm_active:
        return False
    return control.operator_acknowledged_at is None


def assert_exploration_partition_allowed_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> None:
    """Raise when exploration partition work is paused by replay storm."""
    if is_exploration_partition_paused_v1(session, tenant_id=tenant_id):
        control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
        raise ReplayStormHandlingError(
            "exploration_partition_paused",
            detail={
                "gate_id": GP085_ECON02_GATE_ID_V1,
                "storm_detected_at": (
                    control.storm_detected_at.isoformat() if control.storm_detected_at else None
                ),
                "pinned_retrieval_policy_digest": control.pinned_retrieval_policy_digest,
                "requires_operator_ack": True,
            },
        )


def operator_acknowledge_replay_storm_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    operator_user_id: uuid.UUID | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Operator ack — allows saturation resume; keeps pins until storm cleared."""
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    now = datetime.now(tz=UTC)
    control.operator_acknowledged_at = now
    control.operator_acknowledged_by = operator_user_id
    control.updated_at = now
    control.detail_json = {
        **dict(control.detail_json or {}),
        "operator_ack": {"at": now.isoformat(), "note": note},
    }
    session.flush()
    return replay_storm_control_to_public_v1(control)


def clear_replay_storm_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Clear storm after divergence rate normalizes (operator or automated)."""
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    now = datetime.now(tz=UTC)
    control.storm_active = False
    control.exploration_partition_paused = False
    control.updated_at = now
    session.flush()
    return replay_storm_control_to_public_v1(control)


def evaluate_replay_storm_for_tenant_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Full tenant replay storm evaluation card."""
    rate = compute_combined_replay_divergence_rate_v1(session, tenant_id=tenant_id)
    control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)
    if rate.get("spike_detected") and not control.storm_active:
        control = activate_replay_storm_response_v1(
            session,
            tenant_id=tenant_id,
            rate_snapshot=rate,
        )
    elif not rate.get("spike_detected") and control.storm_active:
        clear_replay_storm_v1(session, tenant_id=tenant_id)
        control = get_or_create_replay_storm_control_v1(session, tenant_id=tenant_id)

    return {
        "surface_kind": "replay_storm_card",
        "gate_id": GP085_ECON02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "divergence_rate": rate,
        "control": replay_storm_control_to_public_v1(control),
        "exploration_partition_paused": is_exploration_partition_paused_v1(
            session,
            tenant_id=tenant_id,
        ),
        "saturation_blocked": is_saturation_blocked_by_replay_storm_v1(
            session,
            tenant_id=tenant_id,
        ),
    }


def handle_replay_divergence_observed_v1(
    *,
    tenant_id: str,
    source: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """CESP handler invoked via ``replay_divergence_observability``."""
    try:
        tid = uuid.UUID(str(tenant_id))
    except ValueError:
        return
    try:
        from vector.infrastructure.db.session import session_scope

        with session_scope() as session:
            persist_replay_divergence_event_v1(
                session,
                tenant_id=tid,
                source=source,
                detail=detail,
            )
            evaluate_and_activate_replay_storm_v1(session, tenant_id=tid)
            session.commit()
    except Exception:  # noqa: BLE001
        _LOGGER.debug("replay_storm_persist_skipped tenant_id=%s", tenant_id, exc_info=True)


def build_replay_storm_handling_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_replay_storm_runtime_schema_version": int(
            PHASE085_REPLAY_STORM_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_REPLAY_STORM_SPEC_REF_V1,
        "primary_gate_id": GP085_ECON02_GATE_ID_V1,
        "divergence_spike_per_hour": get_replay_storm_divergence_spike_per_hour_v1(),
        "window_hours": get_replay_storm_window_hours_v1(),
        "evaluation_entrypoints": [
            "evaluate_replay_storm_for_tenant_v1",
            "operator_acknowledge_replay_storm_v1",
        ],
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_replay_storm_handling"
        ),
    }


def verify_gp085_econ02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_replay_storm_handling_catalog_v1()
    if cat["primary_gate_id"] != GP085_ECON02_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    from vector.domains.cortex.retrieval import retrieval_replay_equivalence as rre
    from vector.domains.cortex.synthesis import synthesis_replay_equivalence as sre

    if "on_replay_divergence_observed_v1" not in inspect.getsource(
        rre.record_retrieval_replay_divergence_v1
    ):
        errors.append("retrieval_divergence_missing_storm_hook")
    if "on_replay_divergence_observed_v1" not in inspect.getsource(
        sre.record_synthesis_replay_divergence_v1
    ):
        errors.append("synthesis_divergence_missing_storm_hook")

    from vector.domains.cortex.operational_runtime import substrate_tcre_saturation_scheduling as tss

    if "is_saturation_blocked_by_replay_storm_v1" not in inspect.getsource(
        tss.evaluate_tcre_saturation_schedule_v1
    ):
        errors.append("tcre_saturation_missing_storm_gate")

    from vector.domains.cortex.retrieval import query_execution as qe

    if "assert_exploration_partition_allowed_v1" not in inspect.getsource(
        qe.execute_retrieval_query_envelope_v1
    ):
        errors.append("retrieval_query_missing_exploration_storm_gate")

    passed = not errors
    return {
        "id": GP085_ECON02_GATE_ID_V1,
        "name": "cesp_substrate_replay_storm_handling",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
