"""Phase 08.5 P085-21 — retrieval density maturity (**G-P085-RET-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-retrieval-density-doctrine.md``.
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.retrieval.retrieval_density_metrics import (
    get_retrieval_density_metrics_snapshot_v1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import RET_SKIP_CODES_V1
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
    CortexRetrievalMaterializationReport,
)

PHASE085_RETRIEVAL_DENSITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_RETRIEVAL_DENSITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-retrieval-density-doctrine.md"
)

GP085_RET01_GATE_ID_V1: Final[str] = "G-P085-RET-01"

METRIC_RETRIEVAL_ELIGIBLE_ARTIFACT_COUNT_V1: Final[str] = "retrieval_eligible_artifact_count"
METRIC_RETRIEVAL_INDEXED_COUNT_V1: Final[str] = "retrieval_indexed_count"
METRIC_RETRIEVAL_DENSITY_PERCENT_V1: Final[str] = "retrieval_density_percent"
METRIC_RETRIEVAL_DENSITY_SCORE_V1: Final[str] = "retrieval_density_score"
METRIC_RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1: Final[str] = "retrieval_rows_materialized_total"
METRIC_RETRIEVAL_ROW_ACCEPTANCE_RATE_V1: Final[str] = "retrieval_row_acceptance_rate"
METRIC_RETRIEVAL_EPOCH_EMPTY_RATE_V1: Final[str] = "retrieval_epoch_empty_rate"
METRIC_ELIGIBLE_SCOPE_GROWTH_RATE_V1: Final[str] = "eligible_scope_growth_rate"

RETRIEVAL_DENSITY_METRIC_IDS_V1: Final[tuple[str, ...]] = (
    METRIC_RETRIEVAL_ELIGIBLE_ARTIFACT_COUNT_V1,
    METRIC_RETRIEVAL_INDEXED_COUNT_V1,
    METRIC_RETRIEVAL_DENSITY_PERCENT_V1,
    METRIC_RETRIEVAL_DENSITY_SCORE_V1,
    METRIC_RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1,
    METRIC_RETRIEVAL_ROW_ACCEPTANCE_RATE_V1,
    METRIC_RETRIEVAL_EPOCH_EMPTY_RATE_V1,
    METRIC_ELIGIBLE_SCOPE_GROWTH_RATE_V1,
)

RETRIEVAL_MATURITY_RET0_V1: Final[str] = "RET0"
RETRIEVAL_MATURITY_RET1_V1: Final[str] = "RET1"
RETRIEVAL_MATURITY_RET2_V1: Final[str] = "RET2"
RETRIEVAL_MATURITY_RET3_V1: Final[str] = "RET3"

RETRIEVAL_MATURITY_CLASS_IDS_V1: Final[tuple[str, ...]] = (
    RETRIEVAL_MATURITY_RET0_V1,
    RETRIEVAL_MATURITY_RET1_V1,
    RETRIEVAL_MATURITY_RET2_V1,
    RETRIEVAL_MATURITY_RET3_V1,
)

RETRIEVAL_MATURITY_RET1_DENSITY_LT_V1: Final[float] = 25.0
RETRIEVAL_MATURITY_RET3_DENSITY_GTE_V1: Final[float] = 85.0
RETRIEVAL_DENSITY_EMERGING_GTE_V1: Final[float] = 40.0

_SKIP_REQUIRED_KEYS_V1: Final[frozenset[str]] = frozenset(
    {"upstream_code", "ret_skip_code", "replay_safe"}
)


class SubstrateRetrievalDensityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_latest_retrieval_materialization_report_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexRetrievalMaterializationReport | None:
    return session.scalar(
        select(CortexRetrievalMaterializationReport)
        .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
        .order_by(CortexRetrievalMaterializationReport.created_at.desc())
        .limit(1)
    )


def _entry_count_from_report_v1(row: CortexRetrievalMaterializationReport) -> int:
    body = dict(row.report_json or {})
    return int(body.get("entry_count") or row.accepted_rows or 0)


def _report_publish_stats_v1(
    rows: list[CortexRetrievalMaterializationReport],
) -> tuple[int, int, int]:
    accepted = sum(int(r.accepted_rows) for r in rows)
    skipped = sum(int(r.skipped_rows) for r in rows)
    empty_epochs = sum(1 for r in rows if _entry_count_from_report_v1(r) <= 0)
    return accepted, skipped, empty_epochs


def compute_eligible_scope_growth_rate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> float:
    """Delta eligible candidates per hour from last two materialization reports."""
    rows = list(
        session.scalars(
            select(CortexRetrievalMaterializationReport)
            .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
            .order_by(CortexRetrievalMaterializationReport.created_at.desc())
            .limit(2)
        ).all()
    )
    if len(rows) < 2:
        return 0.0
    newer, older = rows[0], rows[1]
    if newer.created_at is None or older.created_at is None:
        return 0.0
    dt_hours = (newer.created_at - older.created_at).total_seconds() / 3600.0
    if dt_hours <= 0:
        return 0.0
    scope_new = int(newer.tcre_candidates + newer.walks_candidates + newer.org_link_candidates)
    scope_old = int(older.tcre_candidates + older.walks_candidates + older.org_link_candidates)
    return round((scope_new - scope_old) / dt_hours, 4)


def compute_retrieval_density_percent_v1(
    *,
    retrieval_indexed_count: int,
    retrieval_eligible_artifact_count: int,
) -> float:
    if retrieval_eligible_artifact_count <= 0:
        return 0.0
    ratio = float(retrieval_indexed_count) / float(retrieval_eligible_artifact_count)
    return round(min(100.0, max(0.0, ratio * 100.0)), 2)


def compute_retrieval_density_score_v1(*, retrieval_density_percent: float) -> int:
    return int(min(100, max(0, round(retrieval_density_percent))))


def classify_retrieval_maturity_class_v1(
    *,
    retrieval_density_percent: float,
    published_index_epoch: str | None,
) -> str:
    if not published_index_epoch:
        return RETRIEVAL_MATURITY_RET0_V1
    if retrieval_density_percent >= RETRIEVAL_MATURITY_RET3_DENSITY_GTE_V1:
        return RETRIEVAL_MATURITY_RET3_V1
    if retrieval_density_percent >= RETRIEVAL_MATURITY_RET1_DENSITY_LT_V1:
        return RETRIEVAL_MATURITY_RET2_V1
    return RETRIEVAL_MATURITY_RET1_V1


def derive_retrieval_density_substrate_state_v1(
    *,
    eligible: int,
    indexed: int,
    published_epoch: str | None,
    upstream_tcre_pending: bool = False,
    upstream_work_present: bool = False,
    replay_posture: str = "unknown",
    pending_index_builds: int = 0,
    coverage_percent: float = 0.0,
) -> str:
    """Never ``healthy`` when eligible > 0 and indexed = 0 (**G-P085-RET-01**)."""
    from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
        derive_retrieval_stage_substrate_state_v1,
    )

    return derive_retrieval_stage_substrate_state_v1(
        eligible=eligible,
        indexed=indexed,
        coverage_percent=coverage_percent,
        published_epoch=published_epoch,
        replay_posture=replay_posture,
        pending_index_builds=pending_index_builds,
        upstream_tcre_pending=upstream_tcre_pending,
        upstream_work_present=upstream_work_present,
    )


def compute_retrieval_density_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant retrieval density snapshot (**G-P085-RET-01**)."""
    from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
        count_retrieval_eligible_artifacts_v1,
        count_retrieval_indexed_in_published_epoch_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        compute_index_lag_epochs_v1,
    )

    eligible_breakdown = count_retrieval_eligible_artifacts_v1(session, tenant_id=tenant_id)
    eligible = int(eligible_breakdown["eligible_artifact_count"])
    index_stats = count_retrieval_indexed_in_published_epoch_v1(session, tenant_id=tenant_id)
    indexed = int(index_stats["indexed_count"])
    published = index_stats.get("published_index_epoch")
    published_str = str(published) if published else None

    density_percent = compute_retrieval_density_percent_v1(
        retrieval_indexed_count=indexed,
        retrieval_eligible_artifact_count=eligible,
    )
    density_score = compute_retrieval_density_score_v1(
        retrieval_density_percent=density_percent,
    )
    maturity_class = classify_retrieval_maturity_class_v1(
        retrieval_density_percent=density_percent,
        published_index_epoch=published_str,
    )

    report_rows = list(
        session.scalars(
            select(CortexRetrievalMaterializationReport)
            .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
            .order_by(CortexRetrievalMaterializationReport.created_at.desc())
            .limit(64)
        ).all()
    )
    accepted_total, skipped_total, empty_epochs = _report_publish_stats_v1(report_rows)
    publish_count = len(report_rows)
    denom = accepted_total + skipped_total
    acceptance_rate = float(accepted_total) / float(denom) if denom > 0 else 0.0
    empty_rate = float(empty_epochs) / float(publish_count) if publish_count > 0 else 0.0

    ephemeral = get_retrieval_density_metrics_snapshot_v1()
    growth_rate = compute_eligible_scope_growth_rate_v1(session, tenant_id=tenant_id)
    lag = compute_index_lag_epochs_v1(session, tenant_id=tenant_id)
    pending_builds = int(lag.get("stale_epoch_count") or 0)
    if published_str is None and eligible > 0:
        pending_builds = max(pending_builds, 1)

    from vector.domains.cortex.completeness.tcre_completeness_projection import (
        project_tcre_completeness_v1,
    )
    from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
        upstream_work_exists_v1,
    )
    from vector.domains.cortex.completeness.graph_completeness_projection import (
        project_graph_completeness_v1,
    )

    tcre_stage = project_tcre_completeness_v1(session, tenant_id=tenant_id)
    graph_stage = project_graph_completeness_v1(session, tenant_id=tenant_id)
    tcre_omissions = dict(tcre_stage.get("omission_classes") or {})
    upstream_tcre_pending = bool(tcre_stage.get("metrics", {}).get("reconstruction_never_run")) or int(
        tcre_omissions.get("reconstruction_not_yet_run") or 0
    ) > 0
    upstream_work = upstream_work_exists_v1({"tcre": tcre_stage, "graph": graph_stage})

    substrate_state = derive_retrieval_density_substrate_state_v1(
        eligible=eligible,
        indexed=indexed,
        published_epoch=published_str,
        upstream_tcre_pending=upstream_tcre_pending,
        upstream_work_present=upstream_work,
        replay_posture="unknown",
        pending_index_builds=pending_builds,
        coverage_percent=density_percent,
    )

    latest_report = report_rows[0] if report_rows else None

    metrics = {
        METRIC_RETRIEVAL_ELIGIBLE_ARTIFACT_COUNT_V1: eligible,
        METRIC_RETRIEVAL_INDEXED_COUNT_V1: indexed,
        METRIC_RETRIEVAL_DENSITY_PERCENT_V1: density_percent,
        METRIC_RETRIEVAL_DENSITY_SCORE_V1: density_score,
        METRIC_RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1: accepted_total,
        METRIC_RETRIEVAL_ROW_ACCEPTANCE_RATE_V1: round(acceptance_rate, 4),
        METRIC_RETRIEVAL_EPOCH_EMPTY_RATE_V1: round(empty_rate, 4),
        METRIC_ELIGIBLE_SCOPE_GROWTH_RATE_V1: growth_rate,
        "published_index_epoch": published_str,
        "materialization_report_count": publish_count,
        "density_emerging": density_percent >= RETRIEVAL_DENSITY_EMERGING_GTE_V1,
        **eligible_breakdown,
    }

    detail_route = f"/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-density"
    if latest_report is not None:
        detail_route = (
            f"{detail_route}?materialization_report_id={latest_report.id}"
        )

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_RET01_GATE_ID_V1,
        "retrieval_maturity_class": maturity_class,
        "substrate_state": substrate_state,
        "metrics": metrics,
        "latest_materialization_report_id": str(latest_report.id) if latest_report else None,
        "detail_route": detail_route,
        "ephemeral_global_metrics": ephemeral,
    }


def build_retrieval_density_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    snap = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    metrics = dict(snap["metrics"])
    return {
        "surface_kind": "retrieval_density_card",
        "gate_id": GP085_RET01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "retrieval_maturity_class": snap["retrieval_maturity_class"],
        "substrate_state": snap["substrate_state"],
        METRIC_RETRIEVAL_ELIGIBLE_ARTIFACT_COUNT_V1: metrics[
            METRIC_RETRIEVAL_ELIGIBLE_ARTIFACT_COUNT_V1
        ],
        METRIC_RETRIEVAL_INDEXED_COUNT_V1: metrics[METRIC_RETRIEVAL_INDEXED_COUNT_V1],
        METRIC_RETRIEVAL_DENSITY_PERCENT_V1: metrics[METRIC_RETRIEVAL_DENSITY_PERCENT_V1],
        METRIC_RETRIEVAL_DENSITY_SCORE_V1: metrics[METRIC_RETRIEVAL_DENSITY_SCORE_V1],
        "metrics": metrics,
        "latest_materialization_report_id": snap.get("latest_materialization_report_id"),
        "detail_route": snap["detail_route"],
    }


def build_substrate_retrieval_density_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_retrieval_density_runtime_schema_version": int(
            PHASE085_RETRIEVAL_DENSITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_RETRIEVAL_DENSITY_SPEC_REF_V1,
        "primary_gate_id": GP085_RET01_GATE_ID_V1,
        "metric_ids": list(RETRIEVAL_DENSITY_METRIC_IDS_V1),
        "retrieval_maturity_class_ids": list(RETRIEVAL_MATURITY_CLASS_IDS_V1),
        "maturity_thresholds": {
            "ret0_no_published_epoch": True,
            "ret1_density_lt_percent": RETRIEVAL_MATURITY_RET1_DENSITY_LT_V1,
            "ret2_density_range_percent": [
                RETRIEVAL_MATURITY_RET1_DENSITY_LT_V1,
                RETRIEVAL_MATURITY_RET3_DENSITY_GTE_V1,
            ],
            "ret3_density_gte_percent": RETRIEVAL_MATURITY_RET3_DENSITY_GTE_V1,
            "density_emerging_gte_percent": RETRIEVAL_DENSITY_EMERGING_GTE_V1,
        },
        "skip_code_prefix": "RET-SKIP-",
        "materialization_report_table": "cortex_retrieval_materialization_reports",
        "density_formula": "indexed_rows_in_published_epoch / eligible_indexable_addresses",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_retrieval_density"
        ),
        "density_entrypoint": "compute_retrieval_density_metrics_v1",
        "materialization_entrypoint": "materialize_retrieval_index_for_pipeline_v1",
    }


def verify_gp085_ret01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_retrieval_density_catalog_v1()
    if cat["primary_gate_id"] != GP085_RET01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["metric_ids"]) != set(RETRIEVAL_DENSITY_METRIC_IDS_V1):
        errors.append("metric_ids_mismatch")

    pct = compute_retrieval_density_percent_v1(
        retrieval_indexed_count=40,
        retrieval_eligible_artifact_count=100,
    )
    if pct != 40.0:
        errors.append("density_percent_formula")
    if compute_retrieval_density_score_v1(retrieval_density_percent=40.0) != 40:
        errors.append("density_score_alignment")

    if (
        classify_retrieval_maturity_class_v1(
            retrieval_density_percent=0.0,
            published_index_epoch=None,
        )
        != RETRIEVAL_MATURITY_RET0_V1
    ):
        errors.append("maturity_ret0")
    if (
        classify_retrieval_maturity_class_v1(
            retrieval_density_percent=90.0,
            published_index_epoch="epoch-1",
        )
        != RETRIEVAL_MATURITY_RET3_V1
    ):
        errors.append("maturity_ret3")

    if (
        derive_retrieval_density_substrate_state_v1(
            eligible=10,
            indexed=0,
            published_epoch=None,
        )
        != "degraded"
    ):
        errors.append("eligible_unindexed_must_degrade")

    from vector.domains.cortex.retrieval import retrieval_index_materialization as rim

    if "persist_retrieval_materialization_report_v1" not in inspect.getsource(
        rim.materialize_retrieval_index_for_pipeline_v1
    ):
        errors.append("pipeline_materialization_missing_report_persist")

    from vector.domains.cortex.retrieval.retrieval_skip_registry import (
        normalize_retrieval_skip_reason_v1,
    )

    row = normalize_retrieval_skip_reason_v1(source="walk", code="walk_incomplete")
    if not _SKIP_REQUIRED_KEYS_V1.issubset(set(row.keys())):
        errors.append("ret_skip_missing_required_keys")
    if row["ret_skip_code"] not in RET_SKIP_CODES_V1:
        errors.append("ret_skip_not_canonical")

    from vector.domains.cortex.operational_runtime import retrieval_completeness_propagation as rcp

    if "compute_retrieval_density_metrics_v1" not in inspect.getsource(
        rcp.propagate_retrieval_completeness_stage_v1
    ):
        errors.append("propagation_missing_density_integration")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "evaluate_operational_health_dimensions_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_health01_delegate")

    passed = not errors
    return {
        "id": GP085_RET01_GATE_ID_V1,
        "name": "cesp_substrate_retrieval_density",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
