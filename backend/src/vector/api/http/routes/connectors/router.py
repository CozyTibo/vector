"""Factory: /connectors aggregate routes + per-provider sub-routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.api.http.routes.connectors import github as github_connect
from vector.api.http.routes.connectors import linear as linear_connect
from vector.api.http.routes.connectors import notion as notion_connect
from vector.api.http.routes.connectors import slack as slack_connect
from vector.api.http.routes.connectors import calls as calls_connect
from vector.contracts.connectors import ConnectorsListResponse
from vector.domains.connectors.runtime import all_runtimes_ordered, runtime_by_id
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.settings import Settings


def build_connectors_router() -> APIRouter:
    root = APIRouter(prefix="/connectors", tags=["connectors"])
    providers = runtime_by_id()

    @root.get("", response_model=ConnectorsListResponse)
    def list_connectors(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> ConnectorsListResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        items = [
            rt.status_for_tenant(db, settings, claims.tenant_id)
            for rt in all_runtimes_ordered()
        ]
        return ConnectorsListResponse(items=items)

    @root.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
    def disconnect_connector(
        provider_id: str,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> Response:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        runtime = providers.get(provider_id)
        if runtime is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Unknown connector provider.",
            ) from None
        runtime.disconnect_tenant(db, claims.tenant_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    root.include_router(github_connect.build_github_connector_router(), prefix="/github")
    root.include_router(linear_connect.build_linear_connector_router(), prefix="/linear")
    root.include_router(notion_connect.build_notion_connector_router(), prefix="/notion")
    root.include_router(calls_connect.build_calls_connector_router(), prefix="/calls")
    root.include_router(slack_connect.build_slack_connector_router(), prefix="/slack")
    return root
