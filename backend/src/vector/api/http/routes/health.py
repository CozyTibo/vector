"""Health endpoint (ALB/ECS, probes) — includes DB connectivity."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from vector.infrastructure.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def health_check() -> dict[str, str] | JSONResponse:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
    return {"status": "ok"}
