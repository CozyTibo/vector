"""Phase S2.2 — execution-bearing canonical drain priority tests."""

from __future__ import annotations

import pytest

from vector.domains.cortex.canonical.forward_progress.execution_kind_priority_v1 import (
    EXECUTION_BEARING_RESOURCE_TYPES_V1,
    LOW_VALUE_GITHUB_RESOURCE_TYPES_V1,
    canonical_execution_kind_priority_enabled_v1,
    permanent_orphan_threshold_for_resource_type_v1,
    raw_record_drain_priority_rank_v1,
)


def test_execution_bearing_types_rank_before_default() -> None:
    assert raw_record_drain_priority_rank_v1("github.pull_request") == 0
    assert raw_record_drain_priority_rank_v1("github.deployment") == 0
    assert raw_record_drain_priority_rank_v1("slack.message") == 0
    assert raw_record_drain_priority_rank_v1("github.issue") == 1


def test_low_value_github_types_rank_last() -> None:
    assert raw_record_drain_priority_rank_v1("github.branch") == 2
    assert raw_record_drain_priority_rank_v1("github.tag") == 2
    assert "github.pull_request" in EXECUTION_BEARING_RESOURCE_TYPES_V1
    assert "github.branch" in LOW_VALUE_GITHUB_RESOURCE_TYPES_V1


def test_low_value_github_orphan_threshold_reduced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_CANONICAL_EXECUTION_KIND_PRIORITY", "1")
    assert canonical_execution_kind_priority_enabled_v1() is True
    assert permanent_orphan_threshold_for_resource_type_v1("github.branch", default_threshold=5) == 2
    assert permanent_orphan_threshold_for_resource_type_v1("github.pull_request", default_threshold=5) == 5


def test_priority_disabled_restores_default_orphan_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_CANONICAL_EXECUTION_KIND_PRIORITY", "0")
    assert permanent_orphan_threshold_for_resource_type_v1("github.branch", default_threshold=5) == 5
