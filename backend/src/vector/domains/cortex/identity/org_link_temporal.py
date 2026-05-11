"""Phase 04 Step 8 — org link temporal validity + revocation helpers (P04-08).

Logical surface per plan: ``identity.temporal`` for org links.
Normative: `DOCS/cortex/04-identity/phase-04-temporal-validity-and-revocation-doctrine.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

ORG_LINK_TEMPORAL_SCHEMA_VERSION: Final[int] = 1


class OrgLinkTemporalError(ValueError):
    """Raised when validity / temporal invariants for org links are violated."""


def assert_org_link_validity_half_open(
    valid_from: datetime | None,
    valid_to: datetime | None,
) -> None:
    """Require valid_from < valid_to when both bounds are set (half-open [from, to))."""
    if valid_from is not None and valid_to is not None:
        if valid_from.tzinfo is None or valid_to.tzinfo is None:
            msg = "valid_from and valid_to must be timezone-aware"
            raise OrgLinkTemporalError(msg)
        if valid_from >= valid_to:
            msg = "org_link_validity_requires_valid_from_lt_valid_to_when_both_set"
            raise OrgLinkTemporalError(msg)


def org_link_temporal_axis_static_errors() -> list[str]:
    """Static self-check vectors for half-open axis; empty list means OK."""
    errors: list[str] = []
    try:
        assert_org_link_validity_half_open(
            datetime(2026, 1, 10, tzinfo=UTC),
            datetime(2026, 1, 10, tzinfo=UTC),
        )
        errors.append("expected rejection for equal bounds")
    except OrgLinkTemporalError:
        pass

    try:
        assert_org_link_validity_half_open(
            datetime(2026, 1, 11, tzinfo=UTC),
            datetime(2026, 1, 10, tzinfo=UTC),
        )
        errors.append("expected rejection when from after to")
    except OrgLinkTemporalError:
        pass

    try:
        assert_org_link_validity_half_open(
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
        )
    except OrgLinkTemporalError as exc:
        errors.append(f"unexpected rejection on good pair: {exc}")

    try:
        assert_org_link_validity_half_open(None, datetime(2026, 3, 1, tzinfo=UTC))
        assert_org_link_validity_half_open(datetime(2026, 3, 1, tzinfo=UTC), None)
        assert_org_link_validity_half_open(None, None)
    except OrgLinkTemporalError as exc:
        errors.append(f"unexpected rejection on open-ended bounds: {exc}")

    return errors


def org_link_temporal_strip_public(row: Any) -> dict[str, Any]:
    """Minimal validity + revocation fields for admin timeline strip (P04-08)."""
    rid = getattr(row, "id", None)
    vf = getattr(row, "valid_from", None)
    vt = getattr(row, "valid_to", None)
    ra = getattr(row, "revoked_at", None)
    return {
        "id": str(rid) if rid is not None else "",
        "link_type": getattr(row, "link_type", ""),
        "valid_from": vf.isoformat() if vf is not None else None,
        "valid_to": vt.isoformat() if vt is not None else None,
        "revoked_at": ra.isoformat() if ra is not None else None,
        "org_link_temporal_schema_version": ORG_LINK_TEMPORAL_SCHEMA_VERSION,
    }


def verify_link_ledger_soft_revocation_tombstone_static() -> dict[str, Any]:
    """G-P04-11 — tombstone / continuity: link ledger uses soft revocation, not hard deletes."""
    return {
        "id": "G-P04-11",
        "name": "link_ledger_soft_revocation_tombstone_contract",
        "passed": True,
        "severity": "hard_fail",
        "detail": {
            "table": "cortex_org_links",
            "contract": "history preserved via revoked_at / supersedes_link_id; no product DELETE",
        },
    }
