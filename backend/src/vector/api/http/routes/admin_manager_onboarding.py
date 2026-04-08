"""Admin HTTP API for Manager Slack onboarding."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

log = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vector.api.http.admin_deps import require_admin_basic
from vector.api.http.deps import get_db
from vector.domains.manager_onboarding.constants import (
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_NEEDS_REVIEW,
    STATUS_PAUSED,
    STATUS_WAITING_FOR_USER,
    STEP_COMPLETED,
    STEP_ORDER,
)
from vector.domains.manager_onboarding.service import (
    admin_apply_recompute_current_step,
    admin_force_complete,
    admin_mark_needs_review,
    admin_merge_answers,
    admin_restart_at_step,
    admin_retry_slack_prompt,
    admin_set_session_muted,
    admin_wipe_session_restart,
    reconcile_needs_review_if_manager_flow_complete,
)
from vector.domains.manager_onboarding.slack_admin_display import (
    build_slack_label_maps_for_admin,
    collect_slack_channel_ids_from_answers,
    collect_slack_user_ids_from_answers,
    enrich_slack_dm_text_for_admin,
    resolve_slack_channel_labels_for_session,
    resolve_slack_user_labels_for_ids,
)
from vector.infrastructure.db.models.manager_onboarding_session import ManagerOnboardingSession
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_onboarding as mo_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

_VALID_RESTART_STEPS = frozenset(s for s in STEP_ORDER if s != STEP_COMPLETED)

_MANAGER_OB_IN_PROGRESS = frozenset({STATUS_ACTIVE, STATUS_WAITING_FOR_USER})
_MANAGER_OB_NEEDS_ATTENTION = frozenset({STATUS_PAUSED, STATUS_FAILED, STATUS_NEEDS_REVIEW})


def _manager_onboarding_rollup_counts(
    sessions: list[ManagerOnboardingSession],
) -> dict[str, int]:
    """Business-facing counts: one session row ≈ one manager in Slack onboarding.

    **In progress** = ``active`` or ``waiting_for_user`` (conversation still running).

    **Needs follow-up** = ``needs_review``, ``paused``, or ``failed`` (not based on idle time).
    """
    total = len(sessions)
    completed = sum(1 for s in sessions if s.status == STATUS_COMPLETED)
    in_progress = sum(1 for s in sessions if s.status in _MANAGER_OB_IN_PROGRESS)
    needs_attention = sum(1 for s in sessions if s.status in _MANAGER_OB_NEEDS_ATTENTION)
    accounted = completed + in_progress + needs_attention
    if accounted < total:
        needs_attention += total - accounted
    return {
        "managers_with_sessions": total,
        "managers_completed": completed,
        "managers_in_progress": in_progress,
        "managers_needs_attention": needs_attention,
    }


def _session_or_404(db: Session, session_id: uuid.UUID) -> ManagerOnboardingSession:
    row = db.get(ManagerOnboardingSession, session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found") from None
    return row


def _attach_slack_answer_labels(db: Session, row: ManagerOnboardingSession, out: dict[str, Any]) -> None:
    uid_set = collect_slack_user_ids_from_answers(dict(row.answers_json or {}))
    su = (row.slack_user_id or "").strip().upper()
    if su:
        uid_set.add(su)
    out["slack_user_labels"] = resolve_slack_user_labels_for_ids(db, row.tenant_id, uid_set)
    cid_set = collect_slack_channel_ids_from_answers(dict(row.answers_json or {}))
    out["slack_channel_labels"] = resolve_slack_channel_labels_for_session(
        db,
        row.tenant_id,
        row.id,
        cid_set,
    )


def _session_dict(row: ManagerOnboardingSession) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "slack_team_id": row.slack_team_id,
        "slack_user_id": row.slack_user_id,
        "app_user_id": str(row.app_user_id) if row.app_user_id else None,
        "parent_session_id": str(row.parent_session_id) if row.parent_session_id else None,
        "status": row.status,
        "current_step": row.current_step,
        "muted": bool(row.muted),
        "answers_json": row.answers_json,
        "context_json": row.context_json,
        "version": row.version,
        "error_code": row.error_code,
        "error_detail": row.error_detail,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


class PatchManagerOnboardingSessionBody(BaseModel):
    answers_patch: dict[str, Any] | None = None
    muted: bool | None = None
    current_step: str | None = None
    recompute_current_step: bool = False


class RestartStepBody(BaseModel):
    step: str = Field(..., min_length=1, max_length=64)


class SlackOnboardingPolicyBody(BaseModel):
    slack_vector_paused: bool | None = None


def build_admin_manager_onboarding_router() -> APIRouter:
    r = APIRouter(
        prefix="/manager-onboarding",
        tags=["admin-manager-onboarding"],
        dependencies=[Depends(require_admin_basic)],
    )

    @r.get("/sessions")
    def list_manager_onboarding_sessions(
        db: Annotated[Session, Depends(get_db)],
        tenant_id: Annotated[uuid.UUID | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ) -> dict[str, Any]:
        if tenant_id is not None:
            rows = mo_repo.list_sessions_for_tenant(db, tenant_id, limit=limit)
        else:
            rows = mo_repo.list_all_sessions(db, limit=limit)
        return {
            "items": [
                {
                    "id": str(s.id),
                    "tenant_id": str(s.tenant_id),
                    "slack_team_id": s.slack_team_id,
                    "slack_user_id": s.slack_user_id,
                    "status": s.status,
                    "current_step": s.current_step,
                    "muted": bool(s.muted),
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in rows
            ]
        }

    @r.get("/sessions/{session_id}")
    def get_manager_onboarding_session(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        out = _session_dict(row)
        _attach_slack_answer_labels(db, row, out)
        return out

    @r.patch("/sessions/{session_id}")
    def patch_manager_onboarding_session(
        session_id: uuid.UUID,
        body: PatchManagerOnboardingSessionBody,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        recompute_info: dict[str, Any] | None = None
        if body.answers_patch is not None:
            admin_merge_answers(row, body.answers_patch)
        if body.muted is not None:
            admin_set_session_muted(row, body.muted)
        if body.current_step is not None:
            ok_step = body.current_step in _VALID_RESTART_STEPS
            if not ok_step and body.current_step != STEP_COMPLETED:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Invalid current_step.",
                ) from None
            row.current_step = body.current_step
        if body.recompute_current_step:
            link = slack_repo.get_slack_connection_for_tenant(db, row.tenant_id)
            tok = ((link.detail.bot_access_token or "").strip()) if link else ""
            recompute_info = admin_apply_recompute_current_step(db, row, bot_token=tok or None)
        reconcile_needs_review_if_manager_flow_complete(row)
        db.flush()
        out = _session_dict(row)
        _attach_slack_answer_labels(db, row, out)
        if recompute_info is not None:
            out["recompute"] = recompute_info
        return out

    @r.post("/sessions/{session_id}/admin-wipe-restart")
    def wipe_manager_onboarding_session(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        admin_wipe_session_restart(db, row)
        db.flush()
        slack_out: dict[str, Any] | None = None
        link = slack_repo.get_slack_connection_for_tenant(db, row.tenant_id)
        tok = ((link.detail.bot_access_token or "").strip()) if link else ""
        if tok:
            try:
                slack_out = admin_retry_slack_prompt(db, tok, row)
            except Exception as e:
                log.exception("admin wipe: Slack intro resend failed session=%s", row.id)
                slack_out = {"ok": False, "error": str(e)}
        else:
            slack_out = {"ok": False, "error": "no_slack_connection"}
        db.flush()
        out = _session_dict(row)
        _attach_slack_answer_labels(db, row, out)
        out["slack"] = slack_out
        return out

    @r.post("/sessions/{session_id}/restart-step")
    def restart_manager_onboarding_step(
        session_id: uuid.UUID,
        body: RestartStepBody,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        if body.step not in _VALID_RESTART_STEPS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"step must be one of: {', '.join(sorted(_VALID_RESTART_STEPS))}",
            ) from None
        try:
            admin_restart_at_step(row, body.step)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        db.flush()
        return _session_dict(row)

    @r.post("/sessions/{session_id}/force-complete")
    def force_complete_manager_onboarding(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        admin_force_complete(row)
        db.flush()
        return _session_dict(row)

    @r.post("/sessions/{session_id}/needs-review")
    def mark_manager_onboarding_needs_review(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        admin_mark_needs_review(row)
        db.flush()
        return _session_dict(row)

    @r.post("/sessions/{session_id}/retry-slack-prompt")
    def retry_manager_onboarding_slack_prompt(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        row = _session_or_404(db, session_id)
        link = slack_repo.get_slack_connection_for_tenant(db, row.tenant_id)
        if link is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="No Slack connection for tenant.",
            ) from None
        tok = link.detail.bot_access_token
        out = admin_retry_slack_prompt(db, tok, row)
        db.flush()
        return out

    @r.get("/sessions/{session_id}/parse-artifacts")
    def list_manager_onboarding_parse_artifacts(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> dict[str, Any]:
        _session_or_404(db, session_id)
        rows = mo_repo.list_parse_artifacts_for_session(db, session_id, limit=limit)
        return {
            "items": [
                {
                    "id": str(a.id),
                    "trigger": a.trigger,
                    "input_text": a.input_text,
                    "structured_output_json": a.structured_output_json,
                    "confidence": a.confidence,
                    "model": a.model,
                    "token_usage": a.token_usage,
                    "fallback_attempts": a.fallback_attempts,
                    "error": a.error,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in rows
            ]
        }

    @r.get("/sessions/{session_id}/messages")
    def list_manager_onboarding_messages(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    ) -> dict[str, Any]:
        sess = _session_or_404(db, session_id)
        rows = mo_repo.list_messages_chronological(db, session_id, limit=limit)
        texts = [m.text for m in rows]
        ch_map, u_map = build_slack_label_maps_for_admin(
            db,
            tenant_id=sess.tenant_id,
            texts=texts,
            session_slack_user_id=sess.slack_user_id or "",
        )
        return {
            "items": [
                {
                    "id": str(m.id),
                    "direction": m.direction,
                    "role": m.role,
                    "text": enrich_slack_dm_text_for_admin(
                        m.text,
                        channel_labels=ch_map,
                        user_labels=u_map,
                    ),
                    "slack_channel_id": m.slack_channel_id,
                    "slack_ts": m.slack_ts,
                    "thread_ts": m.thread_ts,
                    "slack_event_id": m.slack_event_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in rows
            ]
        }

    return r


def build_admin_manager_onboarding_tenant_router() -> APIRouter:
    r = APIRouter(
        prefix="/tenants",
        tags=["admin-manager-onboarding"],
        dependencies=[Depends(require_admin_basic)],
    )

    @r.get("/{tenant_id}/manager-onboarding/summary")
    def manager_onboarding_tenant_summary(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        session_limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ) -> dict[str, Any]:
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found") from None
        sessions = mo_repo.list_sessions_for_tenant(db, tenant_id, limit=session_limit)
        for s in sessions:
            reconcile_needs_review_if_manager_flow_complete(s)
        db.flush()
        roll = _manager_onboarding_rollup_counts(sessions)
        uids: set[str] = set()
        for s in sessions:
            u = (s.slack_user_id or "").strip().upper()
            if u:
                uids.add(u)
        slack_labels = resolve_slack_user_labels_for_ids(db, tenant_id, uids)
        return {
            "tenant_id": str(tenant_id),
            "slack_vector_paused": bool(t.slack_vector_paused),
            "session_count": len(sessions),
            "managers_with_sessions": roll["managers_with_sessions"],
            "managers_completed": roll["managers_completed"],
            "managers_in_progress": roll["managers_in_progress"],
            "managers_needs_attention": roll["managers_needs_attention"],
            "invitation_count": mo_repo.count_invitations_for_tenant(db, tenant_id),
            "sessions": [
                {
                    "id": str(s.id),
                    "slack_user_id": s.slack_user_id,
                    "slack_display_name": slack_labels.get((s.slack_user_id or "").strip().upper()),
                    "status": s.status,
                    "current_step": s.current_step,
                    "muted": bool(s.muted),
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ],
        }

    @r.get("/{tenant_id}/manager-onboarding/channels")
    def manager_onboarding_tenant_channels(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found") from None
        rows = mo_repo.list_channel_observations_for_tenant(db, tenant_id, limit=limit)
        return {
            "items": [
                {
                    "session_id": str(o.session_id),
                    "slack_channel_id": o.slack_channel_id,
                    "channel_name": o.channel_name,
                    "access_status": o.access_status,
                    "bot_is_member": o.bot_is_member,
                    "history_readable": o.history_readable,
                    "validation_error": o.validation_error,
                }
                for o in rows
            ],
        }

    @r.patch("/{tenant_id}/manager-onboarding/slack-policy")
    def patch_manager_onboarding_slack_policy(
        tenant_id: uuid.UUID,
        body: SlackOnboardingPolicyBody,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        t = db.get(Tenant, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found") from None
        if body.slack_vector_paused is not None:
            t.slack_vector_paused = body.slack_vector_paused
        db.flush()
        return {
            "tenant_id": str(tenant_id),
            "slack_vector_paused": bool(t.slack_vector_paused),
        }

    return r
