"""Cortex debug-only admin routes (Wave 2 — not linked from primary operator nav)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.contracts.admin import (
    AdminCortexIdentityBackfillFromAnchorsRequest,
    AdminCortexIdentityBackfillFromAnchorsResponse,
    AdminCortexIdentityBackfillRunsListResponse,
    AdminCortexOrgLinkReplayJobDetailResponse,
    AdminCortexOrgLinkReplayJobEnqueueRequest,
    AdminCortexOrgLinkReplayJobEnqueueResponse,
    AdminCortexOrgLinkReplayJobItem,
    AdminCortexOrgLinkReplayJobListResponse,
    AdminCortexOrgLinkReplayJobRunRequest,
    AdminCortexOrgLinkReplayJobRunResponse,
)
from vector.domains.cortex.identity.debug_full_substrate_refresh_v1 import (
    DEBUG_FULL_SUBSTRATE_REFRESH_ACK_KEY_V1,
    DEBUG_FULL_SUBSTRATE_REFRESH_SURFACE_KIND_V1,
    run_debug_full_substrate_refresh_v1,
)
from vector.domains.cortex.identity.identity_substrate_operator_v1 import (
    WAVE2_COLLAPSED_REPLAY_JOB_KINDS_V1,
)


def register_cortex_debug_routes(r: APIRouter, *, assert_tenant) -> None:
    """Register ``/tenants/{tenant_id}/cortex/debug/...`` routes."""

    @r.post(
        "/tenants/{tenant_id}/cortex/debug/identity/backfill/from-canonical-anchors",
        response_model=AdminCortexIdentityBackfillFromAnchorsResponse,
        tags=["cortex-debug"],
    )
    def admin_debug_identity_backfill_from_canonical_anchors(
        tenant_id: uuid.UUID,
        body: AdminCortexIdentityBackfillFromAnchorsRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityBackfillFromAnchorsResponse:
        assert_tenant(db, tenant_id)
        if body.include_candidate_regen:
            from vector.domains.cortex.identity.continuity_rebuild import (
                run_identity_handles_and_candidates_refresh,
            )

            raw = run_identity_handles_and_candidates_refresh(
                db,
                tenant_id=tenant_id,
                dry_run=body.dry_run,
                anchor_limit=body.anchor_limit,
            )
        else:
            from vector.domains.cortex.identity.backfill import run_anchor_handle_backfill

            raw = run_anchor_handle_backfill(
                db,
                tenant_id=tenant_id,
                dry_run=body.dry_run,
                anchor_limit=body.anchor_limit,
                skip_candidate_regen=True,
            )
        db.commit()
        return AdminCortexIdentityBackfillFromAnchorsResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/debug/identity/backfill/runs",
        response_model=AdminCortexIdentityBackfillRunsListResponse,
        tags=["cortex-debug"],
    )
    def admin_debug_identity_backfill_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexIdentityBackfillRunsListResponse:
        assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.backfill import (
            ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
            list_org_identity_backfill_runs,
            org_identity_backfill_run_public_dict,
        )
        from vector.contracts.admin import AdminCortexIdentityBackfillRunItem

        rows = list_org_identity_backfill_runs(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexIdentityBackfillRunsListResponse(
            org_identity_backfill_schema_version=ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            runs=[
                AdminCortexIdentityBackfillRunItem.model_validate(org_identity_backfill_run_public_dict(row))
                for row in rows
            ],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/debug/identity/replay-jobs",
        response_model=AdminCortexOrgLinkReplayJobListResponse,
        tags=["cortex-debug"],
    )
    def admin_debug_identity_replay_jobs_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexOrgLinkReplayJobListResponse:
        assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            list_org_link_replay_jobs,
            org_link_replay_job_public_dict,
        )

        jobs = list_org_link_replay_jobs(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexOrgLinkReplayJobListResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            jobs=[AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(j)) for j in jobs],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/debug/identity/replay-jobs/{job_id}",
        response_model=AdminCortexOrgLinkReplayJobDetailResponse,
        tags=["cortex-debug"],
    )
    def admin_debug_identity_replay_job_detail(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobDetailResponse:
        assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            get_org_link_replay_job,
            org_link_replay_job_public_dict,
            org_link_replay_receipt_public_dict,
        )
        from vector.contracts.admin import AdminCortexOrgLinkReplayJobReceiptItem

        job = get_org_link_replay_job(db, tenant_id=tenant_id, job_id=job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_link_replay_job_not_found")
        receipts = sorted(job.receipts or [], key=lambda rc: rc.created_at or rc.id)
        return AdminCortexOrgLinkReplayJobDetailResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
            receipts=[
                AdminCortexOrgLinkReplayJobReceiptItem.model_validate(org_link_replay_receipt_public_dict(rc))
                for rc in receipts
            ],
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/debug/identity/replay-jobs/run",
        response_model=AdminCortexOrgLinkReplayJobRunResponse,
        tags=["cortex-debug"],
    )
    def admin_debug_identity_replay_jobs_run(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgLinkReplayJobRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobRunResponse:
        assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            OrgLinkReplayError,
            execute_org_link_replay_job,
            org_link_replay_job_public_dict,
        )

        scope = dict(body.scope_json or {})
        if body.job_kind in WAVE2_COLLAPSED_REPLAY_JOB_KINDS_V1:
            scope[DEBUG_FULL_SUBSTRATE_REFRESH_ACK_KEY_V1] = True
        try:
            job = execute_org_link_replay_job(
                db,
                tenant_id=tenant_id,
                job_kind=body.job_kind,
                pinned_rule_version=body.pinned_rule_version,
                dry_run=body.dry_run,
                scope_json=scope or None,
            )
        except OrgLinkReplayError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        db.commit()
        db.refresh(job)
        return AdminCortexOrgLinkReplayJobRunResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/debug/identity/replay-jobs/enqueue",
        response_model=AdminCortexOrgLinkReplayJobEnqueueResponse,
        tags=["cortex-debug"],
    )
    def admin_debug_identity_replay_jobs_enqueue(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgLinkReplayJobEnqueueRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobEnqueueResponse:
        assert_tenant(db, tenant_id)
        from app.tasks.cortex_org_link_jobs import run_org_link_replay_job_task
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            create_queued_org_link_replay_job,
            org_link_replay_job_public_dict,
        )

        scope = dict(body.scope_json or {})
        if body.job_kind in WAVE2_COLLAPSED_REPLAY_JOB_KINDS_V1:
            scope[DEBUG_FULL_SUBSTRATE_REFRESH_ACK_KEY_V1] = True
        job = create_queued_org_link_replay_job(
            db,
            tenant_id=tenant_id,
            job_kind=body.job_kind,
            pinned_rule_version=body.pinned_rule_version,
            dry_run=body.dry_run,
            scope_json=scope,
        )
        db.flush()
        try:
            async_result = run_org_link_replay_job_task.delay(
                str(tenant_id),
                body.job_kind,
                body.pinned_rule_version,
                body.dry_run,
                scope,
                str(job.id),
            )
        except Exception as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"celery_enqueue_failed:{exc}",
            ) from exc
        job.celery_task_id = str(async_result.id)
        db.commit()
        db.refresh(job)
        worker_path = f"/admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{async_result.id}"
        return AdminCortexOrgLinkReplayJobEnqueueResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            celery_task_id=str(async_result.id),
            worker_task_status_path=worker_path,
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/debug/identity/full-substrate-refresh",
        tags=["cortex-debug"],
    )
    def admin_debug_full_substrate_refresh(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        bundle_id: Annotated[str, Query(min_length=1)],
        debug_acknowledged: Annotated[bool, Query()] = False,
        materialize_batch_limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
        anchor_limit: Annotated[int, Query(ge=1, le=50_000)] = 5000,
        dry_run: Annotated[bool, Query()] = False,
    ) -> dict:
        assert_tenant(db, tenant_id)
        if not debug_acknowledged:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="debug_acknowledged_required_for_full_substrate_refresh",
            )
        try:
            out = run_debug_full_substrate_refresh_v1(
                db,
                tenant_id=tenant_id,
                bundle_id=bundle_id.strip(),
                materialize_batch_limit=materialize_batch_limit,
                anchor_limit=anchor_limit,
                dry_run=dry_run,
                debug_acknowledged=True,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        db.commit()
        return {
            "surface_kind": DEBUG_FULL_SUBSTRATE_REFRESH_SURFACE_KIND_V1,
            "tenant_id": str(tenant_id),
            "result": out,
            "warning": "Non-authoritative debug path — prefer operator rebuild_identities (reset + dirty).",
        }
