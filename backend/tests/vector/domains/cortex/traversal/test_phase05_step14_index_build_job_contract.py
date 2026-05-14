"""P05-14 — index build job contract (**G-P05-JOB-01**, **G-P05-JOB-02**)."""

from __future__ import annotations

import hashlib
import json

import pytest

from vector.domains.cortex.traversal.derived_index_contract import DerivedIndexContractError
from vector.domains.cortex.traversal.index_build_job_contract import (
    IBJ_RUNTIME_SCHEMA_VERSION,
    INDEX_BUILD_JOB_STATE_BUILDING,
    INDEX_BUILD_JOB_STATE_COMMITTED,
    INDEX_BUILD_JOB_STATE_PUBLISHING,
    INDEX_BUILD_JOB_STATE_QUEUED,
    IndexBuildJobContractError,
    compute_index_build_idempotency_key_v1,
    list_fs_ibj02_duplicate_committed_epoch_different_hash_violations,
    list_rule_ibj01_simultaneous_building_lease_violations,
    octs_index_build_job_fixture_dir,
    validate_fs_ibj03_shadow_store_visibility_v1,
    validate_index_build_completion_events_v1,
    validate_index_build_job_receipt_v1,
    validate_index_build_job_state_transition_v1,
    verify_gp05_job01_index_build_fsm_illegal_transitions_static,
    verify_gp05_job02_validating_publish_audit_static,
)


def test_ibj_runtime_schema_version() -> None:
    assert IBJ_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_job01_static_passes() -> None:
    out = verify_gp05_job01_index_build_fsm_illegal_transitions_static()
    assert out["id"] == "G-P05-JOB-01"
    assert out["passed"] is True


def test_verify_gp05_job02_static_passes() -> None:
    out = verify_gp05_job02_validating_publish_audit_static()
    assert out["id"] == "G-P05-JOB-02"
    assert out["passed"] is True


def test_octs_fixture_dir() -> None:
    d = octs_index_build_job_fixture_dir()
    assert (d / "audit_trail_good_committed_v1.json").is_file()
    assert (d / "audit_trail_bad_skip_validating_v1.json").is_file()


def test_idempotency_key_v1_deterministic() -> None:
    tid = "00000000-0000-4000-8000-000000000001"
    h = "sha256:" + "a" * 64
    payload = json.dumps([tid, h, "rule.v1", 1], separators=(",", ":")).encode("utf-8")
    expected = "sha256:" + hashlib.sha256(payload).hexdigest()
    got = compute_index_build_idempotency_key_v1(
        tenant_id=tid,
        projection_content_hash=h,
        derivation_rule_id="rule.v1",
        target_schema_version=1,
    )
    assert got == expected


def test_idempotency_key_normalizes_tenant_case() -> None:
    h = "sha256:" + "b" * 64
    upper = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    lower = upper.lower()
    k1 = compute_index_build_idempotency_key_v1(
        tenant_id=upper,
        projection_content_hash=h,
        derivation_rule_id="x",
        target_schema_version=0,
    )
    k2 = compute_index_build_idempotency_key_v1(
        tenant_id=lower,
        projection_content_hash=h,
        derivation_rule_id="x",
        target_schema_version=0,
    )
    assert k1 == k2


def test_idempotency_key_rejects_bad_tenant() -> None:
    with pytest.raises(IndexBuildJobContractError, match="tenant_id"):
        compute_index_build_idempotency_key_v1(
            tenant_id="not-a-uuid",
            projection_content_hash="sha256:" + "c" * 64,
            derivation_rule_id="r",
            target_schema_version=1,
        )


def test_fsm_illegal_transition() -> None:
    with pytest.raises(IndexBuildJobContractError, match="illegal"):
        validate_index_build_job_state_transition_v1(
            INDEX_BUILD_JOB_STATE_QUEUED,
            INDEX_BUILD_JOB_STATE_PUBLISHING,
        )


def test_rule_ibj01_two_building_same_partition() -> None:
    v = list_rule_ibj01_simultaneous_building_lease_violations(
        [
            {"index_partition_key": "p1", "job_state": INDEX_BUILD_JOB_STATE_BUILDING},
            {"index_partition_key": "p1", "job_state": INDEX_BUILD_JOB_STATE_BUILDING},
        ],
    )
    assert any("RULE-IBJ-01" in x for x in v)


def test_fs_ibj02_epoch_hash_mismatch() -> None:
    h1 = "sha256:" + "d" * 64
    h2 = "sha256:" + "e" * 64
    v = list_fs_ibj02_duplicate_committed_epoch_different_hash_violations(
        [
            {
                "job_state": INDEX_BUILD_JOB_STATE_COMMITTED,
                "index_epoch": 1,
                "output_index_hash": h1,
            },
            {
                "job_state": INDEX_BUILD_JOB_STATE_COMMITTED,
                "index_epoch": 1,
                "output_index_hash": h2,
            },
        ],
    )
    assert any("FS-IBJ-02" in x for x in v)


def test_fs_ibj03_rejects_shadow_as_live_without_building_lease() -> None:
    with pytest.raises(IndexBuildJobContractError, match="FS-IBJ-03"):
        validate_fs_ibj03_shadow_store_visibility_v1(
            {
                "shadow_served_as_live_without_building_lease": True,
                "active_partition_lease_job_state": INDEX_BUILD_JOB_STATE_PUBLISHING,
            },
        )
    validate_fs_ibj03_shadow_store_visibility_v1(
        {
            "shadow_served_as_live_without_building_lease": True,
            "active_partition_lease_job_state": INDEX_BUILD_JOB_STATE_BUILDING,
        },
    )


def test_receipt_validation() -> None:
    h = "sha256:" + "f" * 64
    validate_index_build_job_receipt_v1(
        {"input_projection_hash": h, "output_index_hash": h, "index_epoch": 2},
    )
    with pytest.raises(DerivedIndexContractError, match="input_projection_hash"):
        validate_index_build_job_receipt_v1(
            {"input_projection_hash": "bad", "output_index_hash": h, "index_epoch": 0},
        )


def test_good_audit_trail_fixture() -> None:
    d = octs_index_build_job_fixture_dir()
    raw = json.loads((d / "audit_trail_good_committed_v1.json").read_text(encoding="utf-8"))
    validate_index_build_completion_events_v1(raw["events"])


def test_bad_audit_trail_fixture() -> None:
    d = octs_index_build_job_fixture_dir()
    raw = json.loads((d / "audit_trail_bad_skip_validating_v1.json").read_text(encoding="utf-8"))
    with pytest.raises(IndexBuildJobContractError, match="FS-IBJ-01"):
        validate_index_build_completion_events_v1(raw["events"])
