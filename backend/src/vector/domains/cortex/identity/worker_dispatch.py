"""Phase 04 Step 19 — tenant-bound Celery task visibility (P04-19)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Final, Literal

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from vector.infrastructure.db.models.cortex_identity_celery_dispatch import CortexIdentityCeleryDispatch
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob

IDENTITY_WORKER_DISPATCH_SCHEMA_VERSION: Final[int] = 1


def append_identity_celery_dispatch(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    celery_task_id: str,
    task_name: str,
    request_summary: dict[str, Any] | None = None,
) -> CortexIdentityCeleryDispatch:
    row = CortexIdentityCeleryDispatch(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        celery_task_id=celery_task_id.strip(),
        task_name=task_name.strip(),
        request_summary_json=dict(request_summary or {}),
    )
    session.add(row)
    session.flush()
    return row


def resolve_worker_task_binding(
    session: Session, *, tenant_id: uuid.UUID, celery_task_id: str
) -> tuple[Literal["replay_job", "dispatch"], uuid.UUID | None]:
    """Return binding kind + replay job id when applicable."""
    cid = celery_task_id.strip()
    job = session.scalars(
        select(CortexOrgLinkReplayJob).where(
            CortexOrgLinkReplayJob.tenant_id == tenant_id,
            CortexOrgLinkReplayJob.celery_task_id == cid,
        )
    ).first()
    if job is not None:
        return "replay_job", job.id
    disp = session.scalars(
        select(CortexIdentityCeleryDispatch).where(
            CortexIdentityCeleryDispatch.tenant_id == tenant_id,
            CortexIdentityCeleryDispatch.celery_task_id == cid,
        )
    ).first()
    if disp is not None:
        return "dispatch", None
    msg = "worker_task_not_found_for_tenant"
    raise KeyError(msg)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def build_worker_task_status_payload(*, celery_task_id: str, bind_kind: str, job_id: uuid.UUID | None) -> dict[str, Any]:
    ar = AsyncResult(celery_task_id, app=celery_app)
    state = str(ar.state or "UNKNOWN")
    ready = bool(ar.ready())
    err: str | None = None
    result: dict[str, Any] | None = None
    if ar.successful():
        raw = ar.result
        if isinstance(raw, dict):
            result = {k: _json_safe(v) for k, v in raw.items()}
        elif raw is not None:
            result = {"value": _json_safe(raw)}
    elif ar.failed():
        try:
            err = str(ar.info)[:8000]
        except Exception:
            err = "task_failed"
    return {
        "celery_task_id": celery_task_id,
        "bind_source": bind_kind,
        "job_id": job_id,
        "celery_state": state,
        "ready": ready,
        "result": result,
        "error": err,
    }
