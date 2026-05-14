"""P05-02 — observed vs derived traversal (observed_vs_derived validators)."""

from __future__ import annotations

import pytest

from vector.domains.cortex.traversal.observed_vs_derived import (
    OVD_RUNTIME_SCHEMA_VERSION,
    PROVENANCE_CLASS_DERIVED,
    PROVENANCE_CLASS_OBSERVED,
    WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
    WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
    ObservedDerivedInvariantError,
    validate_hop_receipt_observed_derived,
    validate_hop_receipt_sequence,
    validate_walk_observed_derived_consistency,
    verify_gp05_ovd01_observed_hop_bindings_static,
    verify_gp05_ovd02_strategy_and_derived_flags_static,
)


def test_ovd_runtime_schema_version() -> None:
    assert OVD_RUNTIME_SCHEMA_VERSION >= 1


def test_rejects_fs_ovd01_observed_without_binding() -> None:
    with pytest.raises(ObservedDerivedInvariantError, match="FS-OVD-01"):
        validate_hop_receipt_observed_derived(
            {
                "hop_sequence": 0,
                "provenance_class": PROVENANCE_CLASS_OBSERVED,
                "authority_binding": None,
            }
        )


def test_accepts_observed_with_binding() -> None:
    validate_hop_receipt_observed_derived(
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "01HZ", "edge_fingerprint": "sha256:aa"},
        }
    )


def test_accepts_derived_null_binding_with_rule() -> None:
    validate_hop_receipt_observed_derived(
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_DERIVED,
            "authority_binding": None,
            "derivation_rule_id": "DERIVED_ADJ_v3",
        }
    )


def test_rejects_derived_without_derivation_rule_id() -> None:
    with pytest.raises(ObservedDerivedInvariantError, match="derivation_rule_id"):
        validate_hop_receipt_observed_derived(
            {
                "hop_sequence": 0,
                "provenance_class": PROVENANCE_CLASS_DERIVED,
                "authority_binding": None,
            }
        )


def test_hop_receipt_sequence_contiguous() -> None:
    receipts = [
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "a", "edge_fingerprint": "sha256:0"},
        },
        {
            "hop_sequence": 1,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "b", "edge_fingerprint": "sha256:1"},
        },
    ]
    validate_hop_receipt_sequence(receipts)


def test_hop_receipt_sequence_rejects_gap() -> None:
    bad = [
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "a", "edge_fingerprint": "sha256:0"},
        },
        {
            "hop_sequence": 2,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "b", "edge_fingerprint": "sha256:1"},
        },
    ]
    with pytest.raises(ObservedDerivedInvariantError, match="hop_sequence"):
        validate_hop_receipt_sequence(bad)


def test_materialized_requires_derived_flag_and_epoch() -> None:
    receipts = [
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "a", "edge_fingerprint": "sha256:0"},
        }
    ]
    with pytest.raises(ObservedDerivedInvariantError, match="execution_path_contains_derived"):
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
            hop_receipts=receipts,
            walk_result={"execution_path_contains_derived": False},
            temporal_anchor={"pinned_index_epoch": 1},
        )


def test_hybrid_requires_epoch_when_derived_flag() -> None:
    receipts = [
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "a", "edge_fingerprint": "sha256:0"},
        }
    ]
    with pytest.raises(ObservedDerivedInvariantError, match="pinned_index_epoch"):
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
            hop_receipts=receipts,
            walk_result={"execution_path_contains_derived": True},
            temporal_anchor=None,
        )


def test_verify_gp05_ovd01_static_passes() -> None:
    out = verify_gp05_ovd01_observed_hop_bindings_static()
    assert out["id"] == "G-P05-OVD-01"
    assert out["passed"] is True


def test_verify_gp05_ovd02_static_passes() -> None:
    out = verify_gp05_ovd02_strategy_and_derived_flags_static()
    assert out["id"] == "G-P05-OVD-02"
    assert out["passed"] is True
