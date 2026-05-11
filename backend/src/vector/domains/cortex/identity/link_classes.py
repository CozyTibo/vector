"""Phase 04 Step 7 — org link class discriminant + merge-closure helpers (P04-07).

Normative: `DOCS/cortex/04-identity/phase-04-hint-and-prohibited-link-doctrine.md`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final

LINK_CLASSES_SCHEMA_VERSION: Final[int] = 1


class OrgLinkClass(StrEnum):
    AUTHORITATIVE = "authoritative"
    HINT = "hint"
    INFERRED = "inferred"
    PROHIBITED = "prohibited"


NON_TRUTH_LINK_CLASSES: Final[frozenset[str]] = frozenset(
    {OrgLinkClass.HINT.value, OrgLinkClass.INFERRED.value, OrgLinkClass.PROHIBITED.value}
)

MERGE_CLOSURE_LINK_CLASSES: Final[frozenset[str]] = frozenset({OrgLinkClass.AUTHORITATIVE.value})


def normalize_link_class(value: str) -> str:
    v = (value or "").strip()
    if v not in {x.value for x in OrgLinkClass}:
        msg = f"invalid_link_class:{value!r}"
        raise ValueError(msg)
    return v


def row_eligible_for_merge_closure_material(row: Any) -> bool:
    """Truth-plane merge inputs: authoritative class + authoritative authority + active."""
    if row.revoked_at is not None:
        return False
    if row.link_class != OrgLinkClass.AUTHORITATIVE.value:
        return False
    return row.link_authority == "authoritative"


def verify_merge_closure_excludes_non_authoritative_link_classes_static() -> dict[str, Any]:
    """G-P04-02 — merge closure whitelist is authoritative-class only (static contract)."""
    ok = MERGE_CLOSURE_LINK_CLASSES == frozenset({OrgLinkClass.AUTHORITATIVE.value})
    return {
        "id": "G-P04-02",
        "name": "merge_closure_link_class_whitelist",
        "passed": ok,
        "severity": "hard_fail",
        "detail": {
            "merge_closure_link_classes": sorted(MERGE_CLOSURE_LINK_CLASSES),
            "non_truth_classes": sorted(NON_TRUTH_LINK_CLASSES),
        },
    }
