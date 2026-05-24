"""Phase S2.3 — execution artifact TCRE scope tests."""

from __future__ import annotations

from vector.domains.cortex.reasoning.runtime.execution_artifact_tcre_scope_v1 import (
    EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1,
)


def test_execution_materialization_kinds_include_pr_and_deploy() -> None:
    assert "pull_request" in EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1
    assert "deployment" in EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1
    assert "message" in EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1
