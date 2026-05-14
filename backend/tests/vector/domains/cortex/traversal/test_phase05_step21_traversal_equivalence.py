"""P05-21 — traversal equivalence (**L-EQ-01..03**, **ENG**, **G-P05-ENG-01**)."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.cortex.traversal.traversal_equivalence_contract import (
    OctsEngineIdentityError,
    VECTOR_OCTS_ENGINE_BUILD_ID_ENV,
    list_fs_te01_same_inputs_different_hash_violations_v1,
    list_fs_te02_fast_path_without_equiv_pass_violations_v1,
    resolve_oct_engine_build_id_v1,
    verify_gp05_eng01_engine_build_id_coherence_static,
    verify_leq01_walk_hash_double_run_stub_static,
    verify_leq02_async_job_order_independence_stub_static,
    verify_leq03_fast_path_equiv_obligation_static,
    verify_oct_traversal_equivalence_step21_static_bundle,
)
from vector.domains.cortex.traversal.walk_api_contract import (
    build_stub_completed_walk_payload_v1,
)


def test_verify_gp05_eng01_static_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in (
        VECTOR_OCTS_ENGINE_BUILD_ID_ENV,
        "VECTOR_OCTS_EMBEDDED_GIT_SHA",
        "OCTS_DEV_ENGINE_ID",
    ):
        monkeypatch.delenv(k, raising=False)
    out = verify_gp05_eng01_engine_build_id_coherence_static()
    assert out["id"] == "G-P05-ENG-01"
    assert out["passed"] is True


def test_verify_leq01_leq02_leq03_static_pass() -> None:
    for fn in (
        verify_leq01_walk_hash_double_run_stub_static,
        verify_leq02_async_job_order_independence_stub_static,
        verify_leq03_fast_path_equiv_obligation_static,
    ):
        out = fn()
        assert out["passed"] is True, out


def test_verify_oct_traversal_equivalence_step21_bundle() -> None:
    bundle = verify_oct_traversal_equivalence_step21_static_bundle()
    assert bundle["passed"] is True


def test_list_fs_te02_stub_empty() -> None:
    assert list_fs_te02_fast_path_without_equiv_pass_violations_v1() == []


def test_list_fs_te01_detects_same_body_divergent_hash() -> None:
    tid = uuid.UUID("00000000-0000-4000-8000-000000000099")
    req: dict = {
        "temporal_anchor": {
            "tenant_id": str(tid),
            "export_id": "00000000-0000-4000-8000-000000000002",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "cc" * 32,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "walk_policy": {
            "max_hops": 8,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    stub = build_stub_completed_walk_payload_v1(req, tenant_id=tid)
    body = dict(stub["walk_result"]["hash_body"])
    v = list_fs_te01_same_inputs_different_hash_violations_v1(
        body,
        "sha256:" + "11" * 32,
        body,
        "sha256:" + "22" * 32,
    )
    assert v


def test_resolve_oct_engine_build_id_git_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    pin = "git:" + "ab" * 20
    monkeypatch.setenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, pin)
    monkeypatch.delenv("OCTS_DEV_ENGINE_ID", raising=False)
    assert resolve_oct_engine_build_id_v1() == pin


def test_resolve_oct_engine_build_id_dev_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, raising=False)
    monkeypatch.setenv("OCTS_DEV_ENGINE_ID", "1")
    assert resolve_oct_engine_build_id_v1() == "dev:unknown"


def test_resolve_oct_engine_build_id_raises_without_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, raising=False)
    monkeypatch.delenv("OCTS_DEV_ENGINE_ID", raising=False)
    with pytest.raises(OctsEngineIdentityError) as ei:
        resolve_oct_engine_build_id_v1()
    assert ei.value.error_code == "engine_identity_unavailable"


def test_verify_gp05_eng01_rejects_bad_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, "git:not-hex")
    out = verify_gp05_eng01_engine_build_id_coherence_static()
    assert out["passed"] is False
    monkeypatch.setenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, "dev:unknown")
    monkeypatch.delenv("OCTS_DEV_ENGINE_ID", raising=False)
    out2 = verify_gp05_eng01_engine_build_id_coherence_static()
    assert out2["passed"] is False


def test_verify_gp05_eng01_embedded_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    pin = "git:" + "cd" * 20
    monkeypatch.setenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, pin)
    monkeypatch.setenv("VECTOR_OCTS_EMBEDDED_GIT_SHA", "ef" * 20)
    out = verify_gp05_eng01_engine_build_id_coherence_static()
    assert out["passed"] is False


def test_verify_gp05_eng01_embedded_match(monkeypatch: pytest.MonkeyPatch) -> None:
    digest = "fe" * 20
    monkeypatch.setenv(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, f"git:{digest}")
    monkeypatch.setenv("VECTOR_OCTS_EMBEDDED_GIT_SHA", digest)
    out = verify_gp05_eng01_engine_build_id_coherence_static()
    assert out["passed"] is True
