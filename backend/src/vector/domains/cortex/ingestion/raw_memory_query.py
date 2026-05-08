"""Phase 02 Step 5 — raw memory query model + anti-goal enforcement."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_temporal import (
    latest_known_before_t,
    list_revision_chain,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex

RawMemoryQueryMode = Literal["source", "replay", "audit", "provenance", "temporal"]
TemporalSubmode = Literal["as_of_t", "latest_before_t", "revision_chain"]

_ALLOWED_INTENTS = {
    "evidence_retrieval",
    "lineage_retrieval",
    "temporal_retrieval",
    "replay_diagnostics",
    "audit_retrieval",
}
_BLOCKED_INTENT_TERMS = {
    "semantic",
    "topic",
    "graph",
    "intelligence",
    "causal",
    "ownership",
    "inference",
    "infer",
    "reasoning",
    "cluster",
}


def enforce_raw_memory_query_anti_goals(*, intent: str | None, query_text: str | None) -> None:
    intent_norm = (intent or "evidence_retrieval").strip().lower()
    text_norm = (query_text or "").strip().lower()
    if intent_norm not in _ALLOWED_INTENTS:
        raise ValueError(
            "Unsupported query intent for Phase 02 raw memory. "
            "Only evidence/lineage/temporal/replay/audit retrieval intents are allowed."
        )
    if any(term in intent_norm for term in _BLOCKED_INTENT_TERMS) or any(
        term in text_norm for term in _BLOCKED_INTENT_TERMS
    ):
        raise ValueError(
            "Semantic/graph/intelligence query intents are out of scope for Phase 02 raw memory."
        )


def _serialize_raw_row(row: RawIngestionRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "resource_type": row.resource_type,
        "external_id": row.external_id,
        "api_endpoint": row.api_endpoint,
        "query_params": dict(row.query_params) if isinstance(row.query_params, dict) else {},
        "payload_body": dict(row.payload_body) if isinstance(row.payload_body, dict) else {},
        "http_status": row.http_status,
        "fetched_at": row.fetched_at,
        "idempotency_key": row.idempotency_key,
        "source_identity_key": row.source_identity_key,
        "source_revision_key": row.source_revision_key,
        "replay_job_id": row.replay_job_id,
        "replay_version": row.replay_version,
    }


def execute_raw_memory_query(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    mode: RawMemoryQueryMode,
    intent: str | None = None,
    query_text: str | None = None,
    connector: str | None = None,
    resource_type: str | None = None,
    source_identity_key: str | None = None,
    source_revision_key: str | None = None,
    replay_job_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    provenance_chain_id: str | None = None,
    fetched_after: datetime | None = None,
    fetched_before: datetime | None = None,
    temporal_submode: TemporalSubmode = "revision_chain",
    as_of: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    enforce_raw_memory_query_anti_goals(intent=intent, query_text=query_text)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    filters = [RawIngestionRecord.tenant_id == tenant_id]
    if connector and connector.strip():
        filters.append(RawIngestionRecord.connector == connector.strip())
    if resource_type and resource_type.strip():
        filters.append(RawIngestionRecord.resource_type == resource_type.strip())
    if fetched_after is not None:
        filters.append(RawIngestionRecord.fetched_at >= fetched_after)
    if fetched_before is not None:
        filters.append(RawIngestionRecord.fetched_at <= fetched_before)

    rows: list[RawIngestionRecord] = []
    if mode == "source":
        if not source_identity_key or not source_identity_key.strip():
            raise ValueError("source mode requires source_identity_key")
        filters.append(RawIngestionRecord.source_identity_key == source_identity_key.strip())
        if source_revision_key and source_revision_key.strip():
            filters.append(RawIngestionRecord.source_revision_key == source_revision_key.strip())
        stmt = (
            select(RawIngestionRecord)
            .where(*filters)
            .order_by(RawIngestionRecord.fetched_at.desc(), RawIngestionRecord.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        rows = list(session.scalars(stmt).all())
    elif mode == "replay":
        if replay_job_id is None:
            raise ValueError("replay mode requires replay_job_id")
        filters.append(RawIngestionRecord.replay_job_id == replay_job_id)
        stmt = (
            select(RawIngestionRecord)
            .where(*filters)
            .order_by(RawIngestionRecord.replay_sequence.asc(), RawIngestionRecord.id.asc())
            .offset(offset)
            .limit(limit + 1)
        )
        rows = list(session.scalars(stmt).all())
    elif mode == "audit":
        if run_id is None and replay_job_id is None:
            raise ValueError("audit mode requires run_id or replay_job_id")
        if run_id is not None:
            filters.append(RawIngestionRecord.run_id == run_id)
        if replay_job_id is not None:
            filters.append(RawIngestionRecord.replay_job_id == replay_job_id)
        stmt = (
            select(RawIngestionRecord)
            .where(and_(*filters))
            .order_by(RawIngestionRecord.fetched_at.asc(), RawIngestionRecord.id.asc())
            .offset(offset)
            .limit(limit + 1)
        )
        rows = list(session.scalars(stmt).all())
    elif mode == "provenance":
        if provenance_chain_id and provenance_chain_id.strip():
            li = session.scalar(
                select(RawMemoryLineageIndex).where(
                    RawMemoryLineageIndex.tenant_id == tenant_id,
                    RawMemoryLineageIndex.provenance_chain_id == provenance_chain_id.strip(),
                )
            )
            if li is None:
                rows = []
            else:
                filters.extend(
                    [
                        RawIngestionRecord.connection_id == li.connection_id,
                        RawIngestionRecord.connector == li.connector,
                        RawIngestionRecord.resource_type == li.resource_type,
                        RawIngestionRecord.source_identity_key == li.source_identity_key,
                    ]
                )
                stmt = (
                    select(RawIngestionRecord)
                    .where(*filters)
                    .order_by(RawIngestionRecord.fetched_at.asc(), RawIngestionRecord.id.asc())
                    .offset(offset)
                    .limit(limit + 1)
                )
                rows = list(session.scalars(stmt).all())
        else:
            if not source_identity_key or not source_identity_key.strip():
                raise ValueError("provenance mode requires provenance_chain_id or source_identity_key")
            filters.append(RawIngestionRecord.source_identity_key == source_identity_key.strip())
            stmt = (
                select(RawIngestionRecord)
                .where(*filters)
                .order_by(RawIngestionRecord.fetched_at.asc(), RawIngestionRecord.id.asc())
                .offset(offset)
                .limit(limit + 1)
            )
            rows = list(session.scalars(stmt).all())
    elif mode == "temporal":
        if not source_identity_key or not source_identity_key.strip():
            raise ValueError("temporal mode requires source_identity_key")
        if not connector or not connector.strip() or not resource_type or not resource_type.strip():
            raise ValueError("temporal mode requires connector and resource_type")
        # connection scope for temporal helpers: use newest matching row's connection.
        base = session.scalar(
            select(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.connector == connector.strip(),
                RawIngestionRecord.resource_type == resource_type.strip(),
                RawIngestionRecord.source_identity_key == source_identity_key.strip(),
            )
            .order_by(RawIngestionRecord.fetched_at.desc(), RawIngestionRecord.id.desc())
            .limit(1)
        )
        if base is None:
            rows = []
        elif temporal_submode == "revision_chain":
            chain = list_revision_chain(
                session,
                tenant_id=tenant_id,
                connection_id=base.connection_id,
                connector=connector.strip(),
                resource_type=resource_type.strip(),
                source_identity_key=source_identity_key.strip(),
            )
            raw_ids = [x.raw_id for x in chain]
            if not raw_ids:
                rows = []
            else:
                stmt = (
                    select(RawIngestionRecord)
                    .where(
                        RawIngestionRecord.tenant_id == tenant_id,
                        RawIngestionRecord.id.in_(raw_ids),
                    )
                    .order_by(RawIngestionRecord.fetched_at.asc(), RawIngestionRecord.id.asc())
                    .offset(offset)
                    .limit(limit + 1)
                )
                rows = list(session.scalars(stmt).all())
        else:
            if as_of is None:
                raise ValueError("temporal as_of_t/latest_before_t mode requires as_of")
            latest = latest_known_before_t(
                session,
                tenant_id=tenant_id,
                connection_id=base.connection_id,
                connector=connector.strip(),
                resource_type=resource_type.strip(),
                source_identity_key=source_identity_key.strip(),
                as_of=as_of,
            )
            if latest is None:
                rows = []
            else:
                row = session.scalar(
                    select(RawIngestionRecord).where(
                        RawIngestionRecord.tenant_id == tenant_id,
                        RawIngestionRecord.id == latest.raw_id,
                    )
                )
                rows = [row] if row is not None else []
    else:
        raise ValueError(f"unsupported mode: {mode}")

    truncated = len(rows) > limit
    if truncated:
        rows = rows[:limit]
    return {
        "mode": mode,
        "items": [_serialize_raw_row(r) for r in rows],
        "total_count": len(rows) + (1 if truncated else 0),
        "offset": offset,
        "limit": limit,
        "truncated": truncated,
    }


def verify_phase02_step5_query_model(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # Anti-goal guard must fail closed for semantic/graph intent.
    anti_goal_passed = False
    try:
        execute_raw_memory_query(
            session,
            tenant_id=tenant_id,
            mode="source",
            source_identity_key="dummy",
            intent="semantic_search",
        )
    except ValueError:
        anti_goal_passed = True
    checks.append(
        {
            "id": "s5_anti_goal_semantic_graph_blocked",
            "passed": anti_goal_passed,
            "detail": "semantic/graph intents rejected",
        }
    )

    # Deterministic supported query classes (when scope exists).
    classes_passed = True
    sample = session.scalar(
        select(RawIngestionRecord)
        .where(RawIngestionRecord.tenant_id == tenant_id)
        .order_by(RawIngestionRecord.fetched_at.desc(), RawIngestionRecord.id.desc())
        .limit(1)
    )
    if sample is None:
        checks.append(
            {
                "id": "s5_supported_query_modes_deterministic",
                "passed": True,
                "detail": "No raw rows yet; query mode determinism unverifiable.",
            }
        )
    else:
        modes: list[dict[str, Any]] = [
            {
                "mode": "source",
                "kwargs": {
                    "source_identity_key": sample.source_identity_key,
                    "connector": sample.connector,
                    "resource_type": sample.resource_type,
                },
            },
            {
                "mode": "audit",
                "kwargs": {"run_id": sample.run_id},
            },
            {
                "mode": "provenance",
                "kwargs": {
                    "source_identity_key": sample.source_identity_key,
                    "connector": sample.connector,
                    "resource_type": sample.resource_type,
                },
            },
            {
                "mode": "temporal",
                "kwargs": {
                    "connector": sample.connector,
                    "resource_type": sample.resource_type,
                    "source_identity_key": sample.source_identity_key,
                    "temporal_submode": "revision_chain",
                },
            },
        ]
        if sample.replay_job_id is not None:
            modes.append(
                {
                    "mode": "replay",
                    "kwargs": {"replay_job_id": sample.replay_job_id, "connector": sample.connector},
                }
            )
        mode_results: list[dict[str, Any]] = []
        for m in modes:
            out1 = execute_raw_memory_query(
                session,
                tenant_id=tenant_id,
                mode=m["mode"],
                intent="evidence_retrieval",
                **m["kwargs"],
            )
            out2 = execute_raw_memory_query(
                session,
                tenant_id=tenant_id,
                mode=m["mode"],
                intent="evidence_retrieval",
                **m["kwargs"],
            )
            ids1 = [x["id"] for x in out1["items"]]
            ids2 = [x["id"] for x in out2["items"]]
            passed = ids1 == ids2
            if not passed:
                classes_passed = False
            mode_results.append({"mode": m["mode"], "passed": passed, "result_size": len(ids1)})
        checks.append(
            {
                "id": "s5_supported_query_modes_deterministic",
                "passed": classes_passed,
                "detail": mode_results,
            }
        )

    passed = all(c["passed"] for c in checks)
    return {
        "passed": passed,
        "state": "healthy" if passed else "degraded",
        "checks": checks,
    }
