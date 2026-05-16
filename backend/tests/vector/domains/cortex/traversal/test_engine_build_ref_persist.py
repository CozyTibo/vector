"""Engine build ref fallback for durable/async walk persistence."""

from __future__ import annotations

import pytest

from vector.domains.cortex.traversal.walk_api_contract import (
    OCTS_STUB_ENGINE_BUILD_ID,
    resolve_engine_build_ref_for_persist_v1,
)


def test_resolve_engine_build_ref_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("VECTOR_OCTS_ENGINE_BUILD_ID", "OCTS_DEV_ENGINE_ID"):
        monkeypatch.delenv(k, raising=False)
    assert resolve_engine_build_ref_for_persist_v1() == OCTS_STUB_ENGINE_BUILD_ID
