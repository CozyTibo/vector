"""Integration: POST /onboarding/restart clears answers and chat; auth required."""

from __future__ import annotations

import json
import uuid

import pytest
from starlette.testclient import TestClient

from vector.domains.onboarding.constants import (
    PROFILE_PHASE_NAME,
    STATUS_IN_PROGRESS,
    STEP_CHAT_PROFILE,
)

pytestmark = pytest.mark.integration


def test_onboarding_restart_requires_session(client: TestClient) -> None:
    assert client.post("/onboarding/restart").status_code == 401


def test_onboarding_restart_clears_answers_and_step(client: TestClient) -> None:
    email = f"ob-restart-{uuid.uuid4().hex[:12]}@example.com"
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secure-pass-1",
            "full_name": "Restart User",
            "company_name": "Restart Co",
        },
    )
    assert reg.status_code == 200

    patched = client.patch(
        "/onboarding",
        json={
            "current_step": "SLACK_STAKEHOLDERS",
            "answers": {"profile_phase": "tools", "company": {"name": "Acme"}},
        },
    )
    assert patched.status_code == 200
    body_before = patched.json()
    assert body_before["current_step"] == "SLACK_STAKEHOLDERS"
    assert body_before["answers"].get("company", {}).get("name") == "Acme"

    restart = client.post("/onboarding/restart")
    assert restart.status_code == 200
    data = restart.json()
    assert data["status"] == STATUS_IN_PROGRESS
    assert data["current_step"] == STEP_CHAT_PROFILE
    assert data["answers"] == {"profile_phase": PROFILE_PHASE_NAME}
    assert data.get("messages") == []

    loaded = client.get("/onboarding")
    assert loaded.status_code == 200
    again = loaded.json()
    assert again["current_step"] == STEP_CHAT_PROFILE
    assert again["answers"] == {"profile_phase": PROFILE_PHASE_NAME}


def test_patch_admin_access_with_slack_stakeholders_appends_user_chat_line(client: TestClient) -> None:
    """PATCH to ADMIN_ACCESS with slack_stakeholders should persist a user row for the chat transcript."""
    email = f"ob-stakeholders-{uuid.uuid4().hex[:12]}@example.com"
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secure-pass-1",
            "full_name": "Stake User",
            "company_name": "Stake Co",
        },
    )
    assert reg.status_code == 200

    to_stakeholders = client.patch(
        "/onboarding",
        json={
            "current_step": "SLACK_STAKEHOLDERS",
            "answers": {"profile_phase": "done"},
        },
    )
    assert to_stakeholders.status_code == 200

    to_admin = client.patch(
        "/onboarding",
        json={
            "current_step": "ADMIN_ACCESS",
            "answers": {
                "slack_stakeholders": {
                    "raw_text": "@Tibo",
                    "slack_user_ids": ["U0AR67MHXLG"],
                    "mention_labels": ["Tibo"],
                }
            },
        },
    )
    assert to_admin.status_code == 200
    msgs = to_admin.json().get("messages") or []
    user_lines = [m["content"] for m in msgs if m.get("role") == "user"]
    assert "@Tibo" in user_lines


def test_patch_slack_collaborators_confirm_appends_structured_json(client: TestClient) -> None:
    """Collaborator picks are logged when entering confirm (same UX pattern as tools_selected)."""
    email = f"ob-collab-chat-{uuid.uuid4().hex[:12]}@example.com"
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secure-pass-1",
            "full_name": "Collab User",
            "company_name": "Collab Co",
        },
    )
    assert reg.status_code == 200

    assert (
        client.patch(
            "/onboarding",
            json={"current_step": "SLACK_STAKEHOLDERS", "answers": {"profile_phase": "done"}},
        ).status_code
        == 200
    )

    to_confirm = client.patch(
        "/onboarding",
        json={
            "current_step": "SLACK_COLLABORATORS_CONFIRM",
            "answers": {
                "slack_stakeholders": {
                    "raw_text": "@ada",
                    "slack_user_ids": ["UADA"],
                    "mention_labels": ["Ada"],
                },
                "slack_collaborators": {
                    "members": [
                        {"slack_user_id": "UADA", "username": "ada", "label": "Ada"},
                        {"slack_user_id": "UBOB", "username": "bob", "label": "Bob"},
                    ]
                },
            },
        },
    )
    assert to_confirm.status_code == 200
    msgs = to_confirm.json().get("messages") or []
    user_lines = [m["content"] for m in msgs if m.get("role") == "user"]
    coll_row = next(
        (c for c in user_lines if c.strip().startswith("{") and "slack_collaborators_selected" in c),
        None,
    )
    assert coll_row is not None
    data = json.loads(coll_row)
    assert data["type"] == "slack_collaborators_selected"
    assert [m["username"] for m in data["members"]] == ["ada", "bob"]
