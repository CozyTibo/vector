from __future__ import annotations

import uuid

from app.celery_app import celery_app
from vector.domains.cortex.identity.materialize import execute_identity_pass_for_tenant
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_TASK_IDENTITY_PASS = "vector.cortex.identity.run_pass"


@celery_app.task(name=_TASK_IDENTITY_PASS, queue="cortex_identity")
def run_cortex_identity_pass_task(
    tenant_id: str,
    source_trigger: str = "scheduled",
) -> dict[str, object]:
    tid = uuid.UUID(tenant_id)
    settings = get_settings()
    batch = settings.cortex_identity_batch_actor_limit
    max_attempts = settings.cortex_identity_max_attempts
    periodic_rescan_limit = settings.cortex_identity_periodic_rescan_limit
    resolver_version = settings.cortex_identity_resolver_version
    with session_scope() as session:
        out = execute_identity_pass_for_tenant(
            session,
            tenant_id=tid,
            source_trigger=source_trigger,
            batch_limit=batch,
            max_attempts=max_attempts,
            periodic_rescan_limit=periodic_rescan_limit,
            resolver_version=resolver_version,
        )
        session.commit()
    return out

