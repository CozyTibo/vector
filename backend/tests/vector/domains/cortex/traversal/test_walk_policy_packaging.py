"""P0-A — OCTS walk policy schema packaged for worker/API images (CONT-INV-02)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from vector.domains.cortex.substrate_pipeline.substrate_traversal_execution import (
    SUBSTRATE_WALK_POLICY_V1,
)
from vector.domains.cortex.traversal.walk_policy import (
    bundled_oct_walk_policy_v1_schema_path,
    load_oct_walk_policy_v1_schema,
    oct_walk_policy_v1_schema_path,
    validate_walk_policy_for_request_v1,
)

_REPO_DOCS_SCHEMA = (
    Path(__file__).resolve().parents[6]
    / "DOCS"
    / "cortex"
    / "05-traversal"
    / "schemas"
    / "octs-walk-policy-v1.schema.json"
)


def test_bundled_schema_file_exists() -> None:
    path = bundled_oct_walk_policy_v1_schema_path()
    assert path.is_file(), f"missing bundled schema at {path}"


def test_oct_walk_policy_schema_path_prefers_bundled() -> None:
    resolved = oct_walk_policy_v1_schema_path()
    assert resolved == bundled_oct_walk_policy_v1_schema_path()


def test_load_schema_without_repo_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate container layout: only packaged schema, no monorepo DOCS tree."""

    def _only_bundled() -> Path:
        bundled = bundled_oct_walk_policy_v1_schema_path()
        if not bundled.is_file():
            msg = f"bundled schema missing: {bundled}"
            raise RuntimeError(msg)
        return bundled

    monkeypatch.setattr(
        "vector.domains.cortex.traversal.walk_policy.oct_walk_policy_v1_schema_path",
        _only_bundled,
    )
    schema = load_oct_walk_policy_v1_schema()
    assert schema["title"] == "OCTSWalkPolicyV1"
    validate_walk_policy_for_request_v1(
        SUBSTRATE_WALK_POLICY_V1,
        walk_execution_strategy="ONLINE_OBSERVED",
        exploration_mode=False,
        enforce_sync_caps=False,
    )


def test_substrate_walk_policy_matches_phase_05_validation() -> None:
    """Same flags as ``substrate_traversal_execution`` (async path, not sync HTTP caps)."""
    validate_walk_policy_for_request_v1(
        SUBSTRATE_WALK_POLICY_V1,
        walk_execution_strategy="ONLINE_OBSERVED",
        exploration_mode=False,
        enforce_sync_caps=False,
    )


@pytest.mark.skipif(
    not _REPO_DOCS_SCHEMA.is_file(),
    reason="monorepo DOCS schema not present",
)
def test_bundled_schema_matches_docs_source() -> None:
    bundled_bytes = bundled_oct_walk_policy_v1_schema_path().read_bytes()
    docs_bytes = _REPO_DOCS_SCHEMA.read_bytes()
    assert hashlib.sha256(bundled_bytes).hexdigest() == hashlib.sha256(docs_bytes).hexdigest()
