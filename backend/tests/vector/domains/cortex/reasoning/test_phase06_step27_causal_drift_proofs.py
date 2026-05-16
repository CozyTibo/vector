"""P06-27 — Causal drift proofs (breakpoint ids + drift linkage)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.causal_drift_proofs import (
    CAUSAL_BREAKPOINT_DETECTION_SPEC_REF_V1,
    PHASE06_CAUSAL_DRIFT_PROOFS_RUNTIME_SCHEMA_VERSION,
    CausalDriftProofsError,
    canonical_breakpoint_id_body_v1,
    hash_breakpoint_id_v1,
    validate_breakpoint_index_sorted_v1,
    validate_drift_degradation_receipt_links_breakpoints_v1,
    verify_gp06_cdp01_breakpoint_id_body_key_oracle_static,
    verify_gp06_cdp02_breakpoint_index_sort_stable_static,
    verify_gp06_cdp03_drift_receipt_requires_sorted_cd_static,
    verify_gp06_cdp04_breakpoint_id_roundtrip_static,
    verify_gp06_cdp05_policy_digest_shape_enforced_static,
)
from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON


def test_runtime_schema_version() -> None:
    assert PHASE06_CAUSAL_DRIFT_PROOFS_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_cdp01_breakpoint_id_body_key_oracle_static()["passed"] is True
    assert verify_gp06_cdp02_breakpoint_index_sort_stable_static()["passed"] is True
    assert verify_gp06_cdp03_drift_receipt_requires_sorted_cd_static()["passed"] is True
    assert verify_gp06_cdp04_breakpoint_id_roundtrip_static()["passed"] is True
    assert verify_gp06_cdp05_policy_digest_shape_enforced_static()["passed"] is True


def test_canonical_body_and_hash() -> None:
    d = "a" * 64
    body = canonical_breakpoint_id_body_v1(
        rule_id="rule-1",
        at_vertex_id="vertex-1",
        frontier_snapshot_digest_pre=d,
        frontier_snapshot_digest_post=d,
        tcre_policy_bundle_digest=d,
    )
    assert set(body.keys()) == {
        "at_vertex_id",
        "frontier_snapshot_digest_post",
        "frontier_snapshot_digest_pre",
        "rule_id",
        "tcre_policy_bundle_digest",
    }
    h = hash_breakpoint_id_v1(
        rule_id="rule-1",
        at_vertex_id="vertex-1",
        frontier_snapshot_digest_pre=d,
        frontier_snapshot_digest_post=d,
        tcre_policy_bundle_digest=d,
    )
    assert len(h) == 64


def test_validate_sorted_index() -> None:
    d = "f" * 64
    r2 = {
        "breakpoint_id": hash_breakpoint_id_v1(
            rule_id="r2",
            at_vertex_id="v2",
            frontier_snapshot_digest_pre=d,
            frontier_snapshot_digest_post=d,
            tcre_policy_bundle_digest=d,
        ),
        "rule_id": "r2",
        "at_vertex_id": "v2",
        "observed_at_iso": "2020-01-02T00:00:00Z",
    }
    r1 = {
        "breakpoint_id": hash_breakpoint_id_v1(
            rule_id="r1",
            at_vertex_id="v1",
            frontier_snapshot_digest_pre=d,
            frontier_snapshot_digest_post=d,
            tcre_policy_bundle_digest=d,
        ),
        "rule_id": "r1",
        "at_vertex_id": "v1",
        "observed_at_iso": "2020-01-01T00:00:00Z",
    }
    ordered = [r1, r2]
    validate_breakpoint_index_sorted_v1(ordered)
    with pytest.raises(CausalDriftProofsError, match="sorted"):
        validate_breakpoint_index_sorted_v1([r2, r1])


def test_drift_linkage_happy_path() -> None:
    d = "0" * 64
    rows = [
        {
            "breakpoint_id": hash_breakpoint_id_v1(
                rule_id="bp-rule",
                at_vertex_id="vx",
                frontier_snapshot_digest_pre=d,
                frontier_snapshot_digest_post=d,
                tcre_policy_bundle_digest=d,
            ),
            "rule_id": "bp-rule",
            "at_vertex_id": "vx",
            "observed_at_iso": "2020-01-01T00:00:00Z",
        }
    ]
    validate_drift_degradation_receipt_links_breakpoints_v1(
        cd_codes_sorted=[CD_CHRON],
        breakpoint_rule_ids_sorted=["bp-rule"],
        breakpoint_index_rows=rows,
    )


def test_drift_linkage_missing_rule() -> None:
    d = "1" * 64
    rows = [
        {
            "breakpoint_id": hash_breakpoint_id_v1(
                rule_id="missing-from-receipt",
                at_vertex_id="v",
                frontier_snapshot_digest_pre=d,
                frontier_snapshot_digest_post=d,
                tcre_policy_bundle_digest=d,
            ),
            "rule_id": "missing-from-receipt",
            "at_vertex_id": "v",
            "observed_at_iso": "2020-01-01T00:00:00Z",
        }
    ]
    with pytest.raises(CausalDriftProofsError, match="missing"):
        validate_drift_degradation_receipt_links_breakpoints_v1(
            cd_codes_sorted=[CD_CHRON],
            breakpoint_rule_ids_sorted=["other"],
            breakpoint_index_rows=rows,
        )


def test_spec_ref() -> None:
    assert "causal-breakpoint-detection" in CAUSAL_BREAKPOINT_DETECTION_SPEC_REF_V1


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        bp = root / "DOCS" / "cortex" / "reasoning" / "causal-breakpoint-detection-spec.md"
        if bp.is_file():
            assert "breakpoint_id" in bp.read_text(encoding="utf-8")
            return
    pytest.fail("causal-breakpoint-detection-spec.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_CAUSAL_DRIFT_PROOFS_RUNTIME_SCHEMA_VERSION >= 1
    assert verify_gp06_cdp01_breakpoint_id_body_key_oracle_static()["passed"] is True
