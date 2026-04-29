"""Request bodies for auth routes."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthOkResponse(BaseModel):
    status: str = "ok"
    session_token: str | None = Field(
        default=None,
        description="Session JWT; use Authorization Bearer when cross-site cookies fail.",
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Generic message (does not reveal whether the email is registered)."""

    status: str = "ok"
    detail: str = "If an account exists for that email, we sent password reset instructions."


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    password: str = Field(min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    status: str = "ok"
    detail: str = "Your password has been updated. You can sign in."
