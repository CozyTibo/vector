"""Wave S3 — retrieval index semantic mix gates (execution-shaped index, not org_link mirror)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_materialization_caps_v1 import (
    get_retrieval_max_canonical_materializations_per_epoch_v1,
    get_retrieval_max_org_link_entries_per_epoch_v1,
)

RETRIEVAL_SEMANTIC_MIX_SCHEMA_VERSION: Final[int] = 1

ORG_LINK_PCT_MAX_V1: Final[float] = 30.0
ORG_ENTITY_PCT_MAX_V1: Final[float] = 10.0
EXECUTION_INDEX_PCT_MIN_V1: Final[float] = 60.0

EXECUTION_INDEX_KINDS_V1: Final[frozenset[str]] = frozenset(
    {"materialization", "walk", "causal_chain", "causal_edge"}
)

ORG_LINK_KIND_V1: Final[str] = "org_link"
ORG_ENTITY_KIND_V1: Final[str] = "org_entity"

FAILURE_CODE_SEMANTIC_MIX_V1: Final[str] = "retrieval_semantic_mix_violation"


class RetrievalSemanticMixError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def is_retrieval_semantic_mix_gate_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_retrieval_semantic_mix_gate_enabled)
    except Exception:  # noqa: BLE001
        return True


def snapshot_retrieval_index_mix_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> dict[str, Any]:
    """Mix breakdown for one materialized epoch (published or BUILDING)."""
    tid = str(tenant_id)
    epoch = index_epoch.strip()
    rows = session.execute(
        text(
            """
            SELECT index_kind, COUNT(*)::bigint AS n
            FROM cortex_retrieval_index_entries
            WHERE tenant_id = :tenant AND index_epoch = :epoch
            GROUP BY 1 ORDER BY n DESC
            """
        ),
        {"tenant": tid, "epoch": epoch},
    ).mappings().all()
    by_kind: dict[str, int] = {str(r["index_kind"]): int(r["n"]) for r in rows}
    total = sum(by_kind.values())
    org_link = by_kind.get(ORG_LINK_KIND_V1, 0)
    org_entity = by_kind.get(ORG_ENTITY_KIND_V1, 0)
    execution = sum(by_kind.get(k, 0) for k in EXECUTION_INDEX_KINDS_V1)
    org_link_pct = round(100.0 * org_link / total, 2) if total else None
    org_entity_pct = round(100.0 * org_entity / total, 2) if total else None
    execution_pct = round(100.0 * execution / total, 2) if total else None
    dup_row = session.execute(
        text(
            """
            SELECT
              COUNT(*)::bigint AS total_rows,
              COUNT(DISTINCT retrieval_lookup_id)::bigint AS distinct_lookup
            FROM cortex_retrieval_index_entries
            WHERE tenant_id = :tenant AND index_epoch = :epoch
            """
        ),
        {"tenant": tid, "epoch": epoch},
    ).mappings().first()
    total_rows = int(dup_row["total_rows"] or 0) if dup_row else total
    distinct_lookup = int(dup_row["distinct_lookup"] or 0) if dup_row else total
    duplicate_lookup_ids = max(0, total_rows - distinct_lookup)
    return {
        "schema_version": RETRIEVAL_SEMANTIC_MIX_SCHEMA_VERSION,
        "tenant_id": tid,
        "index_epoch": epoch,
        "entry_count": total,
        "index_kind_counts": [{"index_kind": k, "count": v} for k, v in sorted(by_kind.items())],
        "org_link_count": org_link,
        "org_entity_count": org_entity,
        "execution_index_count": execution,
        "org_link_pct": org_link_pct,
        "org_entity_pct": org_entity_pct,
        "execution_index_pct": execution_pct,
        "duplicate_retrieval_lookup_ids": duplicate_lookup_ids,
    }


def validate_retrieval_semantic_mix_v1(mix: dict[str, Any]) -> tuple[bool, list[str]]:
    """L1 mix gate + L2 non-empty execution (when entries exist)."""
    violations: list[str] = []
    total = int(mix.get("entry_count") or 0)
    if total <= 0:
        violations.append("empty_epoch")
        return False, violations
    org_link_pct = mix.get("org_link_pct")
    if org_link_pct is not None and float(org_link_pct) > ORG_LINK_PCT_MAX_V1:
        violations.append(f"org_link_pct>{ORG_LINK_PCT_MAX_V1}")
    org_entity_pct = mix.get("org_entity_pct")
    if org_entity_pct is not None and float(org_entity_pct) > ORG_ENTITY_PCT_MAX_V1:
        violations.append(f"org_entity_pct>{ORG_ENTITY_PCT_MAX_V1}")
    execution_pct = mix.get("execution_index_pct")
    if execution_pct is not None and float(execution_pct) < EXECUTION_INDEX_PCT_MIN_V1:
        violations.append(f"execution_index_pct<{EXECUTION_INDEX_PCT_MIN_V1}")
    execution_count = int(mix.get("execution_index_count") or 0)
    if execution_count < 1:
        violations.append("execution_index_empty")
    if int(mix.get("duplicate_retrieval_lookup_ids") or 0) > 0:
        violations.append("duplicate_retrieval_lookup_id")
    return len(violations) == 0, violations


def build_semantic_mix_receipt_v1(
    mix: dict[str, Any],
    *,
    gate_pass: bool,
) -> dict[str, Any]:
    """Operator receipt shape for published epoch mix (S3.4 composition law)."""
    return {
        "org_link_pct": mix.get("org_link_pct"),
        "org_entity_pct": mix.get("org_entity_pct"),
        "execution_index_pct": mix.get("execution_index_pct"),
        "entry_count": int(mix.get("entry_count") or 0),
        "index_epoch": mix.get("index_epoch"),
        "gate_pass": bool(gate_pass),
    }


def enforce_retrieval_semantic_mix_before_publish_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> dict[str, Any]:
    """Run mix validation; raise when gate enabled and laws fail (Wave S3 L1)."""
    mix = snapshot_retrieval_index_mix_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    ok, violations = validate_retrieval_semantic_mix_v1(mix)
    out = {
        "mix_gate_enabled": is_retrieval_semantic_mix_gate_enabled_v1(),
        "mix_ok": ok,
        "violations": violations,
        "mix": mix,
        "semantic_mix": build_semantic_mix_receipt_v1(mix, gate_pass=ok),
    }
    if not ok and is_retrieval_semantic_mix_gate_enabled_v1():
        raise RetrievalSemanticMixError(
            FAILURE_CODE_SEMANTIC_MIX_V1,
            detail=out,
        )
    return out
