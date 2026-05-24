"""S5.5 — execution reality inspection surfaces (Pipeline → Semantic readiness)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_execution_transition_log import CortexExecutionTransitionLog
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

EXECUTION_REALITY_INSPECTION_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_25: Final[str] = "wave_s5_execution_reality_inspection"
EXECUTION_THREAD_SAMPLE_LIMIT: Final[int] = 8


def _sample_execution_thread_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = EXECUTION_THREAD_SAMPLE_LIMIT,
) -> dict[str, Any]:
    lim = max(1, min(int(limit), 25))
    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(CortexTcreReconstructionJob.tenant_id == tenant_id)
            .order_by(CortexTcreReconstructionJob.created_at.desc())
            .limit(lim)
        ).all()
    )
    transitions = list(
        session.scalars(
            select(CortexExecutionTransitionLog)
            .where(CortexExecutionTransitionLog.tenant_id == tenant_id)
            .order_by(CortexExecutionTransitionLog.created_at.desc())
            .limit(lim)
        ).all()
    )
    return {
        "status": "sample",
        "sample_limit": lim,
        "primary_surface": "pipeline_semantic_readiness",
        "tcre_jobs": [
            {
                "job_id": str(row.id),
                "job_kind": row.job_kind,
                "status": row.status,
                "scope_json": dict(row.scope_json or {}),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in jobs
        ],
        "recent_transitions": [
            {
                "from_state": row.from_state,
                "to_state": row.to_state,
                "trigger": row.trigger,
                "gate_result": row.gate_result,
                "pipeline_run_id": str(row.pipeline_run_id) if row.pipeline_run_id else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in transitions
        ],
    }


def build_execution_reality_inspection_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    semantic_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Four inspection surfaces consolidated under semantic readiness."""
    if semantic_payload is None:
        from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
            build_semantic_readiness_v1,
        )

        core = build_semantic_readiness_v1(session, tenant_id=tenant_id)
    else:
        core = semantic_payload
    graph = dict(core.get("graph_truth") or {})
    identity = dict(core.get("identity_continuity") or {})
    retrieval = dict(core.get("retrieval") or {})

    return {
        "surface_kind": "execution_reality_inspection",
        "schema_version": EXECUTION_REALITY_INSPECTION_SCHEMA_VERSION,
        "step": WAVE_S5_STEP_25,
        "tenant_id": str(tenant_id),
        "identity_continuity": {
            "distinct_candidate_pairs": identity.get("distinct_candidate_pairs"),
            "candidate_rows": identity.get("candidate_rows"),
            "candidate_inflation_ratio": identity.get("candidate_inflation_ratio"),
            "candidate_inflation_severity": identity.get("candidate_inflation_severity"),
            "anchors_missing_org_entity_pct": identity.get("anchors_missing_org_entity_pct"),
            "promotable_by_rule_id": identity.get("promotable_by_rule_id") or [],
            "promotion_rule_count_green_min": identity.get("promotion_rule_count_green_min"),
        },
        "execution_thread": _sample_execution_thread_v1(session, tenant_id=tenant_id),
        "retrieval_mix": {
            "published_index_epoch": retrieval.get("published_index_epoch"),
            "entry_count": retrieval.get("entry_count"),
            "index_kind_counts": retrieval.get("index_kind_counts") or [],
            "org_link_pct": retrieval.get("org_link_pct"),
            "execution_index_pct": retrieval.get("execution_index_pct"),
            "org_link_pct_severity": retrieval.get("org_link_pct_severity"),
            "execution_index_pct_severity": retrieval.get("execution_index_pct_severity"),
        },
        "graph_truth": {
            "unique_auth_pairs": graph.get("unique_auth_pairs"),
            "dup_factor": graph.get("dup_factor"),
            "dup_factor_severity": graph.get("dup_factor_severity"),
            "entities_in_auth_graph_pct": graph.get("entities_in_auth_graph_pct"),
            "entities_isolated": graph.get("entities_isolated"),
            "promotion_rule_count": graph.get("promotion_rule_count"),
            "promotions_by_rule_id": graph.get("promotions_by_rule_id") or [],
        },
    }
