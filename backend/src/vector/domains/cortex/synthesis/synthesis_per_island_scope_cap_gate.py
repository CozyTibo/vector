"""Phase C step C2 — per-island scope caps + fail-loud orchestrator errors."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import SynthesisOrchestratorError
from vector.domains.cortex.synthesis.synthesis_per_island import (
    iter_island_synthesis_scopes_v1,
    synthesis_per_island_max_scopes_per_island_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import synthesis_pipeline_max_scopes_v1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

PHASE_C2_SCOPE_CAP_SCHEMA_VERSION: Final[int] = 1
P0_C2_STEP: Final[str] = "step_c2_synthesis_per_island_scope_caps"
ORCHESTRATOR_FAIL_LOUD_CODE_V1: Final[str] = "synthesis_orchestrator_fail_loud"
ALL_SCOPES_FAILED_CODE_V1: Final[str] = "synthesis_per_island_all_scopes_failed"


class SynthesisPerIslandMaterializeError(ValueError):
    """Raised when per-island synthesis cannot complete lawfully (C2 fail-loud)."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = detail or {}
        super().__init__(code)


def is_synthesis_per_island_fail_loud_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_synthesis_per_island_fail_loud_on_orchestrator_error)
    except Exception:  # noqa: BLE001
        return True


def resolve_per_island_scope_cap_budget_v1(
    *,
    island_count: int,
    settings: Any | None = None,
    max_scopes_override: int | None = None,
) -> dict[str, Any]:
    """Bounded scopes per island: min(per-island cap, global_cap // island_count)."""
    from vector.settings import get_settings

    cfg = settings or get_settings()
    if max_scopes_override is not None:
        budget = max(1, int(max_scopes_override))
        source = "override"
    else:
        per_island_cap = synthesis_per_island_max_scopes_per_island_v1(settings=cfg)
        global_cap = synthesis_pipeline_max_scopes_v1(settings=cfg)
        shared = max(1, global_cap // max(1, island_count))
        budget = min(per_island_cap, shared)
        source = "settings"
    return {
        "scopes_budget_per_island": budget,
        "per_island_max_scopes_setting": synthesis_per_island_max_scopes_per_island_v1(settings=cfg),
        "global_pipeline_max_scopes": synthesis_pipeline_max_scopes_v1(settings=cfg),
        "island_count": max(1, island_count),
        "budget_source": source,
        "phase_c2_schema_version": PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
    }


def count_eligible_island_scopes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str,
    workloads: Sequence[str] | None = None,
) -> int:
    """Count scopes before cap (iterator with high ceiling)."""
    n = 0
    for _ in iter_island_synthesis_scopes_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published_index_epoch,
        island_scope_id=island_scope_id,
        max_scopes=1_000_000,
        workloads=workloads,
    ):
        n += 1
    return n


def materialize_capped_island_scopes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str,
    scopes_budget: int,
    workloads: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return capped scope list + eligibility audit for one island."""
    eligible = count_eligible_island_scopes_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published_index_epoch,
        island_scope_id=island_scope_id,
        workloads=workloads,
    )
    scopes = list(
        iter_island_synthesis_scopes_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=published_index_epoch,
            island_scope_id=island_scope_id,
            max_scopes=scopes_budget,
            workloads=workloads,
        )
    )
    return {
        "island_scope_id": island_scope_id,
        "scopes_eligible": eligible,
        "scopes_scheduled": len(scopes),
        "scopes_budget": scopes_budget,
        "scopes_capped": eligible > scopes_budget,
        "scopes": scopes,
    }


def should_fail_loud_on_orchestrator_exception_v1(exc: BaseException) -> bool:
    if not is_synthesis_per_island_fail_loud_enabled_v1():
        return False
    return isinstance(exc, SynthesisOrchestratorError)


def enforce_per_island_orchestrator_fail_loud_v1(
    exc: BaseException,
    *,
    island_scope_id: str,
    retrieval_lookup_id: str | None = None,
) -> None:
    """Re-raise orchestrator failures instead of silent per-scope swallow (C2)."""
    if should_fail_loud_on_orchestrator_exception_v1(exc):
        raise SynthesisPerIslandMaterializeError(
            ORCHESTRATOR_FAIL_LOUD_CODE_V1,
            detail={
                "island_scope_id": island_scope_id,
                "retrieval_lookup_id": retrieval_lookup_id,
                "orchestrator_error": str(exc)[:500],
            },
        ) from exc


def enforce_all_scopes_failed_fail_loud_v1(
    *,
    scopes_scheduled: int,
    jobs_completed: int,
    jobs_failed: int,
    per_island_scope_cap_audit: Sequence[dict[str, Any]] | None = None,
    per_island_scope_cap_budget: dict[str, Any] | None = None,
) -> None:
    """When every scheduled scope failed, surface failure to phase 08 (C2)."""
    if not is_synthesis_per_island_fail_loud_enabled_v1():
        return
    if scopes_scheduled > 0 and jobs_completed == 0 and jobs_failed > 0:
        detail: dict[str, Any] = {
            "scopes_scheduled": scopes_scheduled,
            "jobs_completed": jobs_completed,
            "jobs_failed": jobs_failed,
        }
        if per_island_scope_cap_audit is not None:
            detail["per_island_scope_cap_audit"] = list(per_island_scope_cap_audit)
        if per_island_scope_cap_budget is not None:
            detail["per_island_scope_cap_budget"] = per_island_scope_cap_budget
        raise SynthesisPerIslandMaterializeError(
            ALL_SCOPES_FAILED_CODE_V1,
            detail=detail,
        )


def _artifact_island_scope_id_v1(body: dict[str, Any]) -> str:
    if body.get("island_scope_id"):
        return str(body["island_scope_id"])
    for key in ("envelope", "job_envelope", "synthesis_job_envelope"):
        nested = body.get(key)
        if isinstance(nested, dict) and nested.get("island_scope_id"):
            return str(nested["island_scope_id"])
    return ""


def count_synthesis_artifacts_in_window_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 48,
    island_scope_id: str | None = None,
    published_only: bool = False,
) -> dict[str, Any]:
    """Count synthesis artifacts in SQL window (C2 / D-G1 style)."""
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    stmt = select(CortexSynthesisArtifact).where(
        CortexSynthesisArtifact.tenant_id == tenant_id,
        CortexSynthesisArtifact.created_at >= cutoff,
    )
    if published_only:
        stmt = stmt.where(CortexSynthesisArtifact.published.is_(True))
    rows = list(session.scalars(stmt.order_by(CortexSynthesisArtifact.created_at.desc())).all())
    if island_scope_id:
        primary_rows = [
            r
            for r in rows
            if _artifact_island_scope_id_v1(dict(r.body_json or {})) == island_scope_id
            or str(r.retrieval_lookup_id or "").startswith(island_scope_id)
        ]
    else:
        primary_rows = rows
    total = len(rows)
    published_rows = [r for r in rows if r.published]
    return {
        "lookback_hours": lookback_hours,
        "artifacts_total": total,
        "artifacts_published_in_window": len(published_rows),
        "artifacts_primary_island": len(primary_rows),
        "artifacts_primary_island_published": sum(1 for r in primary_rows if r.published),
        "primary_island_scope_id": island_scope_id,
        "latest_artifact_at": rows[0].created_at.isoformat() if rows else None,
        "published_only_query": published_only,
    }


def snapshot_primary_island_artifact_stats_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 48,
) -> dict[str, Any]:
    stats = count_synthesis_artifacts_in_window_v1(
        session,
        tenant_id=tenant_id,
        lookback_hours=lookback_hours,
        island_scope_id=FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
    )
    total_any = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.published.is_(True),
            )
        )
        or 0
    )
    return {**stats, "artifacts_published_total": total_any}
