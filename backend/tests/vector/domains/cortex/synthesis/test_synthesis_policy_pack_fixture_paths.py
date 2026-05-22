"""Policy pack fixtures must load from the Python package (prod Docker image has no DOCS/)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.synthesis.synthesis_query_plan import (
    load_synthesis_policy_pack_v1,
    synthesis_policy_pack_fixture_path_v1,
)


def test_synthesis_policy_pack_fixture_resolves_from_package_dir() -> None:
    path = synthesis_policy_pack_fixture_path_v1()
    assert path is not None
    assert path.is_file()
    assert "domains/cortex/synthesis/fixtures" in str(path)


def test_load_synthesis_policy_pack_without_docs_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ECS image: only packaged fixtures, no repo DOCS."""
    pack = load_synthesis_policy_pack_v1()
    assert pack.get("synthesis_policy_pack_id") == "SynthesisPolicyPackV1_Default"
    assert isinstance(pack.get("pipeline_default_workloads"), list)

    # Ensure loader does not depend on DOCS/ at repo root.
    from vector.domains.cortex.synthesis import synthesis_query_plan as mod

    def _no_docs_root() -> Path:
        return Path("/nonexistent")

    monkeypatch.setattr(mod, "_repo_root_v1", _no_docs_root)
    pack2 = load_synthesis_policy_pack_v1()
    assert pack2["synthesis_policy_pack_id"] == pack["synthesis_policy_pack_id"]
