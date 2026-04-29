"""Password reset HTTP routes (no email delivery)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_forgot_password_returns_generic_ok(client: TestClient) -> None:
    r = client.post("/auth/forgot-password", json={"email": "not-registered@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "account" in body["detail"].lower()


def test_reset_password_rejects_bad_token(client: TestClient) -> None:
    r = client.post(
        "/auth/reset-password",
        json={"token": "not-a-valid-reset-token-string", "password": "newpassword123"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid or expired reset link."


def test_reset_password_rejects_weak_password(client: TestClient) -> None:
    r = client.post(
        "/auth/reset-password",
        json={"token": "not-a-valid-reset-token-string", "password": "short"},
    )
    assert r.status_code == 422
