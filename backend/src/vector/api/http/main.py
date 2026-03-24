"""ASGI application entry."""

from __future__ import annotations

from fastapi import FastAPI

from vector.api.http.routes import health

app = FastAPI(title="Vector", version="0.1.0")
app.include_router(health.router, prefix="/health", tags=["health"])
