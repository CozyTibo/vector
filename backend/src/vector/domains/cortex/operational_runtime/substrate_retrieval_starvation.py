"""Phase 08.5 P085-22 — retrieval index freshness + starvation gates (**G-P085-RET-02**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-retrieval-density-doctrine.md`` §Starvation.
"""

from __future__ import annotations

import inspect
import uuid
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
    OPERATIONAL_IDLE_PROGRESSING_V1,
    OPERATIONAL_IDLE_STARVATION_V1,
    RETRIEVAL_OMISSION_INDEX_EMPTY_V1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
    GP085_RET01_GATE_ID_V1,
    compute_retrieval_density_metrics_v1,
    get_latest_retrieval_materialization_report_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import (
    CortexRetrievalIndexEpoch,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE085_RETRIEVAL_STARVATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_RETRIEVAL_STARVATION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-retrieval-density-doctrine.md"
)

GP085_RET02_GATE_ID_V1: Final[str] = "G-P085-RET-02"

METRIC_INDEX_AGE_SECONDS_V1: Final[str] = "index_age_seconds"
METRIC_INDEX_STALE_V1: Final[str] = "index_stale"
METRIC_OPERATIONAL_STARVATION_V1: Final[str] = "operational_starvation"

STARVATION_REASON_TCRE_COMPLETED_V1: Final[str] = "tcre_completed_indexed_zero"
STARVATION_REASON_WALKS_COMPLETED_V1: Final[str] = "walks_completed_indexed_zero"
STARVATION_REASON_ELIGIBLE_UNINDEXED_V1: Final[str] = "eligible_artifacts_unindexed"

_PANEL_REQUIRED_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "gate_id",
        "tenant_id",
        "idle_class",
        "operational_starvation",
        "index_freshness",
        "starvation_reasons",
        "eligibility_explanation",
        "density_snapshot",
    }
)


class SubstrateRetrievalStarvationError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_index_stale_threshold_seconds_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(60, int(get_settings().cortex_retrieval_index_stale_seconds))
    except Exception:  # noqa: BLE001
        return 3600


def count_tcre_completed_jobs_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
        )
        or 0
    )


def count_completed_walks_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
        _count_completed_walks_v1,
    )

    return _count_completed_walks_v1(session, tenant_id=tenant_id)


def get_published_index_epoch_row_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexRetrievalIndexEpoch | None:
    return session.scalar(
        select(CortexRetrievalIndexEpoch)
        .where(
            CortexRetrievalIndexEpoch.tenant_id == tenant_id,
            CortexRetrievalIndexEpoch.build_state == "PUBLISHED",
        )
        .order_by(CortexRetrievalIndexEpoch.published_at.desc())
        .limit(1)
    )


def compute_index_freshness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """``index_age_seconds = now - published_at``; stale when > ``T_index_stale``."""
    row = get_published_index_epoch_row_v1(session, tenant_id=tenant_id)
    threshold = get_retrieval_index_stale_threshold_seconds_v1()
    if row is None or row.published_at is None:
        return {
            METRIC_INDEX_AGE_SECONDS_V1: None,
            METRIC_INDEX_STALE_V1: False,
            "index_stale_threshold_seconds": threshold,
            "published_index_epoch": None,
            "published_at": None,
            "entry_count": 0,
        }
    age_seconds = max(0.0, (datetime.now(tz=UTC) - row.published_at).total_seconds())
    entry_count = int(row.entry_count or 0)
    return {
        METRIC_INDEX_AGE_SECONDS_V1: round(age_seconds, 2),
        METRIC_INDEX_STALE_V1: age_seconds > float(threshold),
        "index_stale_threshold_seconds": threshold,
        "published_index_epoch": str(row.index_epoch),
        "published_at": row.published_at.isoformat(),
        "entry_count": entry_count,
    }


def _upstream_work_present_v1(session: Session, *, tenant_id: uuid.UUID) -> bool:
    from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
        upstream_work_exists_v1,
    )
    from vector.domains.cortex.completeness.tcre_completeness_projection import (
        project_tcre_completeness_v1,
    )
    from vector.domains.cortex.completeness.graph_completeness_projection import (
        project_graph_completeness_v1,
    )

    tcre_stage = project_tcre_completeness_v1(session, tenant_id=tenant_id)
    graph_stage = project_graph_completeness_v1(session, tenant_id=tenant_id)
    return upstream_work_exists_v1({"tcre": tcre_stage, "graph": graph_stage})


def classify_retrieval_idle_class_v1(
    *,
    eligible: int,
    indexed: int,
    tcre_completed: int,
    walks_completed: int,
    upstream_work_present: bool,
) -> str:
    """Starvation vs healthy_idle classification (**G-P085-RET-02**)."""
    if indexed == 0 and (tcre_completed > 0 or walks_completed > 0):
        return OPERATIONAL_IDLE_STARVATION_V1
    if eligible > 0 and indexed == 0:
        return OPERATIONAL_IDLE_STARVATION_V1
    if eligible == 0 and not upstream_work_present:
        return OPERATIONAL_IDLE_HEALTHY_IDLE_V1
    return OPERATIONAL_IDLE_PROGRESSING_V1


def build_retrieval_starvation_reasons_v1(
    *,
    eligible: int,
    indexed: int,
    tcre_completed: int,
    walks_completed: int,
    index_freshness: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if tcre_completed > 0 and indexed == 0:
        reasons.append(STARVATION_REASON_TCRE_COMPLETED_V1)
    if walks_completed > 0 and indexed == 0:
        reasons.append(STARVATION_REASON_WALKS_COMPLETED_V1)
    if eligible > 0 and indexed == 0:
        reasons.append(STARVATION_REASON_ELIGIBLE_UNINDEXED_V1)
    if index_freshness.get(METRIC_INDEX_STALE_V1):
        reasons.append("index_stale")
    if index_freshness.get("entry_count") == 0 and index_freshness.get("published_index_epoch"):
        reasons.append(RETRIEVAL_OMISSION_INDEX_EMPTY_V1)
    return reasons


def explain_retrieval_eligibility_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Structured retrieval eligibility / starvation explain API (**G-P085-RET-02**)."""
    eval_out = evaluate_retrieval_starvation_v1(session, tenant_id=tenant_id)
    density = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])

    blocked_by: list[str] = []
    upstream_missing: list[str] = []
    next_required_step: str | None = None

    if eval_out["operational_starvation"]:
        blocked_by.append("retrieval_operational_starvation")
        if STARVATION_REASON_TCRE_COMPLETED_V1 in eval_out["starvation_reasons"]:
            upstream_missing.append("retrieval_index_materialization")
            next_required_step = "run_phase_07_retrieval_materialization"
        elif STARVATION_REASON_WALKS_COMPLETED_V1 in eval_out["starvation_reasons"]:
            upstream_missing.append("walk_index_binding")
            next_required_step = "materialize_walk_retrieval_bindings"
        else:
            next_required_step = "rebuild_retrieval_index"

    freshness = dict(eval_out["index_freshness"])
    if freshness.get(METRIC_INDEX_STALE_V1):
        blocked_by.append("retrieval_index_stale")
        next_required_step = next_required_step or "publish_fresh_retrieval_epoch"

    if freshness.get("entry_count") == 0 and freshness.get("published_index_epoch"):
        blocked_by.append("published_epoch_empty")
        upstream_missing.append("non_empty_index_entries")

    if eval_out["idle_class"] == OPERATIONAL_IDLE_HEALTHY_IDLE_V1:
        next_required_step = "await_upstream_ingestion_or_ingest_data"

    ret_skip_histogram: dict[str, int] = {}
    latest_report = get_latest_retrieval_materialization_report_v1(session, tenant_id=tenant_id)
    if latest_report is not None:
        for skip in list(latest_report.skip_reasons_json or []):
            if isinstance(skip, dict) and skip.get("ret_skip_code"):
                code = str(skip["ret_skip_code"])
                ret_skip_histogram[code] = ret_skip_histogram.get(code, 0) + 1

    retrieval_ready = (
        not eval_out["operational_starvation"]
        and int(dm.get("retrieval_indexed_count") or 0) > 0
        and not freshness.get(METRIC_INDEX_STALE_V1)
    )

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_RET02_GATE_ID_V1,
        "eligible_artifact_count": int(dm.get("retrieval_eligible_artifact_count") or 0),
        "indexed_count": int(dm.get("retrieval_indexed_count") or 0),
        "retrieval_ready": retrieval_ready,
        "operational_starvation": bool(eval_out["operational_starvation"]),
        "idle_class": eval_out["idle_class"],
        "blocked_by": blocked_by,
        "upstream_missing": upstream_missing,
        "starvation_reasons": list(eval_out["starvation_reasons"]),
        "ret_skip_histogram": ret_skip_histogram,
        "index_freshness": freshness,
        "latest_materialization_report_id": density.get("latest_materialization_report_id"),
        "next_required_step": next_required_step,
    }


def evaluate_retrieval_starvation_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Evaluate tenant retrieval starvation + index freshness (**G-P085-RET-02**)."""
    density = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    eligible = int(dm.get("retrieval_eligible_artifact_count") or 0)
    indexed = int(dm.get("retrieval_indexed_count") or 0)
    tcre_completed = count_tcre_completed_jobs_v1(session, tenant_id=tenant_id)
    walks_completed = count_completed_walks_v1(session, tenant_id=tenant_id)
    upstream_work = _upstream_work_present_v1(session, tenant_id=tenant_id)

    index_freshness = compute_index_freshness_v1(session, tenant_id=tenant_id)
    idle_class = classify_retrieval_idle_class_v1(
        eligible=eligible,
        indexed=indexed,
        tcre_completed=tcre_completed,
        walks_completed=walks_completed,
        upstream_work_present=upstream_work,
    )
    starvation_reasons = build_retrieval_starvation_reasons_v1(
        eligible=eligible,
        indexed=indexed,
        tcre_completed=tcre_completed,
        walks_completed=walks_completed,
        index_freshness=index_freshness,
    )
    operational_starvation = idle_class == OPERATIONAL_IDLE_STARVATION_V1

    substrate_state = str(density["substrate_state"])
    if operational_starvation or index_freshness.get(METRIC_INDEX_STALE_V1):
        substrate_state = "degraded"

    return {
        "gate_id": GP085_RET02_GATE_ID_V1,
        "related_gate_id": GP085_RET01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "idle_class": idle_class,
        METRIC_OPERATIONAL_STARVATION_V1: operational_starvation,
        "operational_starvation": operational_starvation,
        "substrate_state": substrate_state,
        "tcre_completed": tcre_completed,
        "walks_completed": walks_completed,
        "eligible_artifact_count": eligible,
        "indexed_count": indexed,
        "upstream_work_present": upstream_work,
        "healthy_idle": idle_class == OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
        "starvation_reasons": starvation_reasons,
        "index_freshness": index_freshness,
    }


def merge_retrieval_starvation_into_completeness_v1(
    *,
    omission_classes: dict[str, int],
    metrics: dict[str, Any],
    substrate_state: str,
    starvation_eval: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, Any], str]:
    """Apply **G-P085-RET-02** to retrieval completeness envelope."""
    omissions = dict(omission_classes)
    out_metrics = dict(metrics)
    state = substrate_state

    if starvation_eval.get("operational_starvation"):
        out_metrics[METRIC_OPERATIONAL_STARVATION_V1] = True
        state = "degraded"
    else:
        out_metrics[METRIC_OPERATIONAL_STARVATION_V1] = False

    freshness = dict(starvation_eval.get("index_freshness") or {})
    if freshness.get("entry_count") == 0 and freshness.get("published_index_epoch"):
        omissions[RETRIEVAL_OMISSION_INDEX_EMPTY_V1] = 1
        state = "degraded"
    if freshness.get(METRIC_INDEX_STALE_V1):
        omissions["retrieval_index_stale"] = 1
        state = "degraded"

    out_metrics["retrieval_idle_class"] = starvation_eval.get("idle_class")
    out_metrics[METRIC_INDEX_AGE_SECONDS_V1] = freshness.get(METRIC_INDEX_AGE_SECONDS_V1)
    out_metrics[METRIC_INDEX_STALE_V1] = bool(freshness.get(METRIC_INDEX_STALE_V1))
    out_metrics["index_stale_threshold_seconds"] = freshness.get("index_stale_threshold_seconds")
    out_metrics["healthy_idle"] = bool(starvation_eval.get("healthy_idle"))

    return omissions, out_metrics, state


def build_retrieval_starvation_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator starvation + freshness panel (**G-P085-RET-02**)."""
    starvation_eval = evaluate_retrieval_starvation_v1(session, tenant_id=tenant_id)
    eligibility = explain_retrieval_eligibility_v1(session, tenant_id=tenant_id)
    density = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)

    ret_skip_hist = dict(eligibility.get("ret_skip_histogram") or {})
    skip_top = Counter(ret_skip_hist).most_common(8)

    return {
        "gate_id": GP085_RET02_GATE_ID_V1,
        "related_gate_id": GP085_RET01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "computed_at_utc": datetime.now(tz=UTC).isoformat(),
        "idle_class": starvation_eval["idle_class"],
        "operational_starvation": starvation_eval["operational_starvation"],
        "substrate_state": starvation_eval["substrate_state"],
        "index_freshness": starvation_eval["index_freshness"],
        "starvation_reasons": starvation_eval["starvation_reasons"],
        "eligibility_explanation": eligibility,
        "density_snapshot": density,
        "ret_skip_top": [{"ret_skip_code": code, "count": count} for code, count in skip_top],
        "detail_route": (
            f"/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-starvation"
        ),
    }


def build_substrate_retrieval_starvation_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_retrieval_starvation_runtime_schema_version": int(
            PHASE085_RETRIEVAL_STARVATION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_RETRIEVAL_STARVATION_SPEC_REF_V1,
        "primary_gate_id": GP085_RET02_GATE_ID_V1,
        "starvation_classifications": [
            {
                "condition": "tcre_completed > 0 AND indexed = 0",
                "idle_class": OPERATIONAL_IDLE_STARVATION_V1,
            },
            {
                "condition": "walks_completed > 0 AND indexed = 0",
                "idle_class": OPERATIONAL_IDLE_STARVATION_V1,
            },
            {
                "condition": "eligible = 0 AND no upstream",
                "idle_class": OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
            },
            {
                "condition": "published epoch entry_count = 0",
                "omission": RETRIEVAL_OMISSION_INDEX_EMPTY_V1,
            },
        ],
        "index_freshness_law": "degrade when index_age_seconds > T_index_stale",
        "index_stale_threshold_seconds": get_retrieval_index_stale_threshold_seconds_v1(),
        "panel_entrypoint": "build_retrieval_starvation_panel_v1",
        "eligibility_entrypoint": "explain_retrieval_eligibility_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_retrieval_starvation"
        ),
    }


def verify_gp085_ret02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_retrieval_starvation_catalog_v1()
    if cat["primary_gate_id"] != GP085_RET02_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    if (
        classify_retrieval_idle_class_v1(
            eligible=0,
            indexed=0,
            tcre_completed=2,
            walks_completed=0,
            upstream_work_present=True,
        )
        != OPERATIONAL_IDLE_STARVATION_V1
    ):
        errors.append("tcre_completed_starvation")
    if (
        classify_retrieval_idle_class_v1(
            eligible=0,
            indexed=0,
            tcre_completed=0,
            walks_completed=3,
            upstream_work_present=True,
        )
        != OPERATIONAL_IDLE_STARVATION_V1
    ):
        errors.append("walks_completed_starvation")
    if (
        classify_retrieval_idle_class_v1(
            eligible=0,
            indexed=0,
            tcre_completed=0,
            walks_completed=0,
            upstream_work_present=False,
        )
        != OPERATIONAL_IDLE_HEALTHY_IDLE_V1
    ):
        errors.append("healthy_idle")

    panel_src = inspect.getsource(build_retrieval_starvation_panel_v1)
    for key in _PANEL_REQUIRED_KEYS_V1:
        if key not in panel_src:
            errors.append(f"panel_missing_key:{key}")

    from vector.domains.cortex.operational_runtime import retrieval_completeness_propagation as rcp

    rcp_src = inspect.getsource(rcp.propagate_retrieval_completeness_stage_v1)
    if "evaluate_retrieval_starvation_v1" not in rcp_src:
        errors.append("propagation_missing_starvation_eval")
    if "merge_retrieval_starvation_into_completeness_v1" not in rcp_src:
        errors.append("propagation_missing_starvation_merge")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "build_retrieval_starvation_panel_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_starvation_panel")

    try:
        from vector.settings import get_settings

        if get_settings().cortex_retrieval_index_stale_seconds < 60:
            errors.append("index_stale_threshold_too_low")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"settings:{exc}")

    passed = not errors
    return {
        "id": GP085_RET02_GATE_ID_V1,
        "name": "cesp_substrate_retrieval_starvation",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
