"""Celery tasks — Phase 01 Step 5 ingestion invariant verification (read-only)."""

from __future__ import annotations

import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants
from vector.infrastructure.db.session import session_scope

_TASK_VERIFY = "vector.cortex.ingestion.verify_tenant"


@celery_app.task(name=_TASK_VERIFY)
def run_cortex_ingestion_verify_task(
    tenant_id: str,
    run_limit: int = 30,
) -> dict[str, Any]:
    """Operator/async sweep of recent ingestion runs + checkpoint parseability for one tenant."""
    tid = uuid.UUID(tenant_id)
    with session_scope() as session:
        return verify_tenant_ingestion_invariants(session, tid, run_limit=run_limit)
