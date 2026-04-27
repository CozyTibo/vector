"""Step 0.5 — deterministic data reliability from Step 1 fetch bundle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from vector.contracts.manager_insights_activity import (
    ConnectorFetchResult,
    ConnectorReliabilityDetail,
    DataReliabilityReport,
    DataReliabilityTier,
    FetchActivityBundle,
    ManagerInsightConnector,
)

_CRITICAL_CONNECTORS: tuple[ManagerInsightConnector, ...] = ("slack", "github", "linear")

_ORDER: tuple[ManagerInsightConnector, ...] = ("slack", "github", "linear", "notion", "calls")
_FRESHNESS_HIGH_HOURS = 24.0
_FRESHNESS_MEDIUM_HOURS = 72.0
_MAX_REASON_ERRORS = 5
_COVERAGE_HIGH_RATIO = 0.80
_COVERAGE_MEDIUM_RATIO = 0.50
_COMPLETENESS_CAPS_DOWNGRADE_RATIO = 0.50
_COMPLETENESS_CAPS_CRITICAL_RATIO = 0.80
_HIGH_CONNECTOR_RATIO_FOR_OVERALL = 0.80


def _freshness_hours(result: ConnectorFetchResult) -> float | None:
    if result.fetched_at is None:
        return None
    delta = result.window_end - result.fetched_at
    if delta.total_seconds() < 0:
        return 0.0
    return delta.total_seconds() / 3600.0


def _detail_for_result(result: ConnectorFetchResult) -> ConnectorReliabilityDetail:
    if result.status == "not_built":
        return ConnectorReliabilityDetail(
            tier="low",
            reasons=["status:not_built", "coverage:connector_not_implemented"],
        )
    if result.status == "global_disabled":
        base_reason = result.errors[0] if result.errors else "connector_globally_disabled"
        return ConnectorReliabilityDetail(
            tier="low",
            reasons=["status:global_disabled", f"coverage:{base_reason}"],
        )
    if result.status == "not_configured":
        return ConnectorReliabilityDetail(
            tier="low",
            reasons=["status:not_configured", "coverage:tenant_not_connected"],
        )
    if result.status == "error":
        return ConnectorReliabilityDetail(
            tier="low",
            reasons=["status:error", "coverage:fetch_failed"]
            + [f"error:{e}" for e in result.errors[:_MAX_REASON_ERRORS]],
        )

    hours = _freshness_hours(result)
    if hours is None:
        return ConnectorReliabilityDetail(
            tier="low",
            reasons=["status:ok", "freshness:missing_fetched_at"],
        )

    cov = result.coverage
    comp = result.completeness
    configured = max(0, cov.configured_sources)
    successful = max(0, cov.successful_sources)
    critical_configured = max(0, cov.critical_configured_sources)
    critical_successful = max(0, cov.critical_successful_sources)
    coverage_ratio = (float(successful) / float(configured)) if configured > 0 else 0.0
    critical_missing = critical_configured > critical_successful
    reasons: list[str] = ["status:ok"]
    metrics = {
        "coverage_ratio": coverage_ratio,
        "freshness_hours": hours,
    }
    if critical_configured > 0:
        metrics["critical_coverage_ratio"] = float(critical_successful) / float(critical_configured)

    if critical_missing:
        tier: DataReliabilityTier = "low"
        reasons.append("coverage:critical_source_missing")
    elif coverage_ratio < _COVERAGE_MEDIUM_RATIO:
        tier = "low"
        reasons.append("coverage:below_50_percent")
    elif coverage_ratio >= _COVERAGE_HIGH_RATIO and hours <= _FRESHNESS_HIGH_HOURS:
        tier = "high"
        reasons.extend(["coverage:at_least_80_percent", "freshness:within_24h"])
    elif hours <= _FRESHNESS_MEDIUM_HOURS:
        tier = "medium"
        reasons.append("coverage:at_least_50_percent")
        reasons.append("freshness:within_72h")
    else:
        tier = "low"
        reasons.append("freshness:stale_over_72h")

    successful_for_completeness = max(0, comp.successful_sources)
    capped_ratio = (
        float(comp.capped_sources) / float(successful_for_completeness)
        if successful_for_completeness > 0
        else 0.0
    )
    non_empty_ratio = (
        float(comp.observed_non_empty_sources) / float(comp.expected_non_empty_sources)
        if comp.expected_non_empty_sources > 0
        else 1.0
    )
    metrics["capped_ratio"] = capped_ratio
    metrics["non_empty_ratio"] = non_empty_ratio
    if capped_ratio > _COMPLETENESS_CAPS_CRITICAL_RATIO:
        tier = "low"
        reasons.append("completeness:caps_dominate")
    elif capped_ratio > _COMPLETENESS_CAPS_DOWNGRADE_RATIO and tier == "high":
        tier = "medium"
        reasons.append("completeness:high_to_medium_due_to_caps")
    elif capped_ratio > _COMPLETENESS_CAPS_DOWNGRADE_RATIO and tier == "medium":
        tier = "low"
        reasons.append("completeness:medium_to_low_due_to_caps")
    elif comp.capped_sources > 0:
        reasons.append("completeness:caps_present")

    if comp.expected_non_empty_sources > 0 and comp.observed_non_empty_sources == 0 and tier != "low":
        tier = "low"
        reasons.append("completeness:all_expected_sources_empty")
    elif comp.expected_non_empty_sources > 0 and non_empty_ratio < 0.5:
        reasons.append("completeness:mostly_empty_sources")
    for cap in result.caps_applied:
        reasons.append(f"cap:{cap}")

    return ConnectorReliabilityDetail(tier=tier, reasons=reasons, metrics=metrics)


def _overall_tier(details: dict[str, ConnectorReliabilityDetail]) -> DataReliabilityTier:
    crit = [details[c] for c in _CRITICAL_CONNECTORS if c in details]
    if not crit:
        return "low"
    crit_lows = sum(1 for d in crit if d.tier == "low")
    crit_highs = sum(1 for d in crit if d.tier == "high")
    if crit_lows:
        return "low"

    all_vals = [details[c] for c in _ORDER if c in details]
    n = len(all_vals)
    if n == 0:
        return "low"
    lows = sum(1 for d in all_vals if d.tier == "low")
    highs = sum(1 for d in all_vals if d.tier == "high")
    if lows > n / 2:
        return "low"
    # High confidence only when all critical connectors are high and >=80% of all connectors are high.
    if crit_highs == len(crit) and highs / float(n) >= _HIGH_CONNECTOR_RATIO_FOR_OVERALL:
        return "high"
    return "medium"


def compute_data_reliability(bundle: FetchActivityBundle) -> DataReliabilityReport:
    """Same inputs+config → same report (deterministic)."""

    details: dict[str, ConnectorReliabilityDetail] = {}
    for key in _ORDER:
        result = bundle.connectors.get(key)
        if result is None:
            details[key] = ConnectorReliabilityDetail(
                tier="low",
                reasons=["missing_connector_result_in_bundle"],
            )
        else:
            details[key] = _detail_for_result(result)

    return DataReliabilityReport(
        slack=details["slack"],
        github=details["github"],
        linear=details["linear"],
        notion=details["notion"],
        calls=details["calls"],
        overall_confidence=_overall_tier(details),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def default_window(*, window_days: int, as_of: datetime | None = None) -> tuple[datetime, datetime]:
    end = as_of or utc_now()
    start = end - timedelta(days=window_days)
    return (start, end)
