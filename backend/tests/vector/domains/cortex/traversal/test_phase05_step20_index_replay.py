"""P05-20 — index replay (**``phase-05-index-replay-doctrine.md``**)."""

from __future__ import annotations

import json

import jsonschema
import pytest

from vector.domains.cortex.traversal.derived_index_contract import (
    compute_index_content_hash_v1,
    octs_derived_index_fixture_dir,
)
from vector.domains.cortex.traversal.index_replay_contract import (
    list_fs_irj02_incomplete_node_set_compare_violations_v1,
    validate_oct_derived_index_replay_verify_body_v1,
    verify_gp05_replay_idx01_double_run_equality_static,
    verify_gp05_replay_idx02_corrupt_lineage_deterministic_failure_static,
)


def test_verify_gp05_replay_idx01_static_passes() -> None:
    out = verify_gp05_replay_idx01_double_run_equality_static()
    assert out["id"] == "G-P05-REPLAY-IDX-01"
    assert out["passed"] is True


def test_verify_gp05_replay_idx02_static_passes() -> None:
    out = verify_gp05_replay_idx02_corrupt_lineage_deterministic_failure_static()
    assert out["id"] == "G-P05-REPLAY-IDX-02"
    assert out["passed"] is True


def test_validate_replay_verify_envelope() -> None:
    validate_oct_derived_index_replay_verify_body_v1(
        {"artifact": {"nodes": ["a"], "adj": {}, "derived_edges": []}}
    )


def test_validate_replay_verify_rejects_extra_top_level_key() -> None:
    with pytest.raises(jsonschema.ValidationError):
        validate_oct_derived_index_replay_verify_body_v1(
            {"artifact": {}, "expected_index_content_hash": "sha256:" + "aa" * 32, "extra": 1}
        )


def test_list_fs_irj02_node_set_mismatch() -> None:
    d = octs_derived_index_fixture_dir()
    ref = json.loads((d / "derived_index_artifact_good_v1.json").read_text(encoding="utf-8"))
    cand = json.loads(json.dumps(ref))
    cand["nodes"] = list(ref["nodes"]) + ["99999999-9999-9999-9999-999999999999"]
    v = list_fs_irj02_incomplete_node_set_compare_violations_v1(ref, cand)
    assert v and "FS-IRJ-02" in v[0]


def test_same_logical_artifact_same_hash() -> None:
    d = octs_derived_index_fixture_dir()
    art = json.loads((d / "derived_index_artifact_good_v1.json").read_text(encoding="utf-8"))
    exp = (d / "index_content_hash_expected_v1.txt").read_text(encoding="utf-8").strip()
    assert compute_index_content_hash_v1(art) == exp
