"""Durable OCTS walk store — restart-safe replay identity (Phase 07)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.traversal.runtime.traversal_epoch_repository import derive_traversal_epoch_v1
from vector.domains.cortex.traversal.runtime.traversal_permutation_repository import (
    build_permutation_profile_v1,
)
from vector.domains.cortex.traversal.runtime.traversal_receipt_repository import persist_traversal_receipt_v1
from vector.domains.cortex.traversal.runtime.traversal_replay_archive import archive_completed_walk_v1
from vector.domains.cortex.traversal.walk_api_contract import (
    WalkApiRecordV1,
    WalkApiStatusV1,
    octs_walk_api_memory_store_v1,
    resolve_engine_build_ref_for_persist_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord


def extract_walk_replay_metadata_v1(
    *,
    request_body: dict[str, Any],
    walk_payload: dict[str, Any],
    replay_lineage: dict[str, Any] | None,
) -> dict[str, Any]:
    wr = walk_payload.get("walk_result") or {}
    hb = wr.get("hash_body") or {}
    walk_hash = str(wr.get("walk_result_hash") or "")
    receipt_body = {
        "walk_result_hash": walk_hash,
        "hash_body": hb,
        "hop_receipts": hb.get("hop_receipts") or [],
        "termination_reason": hb.get("termination_reason"),
    }
    receipt_digest = hash_reasoning_canonical_json_sha256_v1(receipt_body)
    engine_ref = str(
        (walk_payload.get("telemetry") or {}).get("engine_build_id")
        or resolve_engine_build_ref_for_persist_v1()
    )
    epoch = derive_traversal_epoch_v1(
        walk_policy=dict(request_body.get("walk_policy") or {}),
        temporal_anchor=request_body.get("temporal_anchor")
        if isinstance(request_body.get("temporal_anchor"), dict)
        else None,
        engine_build_ref=engine_ref,
    )
    replay_identity = hash_reasoning_canonical_json_sha256_v1(
        {
            "walk_hash": walk_hash,
            "traversal_epoch": epoch,
            "walk_policy_digest": hash_reasoning_canonical_json_sha256_v1(
                dict(request_body.get("walk_policy") or {})
            ),
        }
    )[:32]
    parent_walk_id = None
    if replay_lineage and replay_lineage.get("replay_of_walk_id"):
        parent_walk_id = uuid.UUID(str(replay_lineage["replay_of_walk_id"]))
    degradation: list[str] = []
    if hb.get("termination_reason") not in (None, "", "completed", "frontier_exhausted"):
        degradation.append(str(hb["termination_reason"]))
    return {
        "walk_hash": walk_hash,
        "traversal_receipt_digest": receipt_digest,
        "traversal_epoch": epoch,
        "replay_identity": replay_identity,
        "permutation_profile": build_permutation_profile_v1(
            walk_policy=dict(request_body.get("walk_policy") or {}),
            exploration_mode=bool(request_body.get("exploration_mode")),
        ),
        "continuity_proof_ref": str(hb.get("continuity_proof_ref") or ""),
        "frontier_boundaries": {
            "termination_reason": hb.get("termination_reason"),
            "frontier_size": len(hb.get("frontier_snapshot") or []),
        },
        "replay_legality_posture": "replay_safe" if not degradation else "degraded",
        "degradation_classes": degradation,
        "parent_walk_id": parent_walk_id,
        "engine_build_ref": engine_ref,
    }


class OctsWalkStoreProtocol(Protocol):
    def get(self, tenant_id: uuid.UUID, walk_id: uuid.UUID) -> WalkApiRecordV1 | None: ...

    def insert_completed_sync(
        self,
        *,
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        request_body: dict[str, Any],
        walk_payload: dict[str, Any],
        idempotency_key: str | None,
        replay_lineage: dict[str, Any] | None = None,
    ) -> WalkApiRecordV1: ...

    def insert_async_accepted(
        self,
        *,
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        job_id: str,
        request_body: dict[str, Any],
        idempotency_key: str | None,
    ) -> WalkApiRecordV1: ...

    def lookup_idempotency(self, tenant_id: uuid.UUID, key: str) -> uuid.UUID | None: ...

    def cancel(self, tenant_id: uuid.UUID, walk_id: uuid.UUID) -> WalkApiRecordV1 | None: ...

    def walk_queue_depth_for_tenant(self, tenant_id: uuid.UUID) -> int: ...

    def list_walk_records_for_tenant_v1(self, tenant_id: uuid.UUID) -> list[WalkApiRecordV1]: ...


class OctsWalkApiDurableStore:
    """Session-backed walk store — survives worker restart."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_record(self, row: CortexOctsDurableWalkRecord) -> WalkApiRecordV1:
        return WalkApiRecordV1(
            walk_id=row.walk_id,
            tenant_id=row.tenant_id,
            status=row.status,  # type: ignore[arg-type]
            request_body=dict(row.request_body or {}),
            walk_payload=dict(row.walk_payload) if row.walk_payload else None,
            job_id=row.job_id,
            idempotency_key=row.idempotency_key,
        )

    def get(self, tenant_id: uuid.UUID, walk_id: uuid.UUID) -> WalkApiRecordV1 | None:
        row = self._session.get(CortexOctsDurableWalkRecord, walk_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return self._to_record(row)

    def insert_completed_sync(
        self,
        *,
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        request_body: dict[str, Any],
        walk_payload: dict[str, Any],
        idempotency_key: str | None,
        replay_lineage: dict[str, Any] | None = None,
    ) -> WalkApiRecordV1:
        meta = extract_walk_replay_metadata_v1(
            request_body=request_body,
            walk_payload=walk_payload,
            replay_lineage=replay_lineage,
        )
        existing = self._session.get(CortexOctsDurableWalkRecord, walk_id)
        if existing is not None and existing.tenant_id == tenant_id:
            if existing.replay_identity and existing.replay_identity != meta["replay_identity"]:
                raise ValueError("replay_identity_mismatch")
            existing.status = "completed"
            existing.walk_payload = walk_payload
            existing.updated_at = datetime.now(tz=UTC)
            row = existing
        else:
            row = CortexOctsDurableWalkRecord(
                walk_id=walk_id,
                tenant_id=tenant_id,
                status="completed",
                request_body=request_body,
                walk_payload=walk_payload,
                idempotency_key=idempotency_key,
                walk_hash=meta["walk_hash"],
                traversal_receipt_digest=meta["traversal_receipt_digest"],
                traversal_epoch=meta["traversal_epoch"],
                replay_identity=meta["replay_identity"],
                permutation_profile=meta["permutation_profile"],
                continuity_proof_ref=meta["continuity_proof_ref"] or None,
                frontier_boundaries=meta["frontier_boundaries"],
                replay_legality_posture=meta["replay_legality_posture"],
                degradation_classes=meta["degradation_classes"],
                parent_walk_id=meta["parent_walk_id"],
                engine_build_ref=meta["engine_build_ref"],
            )
            self._session.add(row)
        self._session.flush()
        persist_traversal_receipt_v1(
            self._session,
            tenant_id=tenant_id,
            walk_id=walk_id,
            receipt_kind="walk_result",
            body={
                "walk_hash": meta["walk_hash"],
                "replay_identity": meta["replay_identity"],
            },
        )
        archive_completed_walk_v1(self._session, row=row)
        return self._to_record(row)

    def insert_async_accepted(
        self,
        *,
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        job_id: str,
        request_body: dict[str, Any],
        idempotency_key: str | None,
    ) -> WalkApiRecordV1:
        row = CortexOctsDurableWalkRecord(
            walk_id=walk_id,
            tenant_id=tenant_id,
            status="running",
            request_body=request_body,
            walk_payload=None,
            job_id=job_id,
            idempotency_key=idempotency_key,
            engine_build_ref=resolve_engine_build_ref_for_persist_v1(),
        )
        self._session.add(row)
        self._session.flush()
        return self._to_record(row)

    def lookup_idempotency(self, tenant_id: uuid.UUID, key: str) -> uuid.UUID | None:
        row = self._session.scalar(
            select(CortexOctsDurableWalkRecord).where(
                CortexOctsDurableWalkRecord.tenant_id == tenant_id,
                CortexOctsDurableWalkRecord.idempotency_key == key,
            )
        )
        return row.walk_id if row else None

    def cancel(self, tenant_id: uuid.UUID, walk_id: uuid.UUID) -> WalkApiRecordV1 | None:
        row = self._session.get(CortexOctsDurableWalkRecord, walk_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        if row.status in ("completed", "failed", "cancelled"):
            return self._to_record(row)
        row.status = "cancelled"
        row.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        return self._to_record(row)

    def walk_queue_depth_for_tenant(self, tenant_id: uuid.UUID) -> int:
        rows = self._session.scalars(
            select(CortexOctsDurableWalkRecord).where(
                CortexOctsDurableWalkRecord.tenant_id == tenant_id,
                CortexOctsDurableWalkRecord.status.in_(("queued", "running")),
            )
        ).all()
        return len(rows)

    def list_walk_records_for_tenant_v1(self, tenant_id: uuid.UUID) -> list[WalkApiRecordV1]:
        rows = list(
            self._session.scalars(
                select(CortexOctsDurableWalkRecord)
                .where(CortexOctsDurableWalkRecord.tenant_id == tenant_id)
                .order_by(CortexOctsDurableWalkRecord.walk_id.asc())
            ).all()
        )
        return [self._to_record(r) for r in rows]


def resolve_octs_walk_store_v1(session: Session | None) -> OctsWalkStoreProtocol:
    """Prefer durable store when a DB session is available."""
    if session is not None:
        return OctsWalkApiDurableStore(session)
    return octs_walk_api_memory_store_v1()
