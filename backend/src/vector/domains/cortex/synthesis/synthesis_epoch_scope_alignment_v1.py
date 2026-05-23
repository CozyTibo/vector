"""Wave S4 step 17 — synthesis uses published epoch + primary island in-scope rows (epoch/scope alignment)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
    count_retrieval_entries_in_scope_v1,
    find_prior_published_epoch_v1,
    reconcile_primary_island_scope_on_epoch_change_v1,
    resolve_primary_island_scope_id_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
    count_retrieval_entries_in_published_epoch_v1,
)

SYNTHESIS_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION: Final[int] = 1
FAILURE_CODE_ZERO_IN_SCOPE_V1: Final[str] = "synthesis_epoch_scope_zero_in_scope"
WAVE_S4_STEP_17: Final[str] = "wave_s4_synthesis_epoch_scope_alignment"


class SynthesisEpochScopeError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def is_synthesis_epoch_scope_gate_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_synthesis_epoch_scope_gate_enabled)
    except Exception:  # noqa: BLE001
        return True


def ensure_retrieval_scope_for_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str | None = None,
    island_scope_id: str | None = None,
    force_realign: bool = True,
) -> dict[str, Any]:
    """Realign island tags on published epoch before phase 08 scopes are built."""
    epoch = (published_index_epoch or "").strip() or get_published_index_epoch_v1(
        session, tenant_id=tenant_id
    )
    scope = (island_scope_id or "").strip() or resolve_primary_island_scope_id_v1(
        session, tenant_id=tenant_id
    )[0]
    prior = find_prior_published_epoch_v1(session, tenant_id=tenant_id, exclude_epoch=epoch)
    epoch_stats = count_retrieval_entries_in_published_epoch_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=epoch,
    )
    in_scope_before = (
        count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=epoch or "",
            island_scope_id=scope,
        )
        if epoch and scope
        else 0
    )
    reconcile = reconcile_primary_island_scope_on_epoch_change_v1(
        session,
        tenant_id=tenant_id,
        prior_published_epoch=prior,
        new_published_epoch=epoch,
        island_scope_id=scope,
        force_realign=force_realign,
    )
    in_scope_after = int(reconcile.get("retrieval_entries_in_scope") or 0)
    fizzer_in_scope = (
        count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=epoch or "",
            island_scope_id=FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
        )
        if epoch
        else 0
    )
    return {
        "schema_version": SYNTHESIS_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION,
        "published_index_epoch": epoch,
        "primary_island_scope_id": scope,
        "prior_published_index_epoch": prior,
        "retrieval_entries_in_epoch": int(epoch_stats.get("retrieval_entries_in_epoch") or 0),
        "retrieval_entries_in_scope_before": in_scope_before,
        "retrieval_entries_in_scope": in_scope_after,
        "fizzer_primary_in_scope": fizzer_in_scope,
        "epoch_scope_reconcile": reconcile,
        "primary_island_in_scope_ok": in_scope_after > 0,
    }


def evaluate_synthesis_epoch_scope_readiness_v1(
    scope_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Violation when epoch has rows but primary island has zero in-scope tagged rows."""
    entries_in_epoch = int(scope_snapshot.get("retrieval_entries_in_epoch") or 0)
    in_scope = int(scope_snapshot.get("retrieval_entries_in_scope") or 0)
    violation = (
        is_synthesis_epoch_scope_gate_enabled_v1()
        and entries_in_epoch > 0
        and in_scope <= 0
    )
    return {
        "ok": not violation,
        "violation": violation,
        "retrieval_entries_in_epoch": entries_in_epoch,
        "retrieval_entries_in_scope": in_scope,
        "error_code": FAILURE_CODE_ZERO_IN_SCOPE_V1 if violation else None,
        "blocked_reason": (
            "published_epoch_has_entries_but_zero_primary_island_in_scope"
            if violation
            else None
        ),
    }


def attach_synthesis_epoch_scope_gate_v1(
    materialize_output: dict[str, Any],
    *,
    scope_snapshot: dict[str, Any],
) -> dict[str, Any]:
    out = dict(materialize_output)
    out["synthesis_epoch_scope_alignment"] = scope_snapshot
    out["retrieval_entries_in_scope"] = int(
        scope_snapshot.get("retrieval_entries_in_scope")
        or out.get("retrieval_entries_in_scope")
        or 0
    )
    gate = evaluate_synthesis_epoch_scope_readiness_v1(scope_snapshot)
    out["synthesis_epoch_scope_gate"] = gate
    if gate["violation"]:
        out["epoch_scope_violation"] = True
        out["error_code"] = FAILURE_CODE_ZERO_IN_SCOPE_V1
    return out


def should_fail_phase08_for_epoch_scope_violation_v1(materialize_output: dict[str, Any]) -> bool:
    if not is_synthesis_epoch_scope_gate_enabled_v1():
        return False
    gate = dict(materialize_output.get("synthesis_epoch_scope_gate") or {})
    return bool(materialize_output.get("epoch_scope_violation")) or bool(gate.get("violation"))
