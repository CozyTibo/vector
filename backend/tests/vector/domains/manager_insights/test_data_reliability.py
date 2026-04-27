"""Tests for Manager insights Step 0.5 (data reliability)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from vector.contracts.manager_insights_activity import (
    ConnectorCompletenessStats,
    ConnectorCoverageStats,
    ConnectorFetchResult,
    FetchActivityBundle,
)
from vector.domains.manager_insights.data_reliability import compute_data_reliability


def _result(
    connector: str,
    *,
    status: str,
    fetched_at: datetime | None,
    window_end: datetime,
    caps: list[str] | None = None,
    errors: list[str] | None = None,
    configured_sources: int = 2,
    successful_sources: int = 2,
    critical_configured_sources: int = 1,
    critical_successful_sources: int = 1,
    completeness_successful_sources: int | None = None,
    capped_sources: int = 0,
    expected_non_empty_sources: int = 1,
    observed_non_empty_sources: int = 1,
) -> ConnectorFetchResult:
    window_start = window_end - timedelta(days=30)
    completeness_success = (
        completeness_successful_sources
        if completeness_successful_sources is not None
        else successful_sources
    )
    return ConnectorFetchResult(
        connector=connector,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        fetched_at=fetched_at,
        window_start=window_start,
        window_end=window_end,
        caps_applied=caps or [],
        errors=errors or [],
        coverage=ConnectorCoverageStats(
            configured_sources=configured_sources,
            successful_sources=successful_sources,
            critical_configured_sources=critical_configured_sources,
            critical_successful_sources=critical_successful_sources,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=max(0, completeness_success),
            capped_sources=capped_sources,
            expected_non_empty_sources=expected_non_empty_sources,
            observed_non_empty_sources=observed_non_empty_sources,
        ),
        payload={},
    )


def test_overall_low_when_critical_slack_not_configured() -> None:
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    bundle = FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        connectors={
            "slack": _result("slack", status="not_configured", fetched_at=None, window_end=end),
            "github": _result(
                "github",
                status="ok",
                fetched_at=end - timedelta(hours=1),
                window_end=end,
            ),
            "linear": _result(
                "linear",
                status="ok",
                fetched_at=end - timedelta(hours=1),
                window_end=end,
            ),
            "notion": _result("notion", status="not_built", fetched_at=None, window_end=end),
            "calls": _result("calls", status="not_built", fetched_at=None, window_end=end),
        },
    )
    rep = compute_data_reliability(bundle)
    assert rep.slack.tier == "low"
    assert rep.overall_confidence == "low"


def test_overall_high_when_critical_all_fresh() -> None:
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    fresh = end - timedelta(hours=2)
    bundle = FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        connectors={
            "slack": _result("slack", status="ok", fetched_at=fresh, window_end=end),
            "github": _result("github", status="ok", fetched_at=fresh, window_end=end),
            "linear": _result("linear", status="ok", fetched_at=fresh, window_end=end),
            "notion": _result("notion", status="not_built", fetched_at=None, window_end=end),
            "calls": _result("calls", status="not_built", fetched_at=None, window_end=end),
        },
    )
    rep = compute_data_reliability(bundle)
    assert rep.slack.tier == "high"
    assert rep.notion.tier == "low"
    # 3/5 are high (60%), so overall stays medium per >=80% high rule.
    assert rep.overall_confidence == "medium"


def test_connector_downgrades_to_medium_when_capped() -> None:
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    fresh = end - timedelta(hours=1)
    bundle = FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        connectors={
            "slack": _result("slack", status="ok", fetched_at=fresh, window_end=end),
            "github": _result(
                "github",
                status="ok",
                fetched_at=fresh,
                window_end=end,
                caps=["c1"],
                configured_sources=3,
                successful_sources=3,
                completeness_successful_sources=3,
                capped_sources=2,
            ),
            "linear": _result("linear", status="ok", fetched_at=fresh, window_end=end),
            "notion": _result("notion", status="ok", fetched_at=fresh, window_end=end),
            "calls": _result("calls", status="ok", fetched_at=fresh, window_end=end),
        },
    )
    rep = compute_data_reliability(bundle)
    assert rep.github.tier == "medium"
    assert "completeness:high_to_medium_due_to_caps" in rep.github.reasons
    assert any(r.startswith("cap:") for r in rep.github.reasons)
    assert rep.overall_confidence == "medium"


def test_connector_stale_over_72h_is_low() -> None:
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    stale = end - timedelta(hours=73)
    bundle = FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        connectors={
            "slack": _result("slack", status="ok", fetched_at=stale, window_end=end),
            "github": _result("github", status="ok", fetched_at=end - timedelta(hours=1), window_end=end),
            "linear": _result("linear", status="ok", fetched_at=end - timedelta(hours=1), window_end=end),
            "notion": _result("notion", status="ok", fetched_at=end - timedelta(hours=1), window_end=end),
            "calls": _result("calls", status="ok", fetched_at=end - timedelta(hours=1), window_end=end),
        },
    )
    rep = compute_data_reliability(bundle)
    assert rep.slack.tier == "low"
    assert "freshness:stale_over_72h" in rep.slack.reasons
    assert rep.overall_confidence == "low"


def test_connector_low_when_critical_source_missing() -> None:
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    fresh = end - timedelta(hours=2)
    bundle = FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        connectors={
            "slack": _result(
                "slack",
                status="ok",
                fetched_at=fresh,
                window_end=end,
                critical_configured_sources=2,
                critical_successful_sources=1,
            ),
            "github": _result("github", status="ok", fetched_at=fresh, window_end=end),
            "linear": _result("linear", status="ok", fetched_at=fresh, window_end=end),
            "notion": _result("notion", status="ok", fetched_at=fresh, window_end=end),
            "calls": _result("calls", status="ok", fetched_at=fresh, window_end=end),
        },
    )
    rep = compute_data_reliability(bundle)
    assert rep.slack.tier == "low"
    assert "coverage:critical_source_missing" in rep.slack.reasons
    assert rep.overall_confidence == "low"
