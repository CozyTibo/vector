"""Liveness endpoint (readiness can query DB when wired)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}
