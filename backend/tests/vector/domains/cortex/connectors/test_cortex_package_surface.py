"""Fast checks: cortex connector package wires five providers (no DATABASE_URL)."""

from __future__ import annotations

from vector.domains.cortex.connectors.runtime import all_runtimes_ordered, connector_runtimes, runtime_by_id


def test_connector_runtimes_five_providers_sorted_ids() -> None:
    ids = [r.id for r in all_runtimes_ordered()]
    assert ids == ["calls", "github", "linear", "notion", "slack"]


def test_runtime_by_id_matches_tuple() -> None:
    d = runtime_by_id()
    assert set(d.keys()) == {"calls", "github", "linear", "notion", "slack"}
    assert len(connector_runtimes()) == 5
