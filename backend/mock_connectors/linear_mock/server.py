"""Linear OAuth + GraphQL HTTP handlers (wired from unified app)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mock_connectors.linear_mock import dataset_generator as lg


def build_linear_router(get_linear: Callable[[], dict[str, Any]]) -> APIRouter:
    r = APIRouter()

    @r.post("/oauth/token")
    async def oauth_token(request: Request) -> JSONResponse:
        form = await request.form()
        grant_type = str(form.get("grant_type") or "")
        if grant_type not in ("authorization_code", "refresh_token"):
            return JSONResponse({"error": "unsupported_grant"}, status_code=400)
        return JSONResponse(
            {
                "access_token": "mock-linear-access-token",
                "token_type": "Bearer",
                "expires_in": 86400,
                "scope": "read write",
                "refresh_token": "mock-linear-refresh-token",
            },
        )

    @r.post("/graphql")
    def graphql(body: dict[str, Any]) -> JSONResponse:
        linear = get_linear()
        payload = lg.handle_graphql(linear, body if isinstance(body, dict) else {})
        return JSONResponse(payload)

    return r
