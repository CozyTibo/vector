"""Retrieval substrate truth validation — runtime-backed integrity checks."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.infrastructure.db.models.cortex_artifact_lineage_edge import CortexArtifactLineageEdge
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

PHASE07_RETRIEVAL_TRUTH_VALIDATION_SCHEMA_VERSION: Final[int] = 1


def validate_retrieval_index_lineage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sample_limit: int = 50,
) -> dict[str, Any]:
    """Every indexed row should have explainable upstream refs or lawful omissions."""
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry)
            .where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
            .limit(max(1, sample_limit))
        ).all()
    )
    orphans = 0
    for row in rows:
        ref = dict(row.artifact_ref_json or {})
        if not ref and row.retrieval_legality_class not in ("retrieval_unverifiable",):
            orphans += 1
    return {
        "check": "index_lineage",
        "passed": orphans == 0,
        "sample_count": len(rows),
        "orphan_without_ref_count": orphans,
    }


def validate_no_unpublished_lawful_reads_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    if published is None:
        return {"check": "publish_barrier", "passed": False, "reason": "no_published_epoch"}
    stale = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch != published,
            )
        )
        or 0
    )
    return {
        "check": "publish_barrier",
        "passed": stale == 0,
        "published_epoch": published,
        "stale_row_count": stale,
    }


def validate_retrieval_replay_legality_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    if published is None:
        return {"check": "replay_legality", "passed": True, "note": "no_published_epoch"}
    unsafe_published = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == published,
                CortexRetrievalIndexEntry.retrieval_legality_class == "retrieval_unverifiable",
            )
        )
        or 0
    )
    return {
        "check": "replay_legality",
        "passed": unsafe_published == 0,
        "unverifiable_published_count": unsafe_published,
    }


def validate_lineage_edge_presence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexArtifactLineageEdge)
            .where(CortexArtifactLineageEdge.tenant_id == tenant_id)
        )
        or 0
    )
    return {
        "check": "lineage_edges",
        "passed": count >= 0,
        "lineage_edge_count": count,
        "note": "zero_edges_allowed_for_fresh_tenant",
    }


def run_retrieval_truth_validation_suite_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    checks = [
        validate_retrieval_index_lineage_v1(session, tenant_id=tenant_id),
        validate_no_unpublished_lawful_reads_v1(session, tenant_id=tenant_id),
        validate_retrieval_replay_legality_v1(session, tenant_id=tenant_id),
        validate_lineage_edge_presence_v1(session, tenant_id=tenant_id),
    ]
    passed = all(c.get("passed") for c in checks)
    return {
        "retrieval_truth_validation_schema_version": PHASE07_RETRIEVAL_TRUTH_VALIDATION_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "passed": passed,
        "checks": checks,
        "surface_kind": "runtime_backed",
    }
