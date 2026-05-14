"""P05-11 — exploration mode (**G-P05-EXP-01**, **G-P05-EXP-02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.exploration_mode_contract import (
    EX_RUNTIME_SCHEMA_VERSION,
    EXECUTION_PARTITION_EXPLORATION,
    ExplorationModeContractError,
    assert_redis_cache_key_namespace_v1,
    exploration_partition_id_v1,
    octs_exploration_fixture_dir,
    validate_exploration_hash_body_invariants_v1,
    validate_row_destination_exploration_law_v1,
    verify_gp05_exp01_walk_request_explicit_exploration_mode_static,
    verify_gp05_exp02_authoritative_table_rejects_exploration_partition_static,
)
from vector.domains.cortex.traversal.walk_result_contract import (
    WalkResultContractError,
    validate_walk_result_hash_body_contract_v1,
)


def test_ex_runtime_schema_version() -> None:
    assert EX_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_exp01_static_passes() -> None:
    out = verify_gp05_exp01_walk_request_explicit_exploration_mode_static()
    assert out["id"] == "G-P05-EXP-01"
    assert out["passed"] is True


def test_verify_gp05_exp02_static_passes() -> None:
    out = verify_gp05_exp02_authoritative_table_rejects_exploration_partition_static()
    assert out["id"] == "G-P05-EXP-02"
    assert out["passed"] is True


def test_exploration_partition_id() -> None:
    assert exploration_partition_id_v1("01HZ") == "explore:01HZ"


def test_cache_key_prefixes() -> None:
    assert_redis_cache_key_namespace_v1("octs:explore:t1:walk:abc", exploration=True)
    assert_redis_cache_key_namespace_v1("octs:auth:t1:walk:def", exploration=False)
    with pytest.raises(ExplorationModeContractError):
        assert_redis_cache_key_namespace_v1("walk:abc", exploration=True)


def test_exploration_fixture_dir() -> None:
    d = octs_exploration_fixture_dir()
    assert (d / "walk_hash_body_exploration_good_v1.json").is_file()


def test_walk_hash_body_exploration_good_passes_contract() -> None:
    path = octs_exploration_fixture_dir() / "walk_hash_body_exploration_good_v1.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    validate_walk_result_hash_body_contract_v1(body)


def test_walk_hash_body_exploration_bad_fs_ex02_rejected() -> None:
    path = octs_exploration_fixture_dir() / "walk_hash_body_exploration_bad_fs_ex02_v1.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(WalkResultContractError, match="FS-EX-02|non_authoritative"):
        validate_walk_result_hash_body_contract_v1(body)


def test_hop_missing_partition_under_exploration_markers() -> None:
    path = octs_exploration_fixture_dir() / "walk_hash_body_exploration_good_v1.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    hop = dict(body["hop_receipts"][0])
    hop.pop("partition", None)
    bad = {**body, "hop_receipts": [hop]}
    with pytest.raises(ExplorationModeContractError, match="partition"):
        validate_exploration_hash_body_invariants_v1(bad)


def test_validate_row_destination_law() -> None:
    validate_row_destination_exploration_law_v1(
        table_name="cortex_octs_walk_authoritative",
        partition="authoritative",
    )
    with pytest.raises(ExplorationModeContractError):
        validate_row_destination_exploration_law_v1(
            table_name="cortex_octs_walk_authoritative",
            partition=EXECUTION_PARTITION_EXPLORATION,
        )
