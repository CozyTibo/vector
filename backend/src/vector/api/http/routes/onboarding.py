"""Design-partner onboarding — thin HTTP over ``vector.domains.onboarding`` commands."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims
from vector.contracts.onboarding import (
    OnboardingChatRequest,
    OnboardingChatResponse,
    OnboardingCompleteResponse,
    OnboardingGetResponse,
    OnboardingPatchBody,
    SlackChannelsResponse,
    SlackMembersResponse,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.errors import (
    InvalidOnboardingStepError,
    OnboardingAlreadyCompletedError,
    SlackMembersLoadError,
    SlackNotConnectedForWorkspaceError,
)
from vector.domains.onboarding.onboarding_commands import (
    complete_onboarding as ob_complete_onboarding,
)
from vector.domains.onboarding.onboarding_commands import (
    get_onboarding_state as ob_get_onboarding_state,
)
from vector.domains.onboarding.onboarding_commands import (
    list_slack_workspace_channels_for_onboarding as ob_list_slack_workspace_channels,
)
from vector.domains.onboarding.onboarding_commands import (
    list_slack_workspace_members_for_onboarding as ob_list_slack_workspace_members,
)
from vector.domains.onboarding.onboarding_commands import (
    patch_onboarding as ob_patch_onboarding,
)
from vector.domains.onboarding.onboarding_commands import (
    restart_onboarding as ob_restart_onboarding,
)
from vector.domains.onboarding.onboarding_service import process_onboarding_chat


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
        return ob_get_onboarding_state(db, claims)

    @r.post("/restart", response_model=OnboardingGetResponse)
    def restart_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingGetResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        return ob_restart_onboarding(db, claims)

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
        try:
            return ob_patch_onboarding(db, claims, body)
        except OnboardingAlreadyCompletedError as e:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Onboarding already completed.",
            ) from e
        except InvalidOnboardingStepError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid current_step: {e.step!r}.",
            ) from e

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

    @r.get("/slack-members", response_model=SlackMembersResponse)
    def get_slack_workspace_members(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> SlackMembersResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            return ob_list_slack_workspace_members(db, claims)
        except SlackNotConnectedForWorkspaceError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Slack is not connected for this workspace.",
            ) from None
        except SlackMembersLoadError as e:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=e.message,
            ) from e

    @r.get("/slack-channels", response_model=SlackChannelsResponse)
    def get_slack_workspace_channels(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> SlackChannelsResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            return ob_list_slack_workspace_channels(db, claims)
        except SlackNotConnectedForWorkspaceError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Slack is not connected for this workspace.",
            ) from None
        except SlackMembersLoadError as e:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=e.message,
            ) from e

    @r.post("/complete", response_model=OnboardingCompleteResponse)
    def complete_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingCompleteResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        return ob_complete_onboarding(db, claims)

    return r
