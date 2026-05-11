"""Phase 04 Step 18 — verification gates **G-P04-22**–**G-P04-26** (operator console)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.link_explorer import LINK_EXPLORER_FILTER_KEYS, list_org_link_explorer_rows
from vector.domains.cortex.identity.operator_console import (
    IDENTITY_CONSOLE_AUDITED_POST_ACTIONS,
    org_primitive_list_row_v1,
)
from vector.domains.cortex.identity.org_ambiguity import count_open_org_ambiguity_records, list_org_ambiguity_records
from vector.domains.cortex.identity.projection_export import (
    PROJECTION_PREVIEW_TOP_LEVEL_KEYS,
    build_org_graph_projection_preview_metadata,
    verify_gp04_25_projection_preview_shape_static,
)
from vector.domains.cortex.identity.execution_primitives import list_org_primitive_instances


def verify_gp04_22_link_explorer_filters_session(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """**G-P04-22** — every §9.2 filter key is accepted by the explorer (no crash; invalid combo excluded)."""
    errors: list[str] = []
    try:
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, authoritative_only=True)
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, candidate_only=True)
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, ambiguous=True)
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, revoked=True)
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, replay_drift=True)
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, rule_version="nope")
        list_org_link_explorer_rows(
            session, tenant_id=tenant_id, limit=3, primitive_id=uuid.uuid4(), handle_id=uuid.uuid4()
        )
        list_org_link_explorer_rows(session, tenant_id=tenant_id, limit=3, time_valid_at=datetime.now(tz=UTC))
    except Exception as exc:  # noqa: BLE001 — gate surfaces unexpected filter regressions
        errors.append(f"explorer_filter_smoke_failed:{exc!s}")
    try:
        list_org_link_explorer_rows(
            session, tenant_id=tenant_id, limit=1, authoritative_only=True, candidate_only=True
        )
        errors.append("expected_value_error_for_exclusive_filters")
    except ValueError:
        pass
    doctrine = {
        "authoritative_only",
        "candidate_only",
        "ambiguous",
        "revoked",
        "replay_drift",
        "rule_version",
        "primitive_id",
        "handle_id",
        "time_valid_at",
    }
    if LINK_EXPLORER_FILTER_KEYS != doctrine:
        errors.append("link_explorer_filter_keys_drift")
    return {
        "id": "G-P04-22",
        "name": "link_ledger_explorer_filters",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors, "filter_keys": sorted(LINK_EXPLORER_FILTER_KEYS)},
    }


def verify_gp04_23_operator_console_audit_discipline_static() -> dict[str, Any]:
    """**G-P04-23** — merge-queue / revoke POST surfaces declare audited ``action_kind`` values."""
    ok = len(IDENTITY_CONSOLE_AUDITED_POST_ACTIONS) >= 4
    return {
        "id": "G-P04-23",
        "name": "identity_operator_console_post_audit_discipline",
        "passed": ok,
        "severity": "hard_fail",
        "detail": {"audited_action_kinds": sorted(IDENTITY_CONSOLE_AUDITED_POST_ACTIONS)},
    }


def verify_gp04_24_org_ambiguity_queue_honesty(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """**G-P04-24** — open backlog count implies list API can return ≥1 open row."""
    n_open = count_open_org_ambiguity_records(session, tenant_id=tenant_id)
    if n_open == 0:
        return {
            "id": "G-P04-24",
            "name": "org_ambiguity_queue_honesty",
            "passed": True,
            "severity": "hard_fail",
            "detail": {"open_count": 0, "note": "no_open_backlog"},
        }
    rows = list_org_ambiguity_records(session, tenant_id=tenant_id, limit=1, status="open")
    passed = len(rows) >= 1
    detail: dict[str, Any] = {"open_count": n_open, "list_open_sample_count": len(rows)}
    if not passed:
        detail["diagnostic_code"] = "backlog_mismatch"
    return {
        "id": "G-P04-24",
        "name": "org_ambiguity_queue_honesty",
        "passed": passed,
        "severity": "hard_fail",
        "detail": detail,
    }


def verify_gp04_25_projection_preview_metadata_only(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """**G-P04-25** — preview payload is metadata-only (no adjacency arrays)."""
    preview = build_org_graph_projection_preview_metadata(session, tenant_id=tenant_id)
    st = verify_gp04_25_projection_preview_shape_static(preview)
    errors = list(st.get("detail", {}).get("errors", [])) if isinstance(st.get("detail"), dict) else []
    return {
        "id": "G-P04-25",
        "name": "projection_preview_metadata_only",
        "passed": bool(st.get("passed")),
        "severity": "hard_fail",
        "detail": {"errors": errors, "allowed_keys": sorted(PROJECTION_PREVIEW_TOP_LEVEL_KEYS)},
    }


def verify_gp04_26_primitive_default_list_shape(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """**G-P04-26** — default primitive explorer rows exclude raw ``envelope_json``."""
    errors: list[str] = []
    for row in list_org_primitive_instances(session, tenant_id=tenant_id, limit=8):
        d = org_primitive_list_row_v1(row, include_raw_envelope=False)
        if "envelope_json" in d:
            errors.append(f"unexpected_envelope_key:{row.id}")
    return {
        "id": "G-P04-26",
        "name": "primitive_default_list_without_raw_blob",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
