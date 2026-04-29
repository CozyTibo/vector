"""Product auth: OAuth (Google) + email/password — thin routes."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from vector.api.http.cookie_utils import clear_session_cookie, set_session_cookie
from vector.api.http.deps import get_db, settings_dep
from vector.contracts.auth_payloads import (
    AuthOkResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from vector.domains.identity_access.errors import (
    EmailAlreadyRegisteredError,
    GoogleOAuthError,
    InvalidCredentialsError,
    InvalidOAuthStateError,
    InvalidPasswordResetTokenError,
    OAuthNotConfiguredError,
    WeakPasswordError,
)
from vector.domains.identity_access.services.auth_flow import (
    complete_google_oauth,
    start_google_oauth,
)
from vector.domains.identity_access.services.local_auth import (
    login_with_email_password,
    register_with_email_password,
)
from vector.domains.identity_access.services.password_reset import (
    request_password_reset,
    reset_password_with_token,
)
from vector.infrastructure.email.waitlist_confirmation import enqueue_waitlist_signup_confirmation
from vector.settings import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthOkResponse)
def register_email_password(
    request: Request,
    body: RegisterRequest,
    settings: Annotated[Settings, Depends(settings_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    try:
        token = register_with_email_password(
            db,
            settings,
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
            company_name=body.company_name,
        )
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e
    except WeakPasswordError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    enqueue_waitlist_signup_confirmation(str(body.email), body.full_name)
    resp = JSONResponse(content=AuthOkResponse(session_token=token).model_dump())
    set_session_cookie(resp, settings, token, request=request)
    return resp


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    settings: Annotated[Settings, Depends(settings_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> ForgotPasswordResponse:
    request_password_reset(db, settings, email=str(body.email))
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ResetPasswordResponse:
    try:
        reset_password_with_token(db, token=body.token, new_password=body.password)
    except InvalidPasswordResetTokenError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        ) from e
    except WeakPasswordError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return ResetPasswordResponse()


@router.post("/login", response_model=AuthOkResponse)
def login_email_password(
    request: Request,
    body: LoginRequest,
    settings: Annotated[Settings, Depends(settings_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    try:
        token = login_with_email_password(
            db,
            settings,
            email=str(body.email),
            password=body.password,
        )
    except InvalidCredentialsError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    resp = JSONResponse(content=AuthOkResponse(session_token=token).model_dump())
    set_session_cookie(resp, settings, token, request=request)
    return resp


@router.get("/google/start")
def google_oauth_start(
    settings: Annotated[Settings, Depends(settings_dep)],
) -> RedirectResponse:
    try:
        started = start_google_oauth(settings)
    except OAuthNotConfiguredError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    response = RedirectResponse(url=started.redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=settings.oauth_state_cookie_name,
        value=started.oauth_cookie_value,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/google/callback")
def google_oauth_callback(
    request: Request,
    settings: Annotated[Settings, Depends(settings_dep)],
    db: Annotated[Session, Depends(get_db)],
    code: str,
    state: str,
) -> RedirectResponse:
    cookie_raw = request.cookies.get(settings.oauth_state_cookie_name)
    front = settings.frontend_url.rstrip("/")
    try:
        token = complete_google_oauth(
            db,
            settings,
            code=code,
            state=state,
            oauth_cookie_raw=cookie_raw,
        )
    except InvalidOAuthStateError:
        dest = f"{front}/?oauth_error=state"
        return RedirectResponse(url=dest, status_code=status.HTTP_302_FOUND)
    except GoogleOAuthError:
        dest = f"{front}/?oauth_error=token"
        return RedirectResponse(url=dest, status_code=status.HTTP_302_FOUND)
    # Fragment: SPA can persist JWT when session cookie is not stored (cross-site / ITP).
    dest = f"{front}/?oauth_ok=1#st={quote(token, safe='')}"
    response = RedirectResponse(url=dest, status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, settings, token, request=request)
    response.delete_cookie(key=settings.oauth_state_cookie_name, path="/")
    return response


@router.post("/logout")
def logout(
    request: Request,
    settings: Annotated[Settings, Depends(settings_dep)],
) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings, request=request)
    return response
