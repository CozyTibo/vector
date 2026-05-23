"""Phase C step C1 — phase 08 must not COMPLETED_EMPTY when retrieval entries exist."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

PHASE_C1_EMPTY_SCOPE_GATE_SCHEMA_VERSION: Final[int] = 1
P0_C1_STEP: Final[str] = "step_c1_phase08_empty_scope_truth"
EMPTY_SCOPE_WITH_ENTRIES_CODE_V1: Final[str] = "phase08_empty_scope_with_retrieval_entries"
EMPTY_SCOPE_WITH_ENTRIES_REASON_V1: Final[str] = (
    "retrieval_entries_exist_but_zero_synthesis_scopes_scheduled"
)


def is_phase08_empty_scope_truth_gate_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_phase08_fail_on_empty_scope_with_entries)
    except Exception:  # noqa: BLE001
        return True


def count_retrieval_entries_in_published_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str | None = None,
) -> dict[str, Any]:
    """Count retrieval index rows on the published epoch (any island scope)."""
    epoch = (published_index_epoch or "").strip() or get_published_index_epoch_v1(
        session, tenant_id=tenant_id
    )
    if not epoch:
        return {
            "published_index_epoch": None,
            "retrieval_entries_in_epoch": 0,
        }
    count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == epoch,
            )
        )
        or 0
    )
    return {
        "published_index_epoch": epoch,
        "retrieval_entries_in_epoch": count,
    }


def evaluate_phase08_empty_scope_truth_v1(
    materialize_output: dict[str, Any],
    *,
    retrieval_entries_in_epoch: int,
) -> dict[str, Any]:
    """
    C1 violation: scopes_scheduled == 0 and jobs_completed == 0 while entries exist on epoch.
    """
    scopes_scheduled = int(materialize_output.get("scopes_scheduled") or 0)
    jobs_completed = int(materialize_output.get("jobs_completed") or 0)
    scope_empty = bool(materialize_output.get("scope_empty"))
    entries = int(retrieval_entries_in_epoch or 0)
    violation = (
        is_phase08_empty_scope_truth_gate_enabled_v1()
        and entries > 0
        and scopes_scheduled == 0
        and jobs_completed == 0
    )
    lawful_empty = scope_empty and entries == 0 and jobs_completed == 0
    return {
        "ok": not violation,
        "violation": violation,
        "lawful_empty": lawful_empty,
        "retrieval_entries_in_epoch": entries,
        "scopes_scheduled": scopes_scheduled,
        "jobs_completed": jobs_completed,
        "scope_empty": scope_empty,
        "error_code": EMPTY_SCOPE_WITH_ENTRIES_CODE_V1 if violation else None,
        "blocked_reason": EMPTY_SCOPE_WITH_ENTRIES_REASON_V1 if violation else None,
        "phase_c1_schema_version": PHASE_C1_EMPTY_SCOPE_GATE_SCHEMA_VERSION,
    }


def attach_phase08_empty_scope_truth_gate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialize_output: dict[str, Any],
    published_index_epoch: str | None = None,
) -> dict[str, Any]:
    """Annotate materialize output with C1 gate evaluation (mutates copy)."""
    stats = count_retrieval_entries_in_published_epoch_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published_index_epoch
        or materialize_output.get("published_index_epoch"),
    )
    gate = evaluate_phase08_empty_scope_truth_v1(
        materialize_output,
        retrieval_entries_in_epoch=int(stats["retrieval_entries_in_epoch"]),
    )
    out = dict(materialize_output)
    out["retrieval_entries_in_epoch"] = stats["retrieval_entries_in_epoch"]
    out["published_index_epoch"] = out.get("published_index_epoch") or stats["published_index_epoch"]
    out["phase08_empty_scope_gate"] = gate
    if gate["violation"]:
        out["empty_scope_violation"] = True
        out["error_code"] = EMPTY_SCOPE_WITH_ENTRIES_CODE_V1
        out["empty_scope_reason"] = EMPTY_SCOPE_WITH_ENTRIES_REASON_V1
    return out


def should_fail_phase08_for_empty_scope_violation_v1(materialize_output: dict[str, Any]) -> bool:
    if not is_phase08_empty_scope_truth_gate_enabled_v1():
        return False
    gate = dict(materialize_output.get("phase08_empty_scope_gate") or {})
    return bool(materialize_output.get("empty_scope_violation")) or bool(gate.get("violation"))
