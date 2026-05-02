"""§6 Step 36 — admin GET fetch-debug forwards `skip_interpretations` / `skip_insights` to the orchestrator."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from vector.api.http.deps import get_db
from vector.api.http.main import app
from vector.settings import get_settings


def _minimal_fetch_debug_response() -> Any:
    """Load the Step 3 contract helper (same object shape as real fetch-debug)."""
    fixture_path = (
        Path(__file__).resolve().parents[2] / "contracts" / "test_fetch_debug_response_step3.py"
    )
    spec = importlib.util.spec_from_file_location("_fetch_debug_step3_contracts", fixture_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load fixture module: {fixture_path}"
        raise RuntimeError(msg)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._minimal_fetch_debug_response()


def test_admin_fetch_debug_forwards_skip_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/step36_admin_fetch_debug_test")
    monkeypatch.setenv("ADMIN_PASSWORD", "step36-admin-fetch-debug-password")
    get_settings.cache_clear()

    mock_session = MagicMock()
    tenant_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    def override_db() -> Any:
        yield mock_session

    captured: dict[str, Any] = {}

    def fake_run(_session: Any, _settings: Any, *, tenant_id: uuid.UUID, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _minimal_fetch_debug_response()

    monkeypatch.setattr(
        "vector.api.http.routes.admin.tenancy_repo.get_tenant_by_id",
        lambda *_a, **_k: object(),
    )
    monkeypatch.setattr(
        "vector.api.http.routes.admin.run_manager_insights_fetch_debug",
        fake_run,
    )

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        r = client.get(
            f"/admin/tenants/{tenant_id}/manager-insight/fetch-debug",
            auth=("x", "step36-admin-fetch-debug-password"),
            params={"skip_interpretations": 1, "skip_insights": 1},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert captured.get("skip_interpretations") is True
    assert captured.get("skip_insights") is True
