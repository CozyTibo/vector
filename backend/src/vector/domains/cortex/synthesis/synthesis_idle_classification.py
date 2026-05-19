"""Phase 08 / 08.5 — synthesis idle vs starved classification (**G-P085-SYN-02**).

Core classification lives in the synthesis package (acyclic law: synthesis MUST NOT import CESP).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    project_retrieval_completeness_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
    count_synthesis_synthesized_scopes_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

GP085_SYN02_GATE_ID_V1: Final[str] = "G-P085-SYN-02"

SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1: Final[str] = "healthy_idle"
SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1: Final[str] = "operational_starvation"
SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1: Final[str] = "legality_blocked"
SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1: Final[str] = "continuity_incomplete"
SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1: Final[str] = "replay_unsafe"
SYNTHESIS_CLASSIFICATION_PROGRESSING_V1: Final[str] = "progressing"

SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1: Final[str] = "synthesis_operational_starvation"

METRIC_SYNTHESIS_CLASSIFICATION_V1: Final[str] = "synthesis_classification"
METRIC_SYNTHESIS_OPERATIONAL_STARVATION_V1: Final[str] = "operational_starvation"
METRIC_SYNTHESIS_IDLE_UI_COLOR_V1: Final[str] = "synthesis_idle_ui_color"

_CLASSIFICATION_UI_COLORS_V1: Final[dict[str, str]] = {
    SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1: "neutral_green",
    SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1: "amber_red",
    SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1: "red",
    SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1: "amber",
    SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1: "red",
    SYNTHESIS_CLASSIFICATION_PROGRESSING_V1: "neutral_green",
}


class SynthesisIdleClassificationError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def synthesis_classification_ui_color_v1(classification: str) -> str:
    return _CLASSIFICATION_UI_COLORS_V1.get(classification, "amber")


def _count_recent_synthesis_forbidden_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    try:
        from vector.settings import get_settings

        threshold = max(1, int(get_settings().cortex_synthesis_forbidden_backoff_threshold))
        window_hours = max(1, int(get_settings().cortex_synthesis_forbidden_backoff_window_hours))
    except Exception:  # noqa: BLE001
        threshold = 3
        window_hours = 24
    since = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    forbidden_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.synthesis_legality_class == "synthesis_forbidden",
                CortexSynthesisJob.created_at >= since,
            )
        )
        or 0
    )
    return {
        "forbidden_count": forbidden_count,
        "forbidden_backoff_threshold": threshold,
        "forbidden_backoff_window_hours": window_hours,
        "forbidden_backoff_active": forbidden_count >= threshold,
    }


def _refresh_stage_envelope_receipt_digest_v1(stage: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(stage)
    payload = {
        "stage_id": out.get("stage_id"),
        "substrate_state": out.get("substrate_state"),
        "total_objects": out.get("total_objects"),
        "processed_count": out.get("processed_count"),
        "omission_classes": out.get("omission_classes"),
        "metrics": out.get("metrics"),
    }
    out["receipt_digest"] = hash_reasoning_canonical_json_sha256_v1(payload)
    return out


def evaluate_synthesis_classification_context_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Gather inputs for **G-P085-SYN-02** eligibility classification."""
    scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    synth = count_synthesis_synthesized_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scope.get("eligible_scopes") or 0)
    synthesized = int(synth.get("synthesized_scopes") or 0)

    retrieval_stage = project_retrieval_completeness_v1(session, tenant_id=tenant_id)
    ret_metrics = dict(retrieval_stage.get("metrics") or {})
    retrieval_operational_starvation = bool(ret_metrics.get("operational_starvation"))
    upstream_work_present = bool(
        int(ret_metrics.get("walk_record_count") or 0) > 0
        or int(ret_metrics.get("tcre_indexable_count") or 0) > 0
        or int(ret_metrics.get("eligible_artifact_count") or 0) > 0
    )

    forbidden_metrics = _count_recent_synthesis_forbidden_v1(session, tenant_id=tenant_id)

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    continuation = (
        get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
        if running is not None
        else None
    )
    continuation_status = continuation.continuation_status if continuation else None
    pipeline_waiting = continuation_status == CONTINUATION_STATUS_WAITING
    pipeline_stalled = continuation_status == CONTINUATION_STATUS_STALLED

    stage_metrics = dict((stage or {}).get("metrics") or {})
    health_state = str(stage_metrics.get("substrate_health_state") or "healthy")
    replay_posture = str((stage or {}).get("replay_posture") or "stable")

    return {
        "tenant_id": str(tenant_id),
        "eligible_scopes": eligible,
        "synthesized_scopes": synthesized,
        "retrieval_operational_starvation": retrieval_operational_starvation,
        "retrieval_idle_class": str(ret_metrics.get("retrieval_card_classification") or ""),
        "upstream_work_present": upstream_work_present,
        "forbidden_count": int(forbidden_metrics.get("forbidden_count") or 0),
        "forbidden_backoff_active": bool(forbidden_metrics.get("forbidden_backoff_active")),
        "pipeline_waiting": pipeline_waiting,
        "pipeline_stalled": pipeline_stalled,
        "continuation_status": continuation_status,
        "substrate_health_state": health_state,
        "replay_posture": replay_posture,
        "replay_unsafe": health_state == "replay_conflicted" or replay_posture == "unsafe",
    }


def classify_synthesis_eligibility_v1(
    *,
    eligible_scopes: int,
    synthesized_scopes: int,
    retrieval_operational_starvation: bool,
    upstream_work_present: bool,
    forbidden_count: int,
    forbidden_backoff_active: bool,
    pipeline_waiting: bool,
    pipeline_stalled: bool,
    replay_unsafe: bool,
) -> dict[str, Any]:
    """Doctrine table — deterministic synthesis eligibility classification."""
    if replay_unsafe:
        classification = SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1
    elif forbidden_backoff_active or forbidden_count > 0:
        classification = SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1
    elif pipeline_waiting or pipeline_stalled:
        classification = SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1
    elif eligible_scopes == 0 and (
        retrieval_operational_starvation
        or (upstream_work_present and synthesized_scopes == 0)
    ):
        classification = SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1
    elif eligible_scopes > 0:
        classification = SYNTHESIS_CLASSIFICATION_PROGRESSING_V1
    else:
        classification = SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1

    operational_starvation = classification == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1
    return {
        "classification": classification,
        METRIC_SYNTHESIS_OPERATIONAL_STARVATION_V1: operational_starvation,
        METRIC_SYNTHESIS_IDLE_UI_COLOR_V1: synthesis_classification_ui_color_v1(classification),
    }


def coerce_synthesis_substrate_state_for_classification_v1(
    *,
    substrate_state: str,
    classification: str,
) -> tuple[str, list[str]]:
    """**G-P085-SYN-02** — synthesis stage MUST NOT be ``healthy`` under operational starvation."""
    drift: list[str] = []
    if (
        classification == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1
        and substrate_state == "healthy"
    ):
        drift.append(
            f"{GP085_SYN02_GATE_ID_V1}: operational_starvation — "
            "substrate_state coerced from healthy"
        )
        return "degraded", drift
    if classification == SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1 and substrate_state == "healthy":
        drift.append(f"{GP085_SYN02_GATE_ID_V1}: replay_unsafe — substrate_state coerced from healthy")
        return "degraded", drift
    if classification == SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1 and substrate_state == "healthy":
        drift.append(
            f"{GP085_SYN02_GATE_ID_V1}: legality_blocked — substrate_state coerced from healthy"
        )
        return "critical", drift
    return substrate_state, drift


def assert_synthesis_never_healthy_under_operational_starvation_v1(
    *,
    classification: str,
    substrate_state: str,
) -> None:
    if (
        classification == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1
        and substrate_state == "healthy"
    ):
        raise SynthesisIdleClassificationError(
            "synthesis_healthy_forbidden_under_operational_starvation",
            detail={"classification": classification, "substrate_state": substrate_state},
        )


def apply_synthesis_idle_classification_to_stage_v1(
    stage: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply classification metrics, omissions, and substrate coercion to synthesis stage."""
    out = dict(stage)
    metrics = dict(out.get("metrics") or {})
    metrics[METRIC_SYNTHESIS_CLASSIFICATION_V1] = classification["classification"]
    metrics[METRIC_SYNTHESIS_OPERATIONAL_STARVATION_V1] = classification[
        METRIC_SYNTHESIS_OPERATIONAL_STARVATION_V1
    ]
    metrics[METRIC_SYNTHESIS_IDLE_UI_COLOR_V1] = classification[METRIC_SYNTHESIS_IDLE_UI_COLOR_V1]
    metrics["synthesis_idle_classification"] = classification["classification"]
    metrics["cesp_synthesis_idle_gate_id"] = GP085_SYN02_GATE_ID_V1
    metrics["gp085_syn02_context"] = {
        "eligible_scopes": context.get("eligible_scopes"),
        "retrieval_operational_starvation": context.get("retrieval_operational_starvation"),
        "forbidden_count": context.get("forbidden_count"),
    }
    out["metrics"] = metrics

    omission_classes = dict(out.get("omission_classes") or {})
    if classification["classification"] == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1:
        omission_classes[SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1] = 1
    out["omission_classes"] = omission_classes

    substrate_state = str(out.get("substrate_state") or "healthy")
    coerced, drift = coerce_synthesis_substrate_state_for_classification_v1(
        substrate_state=substrate_state,
        classification=str(classification["classification"]),
    )
    if coerced != substrate_state:
        out["substrate_state"] = coerced
        drift_warnings = list(out.get("drift_warnings") or [])
        drift_warnings.extend(drift)
        out["drift_warnings"] = drift_warnings

    assert_synthesis_never_healthy_under_operational_starvation_v1(
        classification=str(classification["classification"]),
        substrate_state=str(out.get("substrate_state") or "healthy"),
    )
    return _refresh_stage_envelope_receipt_digest_v1(out)


def project_synthesis_completeness_with_idle_classification_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Project synthesis stage envelope with **G-P085-SYN-02** card law."""
    from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
        _project_synthesis_completeness_without_classification_v1,
    )

    stage = _project_synthesis_completeness_without_classification_v1(session, tenant_id=tenant_id)
    context = evaluate_synthesis_classification_context_v1(
        session,
        tenant_id=tenant_id,
        stage=stage,
    )
    classification = classify_synthesis_eligibility_v1(
        eligible_scopes=int(context["eligible_scopes"]),
        synthesized_scopes=int(context["synthesized_scopes"]),
        retrieval_operational_starvation=bool(context["retrieval_operational_starvation"]),
        upstream_work_present=bool(context["upstream_work_present"]),
        forbidden_count=int(context["forbidden_count"]),
        forbidden_backoff_active=bool(context["forbidden_backoff_active"]),
        pipeline_waiting=bool(context["pipeline_waiting"]),
        pipeline_stalled=bool(context["pipeline_stalled"]),
        replay_unsafe=bool(context["replay_unsafe"]),
    )
    return apply_synthesis_idle_classification_to_stage_v1(
        stage,
        context=context,
        classification=classification,
    )
