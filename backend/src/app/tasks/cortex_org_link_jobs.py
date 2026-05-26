"""Phase 04 Step 5 — Celery entrypoints for link candidate regen + authoritative replay receipts."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.identity.anchor_continuity_candidates import run_anchor_continuity_candidate_regeneration
from vector.domains.cortex.identity.link_ledger import compute_authoritative_link_set_sha256, list_org_links
from vector.domains.cortex.identity.org_link_replay_runtime import (
    execute_org_link_replay_job,
    run_org_link_replay_job_for_row,
)
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_REGEN = "vector.cortex.identity.regenerate_link_candidates"
_TASK_REPLAY = "vector.cortex.identity.replay_authoritative_links"
_TASK_ORG_LINK_REPLAY_JOB = "vector.cortex.identity.run_org_link_replay_job"

CELERY_TASK_NAME_REGENERATE_LINK_CANDIDATES = _TASK_REGEN
CELERY_TASK_NAME_REPLAY_AUTHORITATIVE_LINKS = _TASK_REPLAY
CELERY_TASK_NAME_RUN_ORG_LINK_REPLAY_JOB = _TASK_ORG_LINK_REPLAY_JOB


@celery_app.task(name=_TASK_REGEN)
def regenerate_link_candidates_task(tenant_id: str, rule_version: str) -> dict[str, Any]:
    """Persist anchor-driven candidate batches (deterministic join keys + continuity fixtures)."""
    tid = uuid.UUID(tenant_id)
    _LOGGER.info("link_candidate_regen_start tenant_id=%s rule_version=%s", tenant_id, rule_version)
    with session_scope() as session:
        out = run_anchor_continuity_candidate_regeneration(session, tenant_id=tid)
    _LOGGER.info("link_candidate_regen_done tenant_id=%s out=%s", tenant_id, out)
    return out


@celery_app.task(name=_TASK_REPLAY)
def replay_authoritative_links_task(tenant_id: str) -> dict[str, Any]:
    """Compute authoritative link set hash for operator replay receipts."""
    tid = uuid.UUID(tenant_id)
    with session_scope() as session:
        sha = compute_authoritative_link_set_sha256(session, tenant_id=tid)
        n = len(list_org_links(session, tenant_id=tid, limit=50_000, link_authority="authoritative"))
    return {"tenant_id": tenant_id, "authoritative_set_sha256": sha, "authoritative_link_count": n}


@celery_app.task(name=_TASK_ORG_LINK_REPLAY_JOB, queue="vector")
def run_org_link_replay_job_task(
    tenant_id: str,
    job_kind: str | None = None,
    pinned_rule_version: str | None = None,
    dry_run: bool = False,
    scope_json: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Phase 04 Step 10 + Step 19 — org link replay job (sync create+run, or async row bound by ``job_id``)."""
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
    ):
        msg = (
            "job_kind must be authoritative_replay, candidate_regen, "
            "graph_projection_export, identity_continuity_rebuild, or identity_rebuild_from_anchors"
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
