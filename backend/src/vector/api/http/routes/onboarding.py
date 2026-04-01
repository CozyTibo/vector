"""Design-partner onboarding — state in onboarding_state; connectors unchanged."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims
from vector.contracts.onboarding import (
    OnboardingChatRequest,
    OnboardingChatResponse,
    OnboardingCompleteResponse,
    OnboardingGetResponse,
    OnboardingMessageItem,
    OnboardingPatchBody,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.constants import ONBOARDING_STEPS, STATUS_COMPLETED, STEP_THANK_YOU
from vector.domains.onboarding.onboarding_service import process_onboarding_chat
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.infrastructure.db.repositories import onboarding as ob_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def _load_onboarding_messages(db: Session, tenant_id: uuid.UUID) -> list[OnboardingMessageItem]:
    if not ob_repo.onboarding_messages_table_exists(db):
        return []
    rows = ob_repo.list_onboarding_messages_chronological(db, tenant_id, limit=200)
    return [
        OnboardingMessageItem(
            id=r.id,
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in rows
    ]


def _row_to_response(
    row: OnboardingState,
    *,
    github_connected: bool,
    linear_connected: bool,
    messages: list[OnboardingMessageItem],
) -> OnboardingGetResponse:
    return OnboardingGetResponse(
        id=row.id,
        status=row.status,
        current_step=row.current_step,
        answers=dict(row.answers_json or {}),
        version=row.version,
        started_at=row.started_at,
        completed_at=row.completed_at,
        abandoned_at=row.abandoned_at,
        messages=messages,
        github_connected=github_connected,
        linear_connected=linear_connected,
    )


def _apply_profile_patch(session: Session, user_id: uuid.UUID, patch: dict[str, Any]) -> None:
    nested = patch.get("profile")
    if not isinstance(nested, dict):
        return
    raw = nested.get("name")
    if not isinstance(raw, str):
        return
    name = raw.strip()
    if not name:
        return
    user = tenancy_repo.get_user_by_id(session, user_id)
    if user is None:
        return
    user.full_name = name


def _apply_company_patch(session: Session, tenant_id: uuid.UUID, patch: dict[str, Any]) -> None:
    tenant = tenancy_repo.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        return
    raw = patch.get("company_name")
    if isinstance(raw, str):
        name = raw.strip()
        if name:
            tenant.company_name = name
    nested = patch.get("company")
    if isinstance(nested, dict):
        n = nested.get("name")
        if isinstance(n, str):
            name2 = n.strip()
            if name2:
                tenant.company_name = name2


def build_onboarding_router() -> APIRouter:
    r = APIRouter(prefix="/onboarding", tags=["onboarding"])

    @r.get("", response_model=OnboardingGetResponse)
    def get_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingGetResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
        db.commit()
        db.refresh(row)
        gh = gh_repo.get_github_connection_for_tenant(db, claims.tenant_id)
        lin = linear_repo.get_linear_connection_for_tenant(db, claims.tenant_id)
        msgs = _load_onboarding_messages(db, claims.tenant_id)
        return _row_to_response(
            row,
            github_connected=gh is not None,
            linear_connected=lin is not None,
            messages=msgs,
        )

    @r.patch("", response_model=OnboardingGetResponse)
    def patch_onboarding(
        body: OnboardingPatchBody,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingGetResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
        if row.status == STATUS_COMPLETED:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Onboarding already completed.",
            ) from None
        if body.current_step is not None:
            if body.current_step not in ONBOARDING_STEPS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid current_step: {body.current_step!r}.",
                ) from None
            row.current_step = body.current_step
        if body.answers is not None:
            row.answers_json = ob_repo.deep_merge_answers_json(row.answers_json or {}, body.answers)
            _apply_profile_patch(db, claims.user_id, body.answers)
            _apply_company_patch(db, claims.tenant_id, body.answers)
        row.version = int(row.version) + 1
        db.commit()
        db.refresh(row)
        gh = gh_repo.get_github_connection_for_tenant(db, claims.tenant_id)
        lin = linear_repo.get_linear_connection_for_tenant(db, claims.tenant_id)
        msgs = _load_onboarding_messages(db, claims.tenant_id)
        return _row_to_response(
            row,
            github_connected=gh is not None,
            linear_connected=lin is not None,
            messages=msgs,
        )

    @r.post("/chat", response_model=OnboardingChatResponse)
    def post_onboarding_chat(
        body: OnboardingChatRequest,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingChatResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        return process_onboarding_chat(db, claims, body)

    @r.post("/complete", response_model=OnboardingCompleteResponse)
    def complete_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingCompleteResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
        now = datetime.now(UTC)
        if row.status != STATUS_COMPLETED:
            row.status = STATUS_COMPLETED
            row.current_step = STEP_THANK_YOU
            row.completed_at = now
            row.version = int(row.version) + 1
            db.commit()
        db.refresh(row)
        return OnboardingCompleteResponse(
            status=row.status,
            current_step=row.current_step,
            completed_at=row.completed_at or now,
        )

    return r
