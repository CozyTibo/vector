"""Celery tasks — admin tenancy (hard-delete workspaces)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.tenancy.hard_delete_tenant import hard_delete_tenant
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_HARD_DELETE_BULK = "vector.admin.hard_delete_tenants_bulk"


@celery_app.task(name=_TASK_HARD_DELETE_BULK, queue="vector")
def hard_delete_tenants_bulk_task(tenant_ids: list[str]) -> dict[str, Any]:
    """Delete tenants one at a time (separate commits) so large tenants do not block the batch."""
    deleted: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for raw_id in tenant_ids:
        tid = uuid.UUID(raw_id)
        try:
            with session_scope() as session:
                out = hard_delete_tenant(session, tenant_id=tid)
                session.commit()
            deleted.append(
                {
                    "tenant_id": out["deleted_tenant_id"],
                    "company_name": out["deleted_company_name"],
                }
            )
            _LOGGER.info(
                "admin hard_delete tenant completed tenant_id=%s company=%s",
                out["deleted_tenant_id"],
                out["deleted_company_name"],
            )
        except Exception as exc:
            _LOGGER.exception("admin hard_delete tenant failed tenant_id=%s", raw_id)
            errors.append({"tenant_id": raw_id, "error": str(exc)[:500]})
    return {
        "deleted_count": len(deleted),
        "deleted": deleted,
        "errors": errors,
    }
