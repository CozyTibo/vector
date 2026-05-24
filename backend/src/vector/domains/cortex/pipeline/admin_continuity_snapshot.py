"""Materialized admin continuity snapshot writer/reader (R1)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.org_ambiguity import count_open_org_ambiguity_records
from vector.domains.cortex.operational_runtime.graph_density import (
    count_active_org_entities_v1,
    count_entities_with_promoted_edges_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)
from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
    snapshot_authoritative_link_topology_v1,
    snapshot_promotion_diversity_observability_v1,
)
from vector.infrastructure.db.models.cortex_admin_continuity_snapshot import CortexAdminContinuitySnapshot
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.tenant import Tenant

_LOGGER = logging.getLogger("app")

ADMIN_CONTINUITY_SNAPSHOT_SCHEMA_VERSION: Final[int] = 1

_SNAPSHOT_TRIGGER_PHASES: Final[frozenset[str]] = frozenset(
    {
        PHASE_03_IDENTITY,
        PHASE_04_GRAPH,
        PHASE_05_TRAVERSAL,
        PHASE_06_TCRE,
        PHASE_07_RETRIEVAL,
        PHASE_08_SYNTHESIS,
    }
)


def phase_triggers_admin_snapshot_refresh_v1(phase_id: str) -> bool:
    return phase_id in _SNAPSHOT_TRIGGER_PHASES


def build_admin_continuity_snapshot_payload_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Compute snapshot sections without connected-component scans."""
    entities_total = count_active_org_entities_v1(session, tenant_id=tenant_id)
    entities_in_graph = count_entities_with_promoted_edges_v1(session, tenant_id=tenant_id)
    isolated = max(0, entities_total - entities_in_graph)
    topo = snapshot_authoritative_link_topology_v1(session, tenant_id=tenant_id)
    try:
        promotion = snapshot_promotion_diversity_observability_v1(session, tenant_id=tenant_id)
    except Exception:
        _LOGGER.debug("promotion diversity snapshot failed tenant_id=%s", tenant_id, exc_info=True)
        promotion = {}
    slack_promotable = int((promotion.get("promotable_by_rule") or {}).get("slack_user_id") or 0)
    github_promotable = int((promotion.get("promotable_by_rule") or {}).get("github_login") or 0)
    graph_bits = [f"{entities_in_graph} entities in auth graph"]
    if isolated > 0:
        graph_bits.append(f"{isolated} isolated")
    if slack_promotable == 0 or github_promotable == 0:
        graph_bits.append("Slack/GitHub promotable slack")
    graph_summary = {
        "entities_total": entities_total,
        "entities_in_graph": entities_in_graph,
        "isolated_entity_count": isolated,
        "unique_auth_pairs": int(topo.get("unique_auth_pairs") or 0),
        "promotable_slack": slack_promotable,
        "promotable_github": github_promotable,
        "summary_text": "; ".join(graph_bits) + ".",
    }

    published_epoch = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    epoch_row = None
    if published_epoch:
        epoch_row = session.scalar(
            select(CortexRetrievalIndexEpoch)
            .where(
                CortexRetrievalIndexEpoch.tenant_id == tenant_id,
                CortexRetrievalIndexEpoch.index_epoch == published_epoch,
            )
            .limit(1)
        )
    retrieval_summary: dict[str, Any] = {
        "published_index_epoch": published_epoch,
        "build_state": epoch_row.build_state if epoch_row is not None else None,
        "published_at": epoch_row.published_at.isoformat() if epoch_row and epoch_row.published_at else None,
    }

    synthesis_failed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "failed",
            )
        )
        or 0
    )
    published_artifacts = int(
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
    synthesis_summary = {
        "failed_job_count": synthesis_failed,
        "published_artifact_count": published_artifacts,
    }

    open_ambiguities = count_open_org_ambiguity_records(session, tenant_id=tenant_id)
    identity_summary = {"open_ambiguity_count": open_ambiguities}

    return {
        "schema_version": ADMIN_CONTINUITY_SNAPSHOT_SCHEMA_VERSION,
        "graph_summary_json": graph_summary,
        "retrieval_summary_json": retrieval_summary,
        "synthesis_summary_json": synthesis_summary,
        "identity_summary_json": identity_summary,
    }


def upsert_admin_continuity_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
) -> CortexAdminContinuitySnapshot:
    now = datetime.now(UTC)
    row = session.get(CortexAdminContinuitySnapshot, tenant_id)
    if row is None:
        row = CortexAdminContinuitySnapshot(
            tenant_id=tenant_id,
            captured_at_utc=now,
            graph_summary_json=dict(payload.get("graph_summary_json") or {}),
            retrieval_summary_json=dict(payload.get("retrieval_summary_json") or {}),
            synthesis_summary_json=dict(payload.get("synthesis_summary_json") or {}),
            identity_summary_json=dict(payload.get("identity_summary_json") or {}),
            schema_version=int(payload.get("schema_version") or ADMIN_CONTINUITY_SNAPSHOT_SCHEMA_VERSION),
            updated_at=now,
        )
        session.add(row)
    else:
        row.captured_at_utc = now
        row.graph_summary_json = dict(payload.get("graph_summary_json") or {})
        row.retrieval_summary_json = dict(payload.get("retrieval_summary_json") or {})
        row.synthesis_summary_json = dict(payload.get("synthesis_summary_json") or {})
        row.identity_summary_json = dict(payload.get("identity_summary_json") or {})
        row.schema_version = int(payload.get("schema_version") or ADMIN_CONTINUITY_SNAPSHOT_SCHEMA_VERSION)
        row.updated_at = now
    session.flush()
    from vector.domains.cortex.pipeline.operator_admin_overview import (
        invalidate_operator_overview_cache_v1,
    )

    invalidate_operator_overview_cache_v1(tenant_id)
    return row


def refresh_admin_continuity_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    payload = build_admin_continuity_snapshot_payload_v1(session, tenant_id=tenant_id)
    row = upsert_admin_continuity_snapshot_v1(session, tenant_id=tenant_id, payload=payload)
    return {
        "surface_kind": "admin_continuity_snapshot_refresh",
        "tenant_id": str(tenant_id),
        "captured_at_utc": row.captured_at_utc.isoformat(),
        "schema_version": row.schema_version,
    }


def read_admin_continuity_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    row = session.get(CortexAdminContinuitySnapshot, tenant_id)
    if row is None:
        return {
            "available": False,
            "captured_at_utc": None,
            "graph_summary": None,
            "retrieval_summary": None,
            "synthesis_summary": None,
            "identity_summary": None,
        }
    return {
        "available": True,
        "captured_at_utc": row.captured_at_utc,
        "graph_summary": dict(row.graph_summary_json or {}),
        "retrieval_summary": dict(row.retrieval_summary_json or {}),
        "synthesis_summary": dict(row.synthesis_summary_json or {}),
        "identity_summary": dict(row.identity_summary_json or {}),
    }


def list_active_snapshot_tenant_ids_v1(session: Session, *, limit: int = 500) -> list[uuid.UUID]:
    rows = session.scalars(
        select(Tenant.id)
        .where(
            Tenant.status == "active",
            Tenant.workspace_access_enabled.is_(True),
        )
        .order_by(Tenant.updated_at.desc())
        .limit(max(1, min(limit, 5000)))
    ).all()
    return list(rows)


def enqueue_admin_continuity_snapshot_refresh_v1(tenant_id: uuid.UUID) -> None:
    try:
        from app.tasks.cortex_admin_snapshot import refresh_admin_continuity_snapshot_task

        refresh_admin_continuity_snapshot_task.delay(str(tenant_id))
    except Exception:
        _LOGGER.debug(
            "admin continuity snapshot enqueue skipped tenant_id=%s",
            tenant_id,
            exc_info=True,
        )


def notify_admin_snapshot_after_terminal_phase_v1(
    *,
    tenant_id: uuid.UUID,
    phase_id: str,
) -> None:
    if phase_triggers_admin_snapshot_refresh_v1(phase_id):
        enqueue_admin_continuity_snapshot_refresh_v1(tenant_id)
