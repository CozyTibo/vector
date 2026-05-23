"""P2-E ingest caps + deferral release monitoring."""

from __future__ import annotations

from types import SimpleNamespace

from vector.domains.cortex.execution.execution_ingest_deferral_monitoring import (
    build_exhaust_registry_honesty_v1,
    snapshot_github_ingest_caps_extended_v1,
)


def test_extended_caps_meet_fix6_recommended_defaults() -> None:
    cfg = SimpleNamespace(
        cortex_github_prs_max_pages_per_repo=10,
        cortex_github_pr_fetch_max_repos=16,
        cortex_github_repo_time_budget_seconds=120,
        cortex_github_timeline_max_pages_per_issue_or_pr=10,
        cortex_github_reviews_max_pages_per_pr=5,
        cortex_github_commits_max_pages_per_repo=2,
        cortex_github_deployments_max_pages_per_repo=2,
    )
    caps = snapshot_github_ingest_caps_extended_v1(settings=cfg)  # type: ignore[arg-type]
    assert caps["meets_fix6_recommended"] is True


def test_exhaust_registry_honesty_has_github() -> None:
    import uuid

    payload = build_exhaust_registry_honesty_v1(tenant_id=uuid.uuid4())
    assert payload["surface_kind"] == "exhaust_registry_honesty"
    assert payload["github"] is not None
