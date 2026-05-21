"""M8 — structured 410 Gone for removed admin execution bypass endpoints."""

from __future__ import annotations

from typing import Any, Final

from fastapi import HTTPException, status

M8_ADMIN_PLAN_REF_V1: Final[str] = (
    "DOCS/cortex/CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md#5-admin-simplification-plan"
)

EXECUTION_ADMIN_PREFIX_V1: Final[str] = "/admin/tenants/{tenant_id}/cortex/execution"


def execution_admin_path_v1(suffix: str) -> str:
    """Canonical replacement route under the execution admin surface."""
    base = EXECUTION_ADMIN_PREFIX_V1
    if not suffix.startswith("/"):
        suffix = f"/{suffix}"
    return f"{base}{suffix}"


def raise_admin_endpoint_gone(
    *,
    deprecated: str,
    replacement: str,
    migration: str | None = None,
) -> None:
    """Raise HTTP 410 with replacement route guidance (M8 deprecation contract)."""
    detail: dict[str, Any] = {
        "error": "admin_endpoint_removed",
        "deprecated": deprecated,
        "replacement": replacement,
        "ref": M8_ADMIN_PLAN_REF_V1,
    }
    if migration:
        detail["migration"] = migration
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=detail) from None
