"""Tests for Manager insights Step 1 fetch bundle assembly."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from vector.contracts.manager_insights_activity import ConnectorFetchResult
from vector.domains.manager_insights import fetch_activity as mod


def _fake_result(connector: str, *, window_start: datetime, window_end: datetime) -> ConnectorFetchResult:
    return ConnectorFetchResult(
        connector=connector,  # type: ignore[arg-type]
        status="ok",
        fetched_at=window_end,
        window_start=window_start,
        window_end=window_end,
        caps_applied=[],
        errors=[],
        payload={"probe": True},
    )


def test_run_fetch_activity_bundle_includes_all_connectors(monkeypatch: Any) -> None:
    fixed_end = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
    tenant_id = uuid.uuid4()

    def _patch(connector: str):
        def _fn(*args: Any, **kwargs: Any) -> ConnectorFetchResult:
            return _fake_result(
                connector,
                window_start=kwargs["window_start"],
                window_end=kwargs["window_end"],
            )

        return _fn

    monkeypatch.setattr(mod, "_fetch_slack", _patch("slack"))
    monkeypatch.setattr(mod, "_fetch_github", _patch("github"))
    monkeypatch.setattr(mod, "_fetch_linear", _patch("linear"))
    monkeypatch.setattr(mod, "_fetch_notion", _patch("notion"))
    monkeypatch.setattr(mod, "_fetch_calls", _patch("calls"))

    bundle = mod.run_fetch_activity_bundle(
        session=object(),  # type: ignore[arg-type]
        settings=SimpleNamespace(),
        tenant_id=tenant_id,
        window_days=30,
        as_of=fixed_end,
    )
    assert bundle.tenant_id == tenant_id
    assert sorted(bundle.connectors.keys()) == ["calls", "github", "linear", "notion", "slack"]
    assert bundle.connectors["slack"].window_end == fixed_end
    assert bundle.connectors["slack"].window_start < fixed_end
