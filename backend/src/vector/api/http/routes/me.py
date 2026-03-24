"""Current session / tenant context."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims
from vector.contracts.me import MeResponse
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import build_me_response
from vector.domains.identity_access.services.session_jwt import SessionClaims

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
def read_me(
    db: Annotated[Session, Depends(get_db)],
    claims: Annotated[SessionClaims, Depends(get_session_claims)],
) -> MeResponse:
    try:
        return build_me_response(db, claims)
    except NoMembershipError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
