"""Phase 03 Step 12 — temporal anchors, deterministic ordering keys, supersession ledger.

Normative: `DOCS/cortex/03-canonical/phase-03-temporal-timeline-doctrine.md`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
from vector.infrastructure.db.models.cortex_canonical_temporal_supersession import (
    CortexCanonicalTemporalSupersession,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

TEMPORAL_RUNTIME_SCHEMA_VERSION: Final[int] = 2


def _parse_payload_timestamp(payload: dict[str, Any]) -> datetime | None:
    for key in (
        "provider_event_timestamp",
        "created_at",
        "createdAt",
        "updated_at",
        "updatedAt",
        "edited_at",
        "ts",
    ):
        v = payload.get(key)
        if isinstance(v, str) and len(v) >= 4:
            s = v.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt.astimezone(UTC)
            except ValueError:
                continue
    te = payload.get("timeline_event") if isinstance(payload.get("timeline_event"), dict) else {}
    te_cat = te.get("created_at")
    if isinstance(te_cat, str) and len(te_cat) >= 4:
        s = te_cat.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            pass
    return None


def occurred_at_from_raw(raw: RawIngestionRecord) -> datetime:
    """Best-effort occurred time from payload; else raw fetch time.

    Priority: ``provider_event_timestamp`` and other explicit provider fields (see
    ``_parse_payload_timestamp``), then ``fetched_at``.
    """
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    parsed = _parse_payload_timestamp(payload)
    if parsed is not None:
        return parsed
    fa = raw.fetched_at
    if fa.tzinfo is None:
        return fa.replace(tzinfo=UTC)
    return fa.astimezone(UTC)


# Postgres text must not contain NUL (0x00). Use ASCII unit separator (0x1f) between segments.
_ORDER_KEY_SEP = "\x1f"


def build_temporal_ordering_key(
    *,
    occurred_at: datetime,
    replay_sequence: int,
    source_revision_key: str,
    raw_record_id: int,
) -> str:
    """Lexicographic key: occurred_at, replay_sequence, revision, raw id."""
    occ = occurred_at.astimezone(UTC).isoformat()
    seq = f"{int(replay_sequence):016d}"
    rev = source_revision_key or ""
    rid = f"{int(raw_record_id):012d}"
    return f"{occ}{_ORDER_KEY_SEP}{seq}{_ORDER_KEY_SEP}{rev}{_ORDER_KEY_SEP}{rid}"


def record_temporal_supersession(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    predecessor_materialization_id: uuid.UUID,
    predecessor_logical_key_hash: str,
    successor_materialization_id: uuid.UUID,
    causing_raw_record_id: int,
    engine_build_ref: str,
) -> CortexCanonicalTemporalSupersession:
    row = CortexCanonicalTemporalSupersession(
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        predecessor_materialization_id=predecessor_materialization_id,
        predecessor_logical_key_hash=predecessor_logical_key_hash,
        successor_materialization_id=successor_materialization_id,
        causing_raw_record_id=causing_raw_record_id,
        engine_build_ref=engine_build_ref,
    )
    db.add(row)
    db.flush()
    return row


def supersession_public_dict(row: CortexCanonicalTemporalSupersession) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "bundle_id": row.bundle_id,
        "predecessor_materialization_id": row.predecessor_materialization_id,
        "predecessor_logical_key_hash": row.predecessor_logical_key_hash,
        "successor_materialization_id": row.successor_materialization_id,
        "causing_raw_record_id": row.causing_raw_record_id,
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at,
    }


def list_temporal_supersessions(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
    bundle_id: str | None = None,
) -> list[CortexCanonicalTemporalSupersession]:
    lim = max(1, min(limit, 200))
    q = select(CortexCanonicalTemporalSupersession).where(
        CortexCanonicalTemporalSupersession.tenant_id == tenant_id
    )
    if bundle_id:
        q = q.where(CortexCanonicalTemporalSupersession.bundle_id == bundle_id)
    q = q.order_by(CortexCanonicalTemporalSupersession.created_at.desc()).limit(lim)
    return list(db.scalars(q).all())


def preview_rebuild_raw_order(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    raw_record_ids: list[int],
) -> list[dict[str, Any]]:
    """Sort raw ids by temporal ordering key (rebuild ingest-order proof)."""
    if not raw_record_ids:
        return []
    uniq = sorted(set(raw_record_ids))
    rows = db.scalars(
        select(RawIngestionRecord).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.id.in_(uniq),
        )
    ).all()
    by_id = {r.id: r for r in rows}
    out: list[tuple[str, int, RawIngestionRecord]] = []
    key_by_id: dict[int, str] = {}
    for rid in uniq:
        r = by_id.get(rid)
        if r is None:
            continue
        occ = occurred_at_from_raw(r)
        key = build_temporal_ordering_key(
            occurred_at=occ,
            replay_sequence=int(r.replay_sequence),
            source_revision_key=str(r.source_revision_key),
            raw_record_id=int(r.id),
        )
        key_by_id[int(r.id)] = key
        out.append((key, int(r.id), r))
    out.sort(key=lambda t: t[0])
    topology = build_replay_dependency_topology([r for _k, _rid, r in out], temporal_key_by_id=key_by_id)
    ord_index = {rid: idx for idx, rid in enumerate(topology["ordered_raw_record_ids"])}
    out.sort(key=lambda t: (ord_index.get(t[1], 10**9), t[0]))
    return [
        {
            "raw_record_id": rid,
            "temporal_ordering_key": k,
            "occurred_at": occurred_at_from_raw(r).isoformat(),
            "source_revision_key": str(r.source_revision_key),
            "replay_sequence": int(r.replay_sequence),
            "replay_topology_order_index": int(next((x for x in [ord_index.get(rid)] if x is not None), 0)),
        }
        for k, rid, r in out
    ]
