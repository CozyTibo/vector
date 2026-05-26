"""Phase 04 Step 19 — Celery entrypoint for org-link replay jobs (Wave 3: legacy regen/replay tasks removed)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.identity.org_link_replay_runtime import (
    execute_org_link_replay_job,
    run_org_link_replay_job_for_row,
)
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_ORG_LINK_REPLAY_JOB = "vector.cortex.identity.run_org_link_replay_job"

CELERY_TASK_NAME_RUN_ORG_LINK_REPLAY_JOB = _TASK_ORG_LINK_REPLAY_JOB

# Wave 3 tombstone names — must not be registered (see scheduling.M9_DEAD_CELERY_TASK_NAMES_V1).
CELERY_TASK_NAME_REGENERATE_LINK_CANDIDATES = "vector.cortex.identity.regenerate_link_candidates"
CELERY_TASK_NAME_REPLAY_AUTHORITATIVE_LINKS = "vector.cortex.identity.replay_authoritative_links"


@celery_app.task(name=_TASK_ORG_LINK_REPLAY_JOB, queue="vector")
def run_org_link_replay_job_task(
    tenant_id: str,
    job_kind: str | None = None,
    pinned_rule_version: str | None = None,
    dry_run: bool = False,
    scope_json: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Org link replay job (sync create+run, or async row bound by ``job_id``)."""
    tid = uuid.UUID(tenant_id)
    if job_id:
        jid = uuid.UUID(job_id.strip())
        _LOGGER.info("org_link_replay_job_start tenant_id=%s job_id=%s (async row)", tenant_id, job_id)
        with session_scope() as session:
            job = session.get(CortexOrgLinkReplayJob, jid)
            if job is None or job.tenant_id != tid:
                msg = "org_link_replay_job_not_found_or_tenant_mismatch"
                raise ValueError(msg)
            if job.status != "queued":
                status_out = job.status
                _LOGGER.info(
                    "org_link_replay_job_skip tenant_id=%s job_id=%s status=%s",
                    tenant_id,
                    job_id,
                    status_out,
                )
                return {"tenant_id": tenant_id, "job_id": str(jid), "status": status_out, "skipped": True}
            run_org_link_replay_job_for_row(session, job)
            session.refresh(job)
            status_out = job.status
        _LOGGER.info("org_link_replay_job_done tenant_id=%s job_id=%s status=%s", tenant_id, job_id, status_out)
        return {"tenant_id": tenant_id, "job_id": str(jid), "status": status_out}

    jk = job_kind
    if jk not in (
        "authoritative_replay",
        "candidate_regen",
        "graph_projection_export",
        "identity_continuity_rebuild",
        "identity_rebuild_from_anchors",
        "lawful_edge_promotion",
    ):
        msg = (
            "job_kind must be authoritative_replay, candidate_regen, graph_projection_export, "
            "identity_continuity_rebuild, identity_rebuild_from_anchors, or lawful_edge_promotion"
        )
        raise ValueError(msg)
    _LOGGER.info(
        "org_link_replay_job_start tenant_id=%s job_kind=%s dry_run=%s",
        tenant_id,
        jk,
        dry_run,
    )
    with session_scope() as session:
        job = execute_org_link_replay_job(
            session,
            tenant_id=tid,
            job_kind=jk,  # type: ignore[arg-type]
            pinned_rule_version=pinned_rule_version,
            dry_run=dry_run,
            scope_json=scope_json,
        )
        jid = job.id
        status_out = job.status
    _LOGGER.info("org_link_replay_job_done tenant_id=%s job_id=%s status=%s", tenant_id, jid, status_out)
    return {"tenant_id": tenant_id, "job_id": str(jid), "status": status_out}
