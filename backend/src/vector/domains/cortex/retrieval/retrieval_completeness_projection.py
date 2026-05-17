"""Phase 07 P07-20 — substrate completeness + overview (retrieval stage).

Normative:
``DOCS/cortex/retrieval/phase-07-retrieval-completeness-doctrine.md``,
``DOCS/cortex/retrieval/phase-07-substrate-overview-integration.md``.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    compute_index_lag_epochs_v1,
    get_published_index_epoch_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import retrieval_policy_digest_v1
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    get_retrieval_replay_divergence_total_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_COMP01_GATE_ID_V1: Final[str] = "G-P07-COMP-01"

RETRIEVAL_COMPLETENESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-completeness-doctrine.md"
)

RETRIEVAL_SUBSTRATE_OVERVIEW_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-substrate-overview-integration.md"
)

RETRIEVAL_COVERAGE_THRESHOLD_PERCENT_V1: Final[float] = 90.0

RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1: Final[str] = "retrieval_index_never_built"
RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1: Final[str] = "retrieval_index_stale"
RETRIEVAL_STAGE_OMISSION_UPSTREAM_TCRE_GAP_V1: Final[str] = "retrieval_upstream_tcre_gap"
RETRIEVAL_STAGE_OMISSION_REPLAY_DIVERGENCE_V1: Final[str] = "retrieval_replay_divergence"


class RetrievalCompletenessError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def _count_tcre_indexable_artifacts_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    total = 0
    jobs = session.scalars(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status == "completed",
            CortexTcreReconstructionJob.job_kind == "reconstruct",
        )
        .limit(200)
    ).all()
    for job in jobs:
        summary = job.summary_json or {}
        total += int(
            summary.get("materialization_count")
            or summary.get("chronology_count")
            or summary.get("chronology_receipt_count")
            or summary.get("causal_edge_count")
            or 0
        )
    return total


def _count_completed_walks_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1

    store = resolve_octs_walk_store_v1(session)
    records = store.list_walk_records_for_tenant_v1(tenant_id)
    return sum(1 for r in records if r.status == "completed" and r.walk_payload)


def _count_authoritative_org_links_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(CortexOrgLink.tenant_id == tenant_id)
        )
        or 0
    )


def count_retrieval_eligible_artifacts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """**RET-COMP-01** — eligible indexable addresses (not raw row cardinality)."""
    tcre = _count_tcre_indexable_artifacts_v1(session, tenant_id=tenant_id)
    walks = _count_completed_walks_v1(session, tenant_id=tenant_id)
    graph_links = _count_authoritative_org_links_v1(session, tenant_id=tenant_id)
    eligible = tcre + walks + graph_links
    all_index_rows = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
        )
        or 0
    )
    return {
        "tcre_indexable_count": tcre,
        "walk_record_count": walks,
        "graph_link_count": graph_links,
        "eligible_artifact_count": max(eligible, all_index_rows),
    }


def count_retrieval_indexed_in_published_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    base_q = select(func.count()).select_from(CortexRetrievalIndexEntry).where(
        CortexRetrievalIndexEntry.tenant_id == tenant_id
    )
    if published:
        indexed = int(
            session.scalar(
                base_q.where(CortexRetrievalIndexEntry.index_epoch == published)
            )
            or 0
        )
        replay_safe = int(
            session.scalar(
                base_q.where(
                    CortexRetrievalIndexEntry.index_epoch == published,
                    CortexRetrievalIndexEntry.retrieval_legality_class
                    == "retrieval_replay_safe",
                )
            )
            or 0
        )
    else:
        indexed = 0
        replay_safe = 0
    return {
        "published_index_epoch": published,
        "indexed_count": indexed,
        "replay_safe_count": replay_safe,
    }


def _pct(numerator: int, denominator: int) -> float:
    from vector.domains.cortex.completeness._completeness_common import pct

    return pct(numerator, denominator)


def derive_retrieval_stage_substrate_state_v1(
    *,
    eligible: int,
    indexed: int,
    coverage_percent: float,
    published_epoch: str | None,
    replay_posture: str,
    pending_index_builds: int,
) -> str:
    """Never ``healthy`` (idle) when ``eligible > 0`` and nothing indexed (**RET-COMP-01**)."""
    if eligible == 0:
        return "healthy"
    if indexed == 0 or published_epoch is None:
        return "degraded"
    if replay_posture == "unsafe":
        return "degraded"
    if coverage_percent < RETRIEVAL_COVERAGE_THRESHOLD_PERCENT_V1:
        return "degraded"
    if pending_index_builds > 0:
        return "degraded"
    return "healthy"


def project_retrieval_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """7th pipeline stage envelope for substrate completeness ledger."""
    from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct

    eligible_breakdown = count_retrieval_eligible_artifacts_v1(session, tenant_id=tenant_id)
    eligible = int(eligible_breakdown["eligible_artifact_count"])
    index_stats = count_retrieval_indexed_in_published_epoch_v1(session, tenant_id=tenant_id)
    indexed = int(index_stats["indexed_count"])
    replay_safe = int(index_stats["replay_safe_count"])
    published = index_stats.get("published_index_epoch")
    lag = compute_index_lag_epochs_v1(session, tenant_id=tenant_id)
    stale_epochs = list(lag.get("stale_epochs") or [])

    coverage_percent = _pct(indexed, eligible if eligible else 1)
    replay_safe_percent = _pct(replay_safe, indexed if indexed else 1)

    pending_builds = int(lag.get("stale_epoch_count") or 0)
    if published is None and eligible > 0:
        pending_builds = max(pending_builds, 1)

    never_indexed = eligible > 0 and indexed == 0
    omission_classes: dict[str, int] = {}
    if never_indexed:
        omission_classes[RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1] = 1
    if stale_epochs:
        omission_classes[RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1] = len(stale_epochs)
    tcre_gap = max(0, eligible_breakdown["tcre_indexable_count"] - indexed)
    if tcre_gap > 0 and not never_indexed:
        omission_classes[RETRIEVAL_STAGE_OMISSION_UPSTREAM_TCRE_GAP_V1] = tcre_gap
    divergence_total = get_retrieval_replay_divergence_total_v1()
    if divergence_total > 0:
        omission_classes[RETRIEVAL_STAGE_OMISSION_REPLAY_DIVERGENCE_V1] = divergence_total

    replay_posture = "stable"
    if divergence_total > 0:
        replay_posture = "unsafe"
    elif coverage_percent < RETRIEVAL_COVERAGE_THRESHOLD_PERCENT_V1 and eligible > 0:
        replay_posture = "partial"
    elif never_indexed:
        replay_posture = "unknown"

    substrate_state = derive_retrieval_stage_substrate_state_v1(
        eligible=eligible,
        indexed=indexed,
        coverage_percent=coverage_percent,
        published_epoch=str(published) if published else None,
        replay_posture=replay_posture,
        pending_index_builds=pending_builds,
    )

    degraded_count = indexed - replay_safe if indexed > replay_safe else 0
    unresolved = max(0, eligible - indexed)

    drift_warnings: list[str] = []
    if never_indexed:
        drift_warnings.append(
            "Eligible retrieval artifacts exist but no published index epoch — run index rebuild."
        )
    if stale_epochs:
        drift_warnings.append(f"stale_index_epochs={','.join(stale_epochs[:5])}")

    assert_retrieval_never_idle_healthy_when_eligible_v1(
        eligible_artifact_count=eligible,
        indexed_count=indexed,
        substrate_state=substrate_state,
    )

    return build_stage_envelope_v1(
        stage_id="retrieval",
        label="Retrieval",
        total_objects=eligible if eligible else indexed,
        processed_count=indexed,
        degraded_count=degraded_count,
        unresolved_count=unresolved,
        omitted_count=sum(omission_classes.values()),
        intentionally_excluded_count=pending_builds if pending_builds else 0,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=str(published) if published else None,
        drift_warnings=drift_warnings,
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/retrieval",
        metrics={
            "eligible_artifact_count": eligible,
            "indexed_count": indexed,
            "retrieval_coverage_percent": coverage_percent,
            "replay_safe_query_percent": replay_safe_percent,
            "walk_record_count": eligible_breakdown["walk_record_count"],
            "retrieval_never_indexed": never_indexed,
            "published_index_epoch": published,
            "pending_index_build_count": pending_builds,
            "retrieval_replay_divergence_total": divergence_total,
            **eligible_breakdown,
        },
    )


def build_retrieval_coverage_catalog_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin ``GET .../coverage`` — completeness metrics (coverage independent of query replay)."""
    stage = project_retrieval_completeness_v1(session, tenant_id=tenant_id)
    metrics = dict(stage.get("metrics") or {})
    index_stats = count_retrieval_indexed_in_published_epoch_v1(session, tenant_id=tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "retrieval_completeness_runtime_schema_version": (
            PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION
        ),
        "stage_id": "retrieval",
        "substrate_state": stage.get("substrate_state"),
        "replay_posture": stage.get("replay_posture"),
        "indexed_count": int(metrics.get("indexed_count", 0)),
        "replay_safe_count": int(index_stats["replay_safe_count"]),
        "eligible_artifact_count": int(metrics.get("eligible_artifact_count", 0)),
        "coverage_percent": float(metrics.get("retrieval_coverage_percent", 0.0)),
        "replay_safe_query_percent": float(metrics.get("replay_safe_query_percent", 0.0)),
        "walk_record_count": metrics.get("walk_record_count", 0),
        "retrieval_never_indexed": metrics.get("retrieval_never_indexed", False),
        "published_index_epoch": metrics.get("published_index_epoch"),
        "intentionally_excluded_count": stage.get("intentionally_excluded_count", 0),
        "omission_classes": dict(stage.get("omission_classes") or {}),
        "index_lag_epochs": compute_index_lag_epochs_v1(session, tenant_id=tenant_id),
        "retrieval_policy_digest": retrieval_policy_digest_v1(),
    }


def build_retrieval_overview_catalog_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin overview card + drill-down (coverage strip, stage envelope, policy digest)."""
    coverage = build_retrieval_coverage_catalog_v1(session, tenant_id=tenant_id)
    stage = project_retrieval_completeness_v1(session, tenant_id=tenant_id)
    return {
        **coverage,
        "stage_envelope": stage,
        "doctrine_anchors": [
            RETRIEVAL_COMPLETENESS_SPEC_REF_V1,
            RETRIEVAL_SUBSTRATE_OVERVIEW_SPEC_REF_V1,
        ],
        "drill_down": {
            "coverage_strip": {
                "eligible": coverage.get("eligible_artifact_count"),
                "indexed": coverage.get("indexed_count"),
                "coverage_percent": coverage.get("coverage_percent"),
            },
            "routes": {
                "query_debugger": f"/admin/tenants/{tenant_id}/cortex/retrieval",
                "lineage_explorer": f"/admin/tenants/{tenant_id}/cortex/retrieval/lineage",
                "degradation_topology": f"/admin/tenants/{tenant_id}/cortex/retrieval/degradation-topology",
            },
        },
    }


def assert_retrieval_never_idle_healthy_when_eligible_v1(
    *,
    eligible_artifact_count: int,
    indexed_count: int,
    substrate_state: str,
) -> None:
    """Legality: never idle-healthy when eligible > 0 and index empty."""
    if eligible_artifact_count > 0 and indexed_count == 0 and substrate_state == "healthy":
        raise RetrievalCompletenessError(
            "retrieval_idle_healthy_with_eligible_artifacts",
            detail={
                "eligible_artifact_count": eligible_artifact_count,
                "indexed_count": indexed_count,
            },
        )


def _comp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_COMP01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase07_retrieval_completeness_runtime_schema_version": (
                PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp07_comp01_never_idle_healthy_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        assert_retrieval_never_idle_healthy_when_eligible_v1(
            eligible_artifact_count=5,
            indexed_count=0,
            substrate_state="healthy",
        )
    except RetrievalCompletenessError:
        pass
    else:
        errors.append("expected_idle_healthy_rejection")
    try:
        assert_retrieval_never_idle_healthy_when_eligible_v1(
            eligible_artifact_count=0,
            indexed_count=0,
            substrate_state="healthy",
        )
    except RetrievalCompletenessError as exc:
        errors.append(f"idle_zero_eligible_should_pass:{exc}")
    state = derive_retrieval_stage_substrate_state_v1(
        eligible=10,
        indexed=0,
        coverage_percent=0.0,
        published_epoch=None,
        replay_posture="unknown",
        pending_index_builds=1,
    )
    if state != "degraded":
        errors.append(f"never_built_state:{state}")
    return _comp_meta("gp07_comp01_never_idle_healthy", errors)


def verify_gp07_comp01_coverage_threshold_static() -> dict[str, Any]:
    errors: list[str] = []
    if RETRIEVAL_COVERAGE_THRESHOLD_PERCENT_V1 <= 0:
        errors.append("invalid_threshold")
    low_cov = derive_retrieval_stage_substrate_state_v1(
        eligible=100,
        indexed=50,
        coverage_percent=50.0,
        published_epoch="epoch-1",
        replay_posture="partial",
        pending_index_builds=0,
    )
    if low_cov != "degraded":
        errors.append("low_coverage_should_degrade")
    return _comp_meta("gp07_comp01_coverage_threshold", errors)
