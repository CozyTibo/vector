"""Wave S3 — per-epoch materialization caps (orchestration; mix gate uses separate thresholds)."""

from __future__ import annotations

import os
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import uuid

RETRIEVAL_MATERIALIZATION_CAPS_SCHEMA_VERSION: Final[int] = 1

DEFAULT_MAX_ORG_LINK_ENTRIES_PER_EPOCH_V1: Final[int] = 100
DEFAULT_MAX_CANONICAL_MATERIALIZATIONS_PER_EPOCH_V1: Final[int] = 800

EXECUTION_MIX_SKIP_ORG_LINK_RATIO_V1: Final[float] = 0.60


def get_retrieval_max_org_link_entries_per_epoch_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(0, int(get_settings().cortex_retrieval_max_org_link_entries_per_epoch))
    except Exception:  # noqa: BLE001
        return DEFAULT_MAX_ORG_LINK_ENTRIES_PER_EPOCH_V1


def get_retrieval_max_canonical_materializations_per_epoch_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_retrieval_max_canonical_materializations_per_epoch))
    except Exception:  # noqa: BLE001
        return DEFAULT_MAX_CANONICAL_MATERIALIZATIONS_PER_EPOCH_V1


def retrieval_skip_org_link_when_execution_mix_met_enabled_v1() -> bool:
    """When false, always attempt org_link pass even if execution share ≥ 60% (S3.2 rollback)."""
    raw = os.environ.get("CORTEX_RETRIEVAL_SKIP_ORG_LINK_WHEN_EXECUTION_MIX_MET", "1")
    return raw.strip().lower() not in ("0", "false", "no", "off")


def count_epoch_index_entries_by_kind_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> dict[str, int]:
    from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import EXECUTION_INDEX_KINDS_V1
    from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

    rows = session.execute(
        select(CortexRetrievalIndexEntry.index_kind, func.count())
        .where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.index_epoch == index_epoch.strip(),
        )
        .group_by(CortexRetrievalIndexEntry.index_kind)
    ).all()
    by_kind = {str(kind): int(count) for kind, count in rows}
    total = sum(by_kind.values())
    execution = sum(by_kind.get(k, 0) for k in EXECUTION_INDEX_KINDS_V1)
    return {
        "total": total,
        "execution": execution,
        "org_link": by_kind.get("org_link", 0),
        "by_kind": by_kind,
    }


def should_skip_org_link_materialization_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> tuple[bool, dict[str, object]]:
    """Skip org_link pass when execution index share already meets mix target (S3.2)."""
    if not retrieval_skip_org_link_when_execution_mix_met_enabled_v1():
        return False, {"skip_enabled": False}
    counts = count_epoch_index_entries_by_kind_v1(
        session, tenant_id=tenant_id, index_epoch=index_epoch
    )
    total = int(counts["total"])
    execution = int(counts["execution"])
    if total <= 0:
        return False, {"reason": "empty_epoch", **counts}
    ratio = round(execution / total, 4)
    skip = ratio >= EXECUTION_MIX_SKIP_ORG_LINK_RATIO_V1
    return skip, {
        "skip_enabled": True,
        "execution_index_ratio": ratio,
        "execution_mix_skip_threshold": EXECUTION_MIX_SKIP_ORG_LINK_RATIO_V1,
        "skip_org_link": skip,
        **counts,
    }
