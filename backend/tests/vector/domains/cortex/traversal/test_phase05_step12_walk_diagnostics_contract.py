"""P05-12 — walk diagnostics (**G-P05-DIAG-01**, **G-P05-DIAG-02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.hop_receipt_contract import (
    HopReceiptContractError,
    octs_hop_receipt_fixture_dir,
    validate_hop_receipt_list_for_hash_body_v1,
)
from vector.domains.cortex.traversal.walk_diagnostics_contract import (
    WD_RUNTIME_SCHEMA_VERSION,
    WalkDiagnosticsContractError,
    compute_cycle_fingerprint_v1,
    octs_walk_diagnostics_fixture_dir,
    validate_hash_body_diagnostics_contract_v1,
    validate_skip_reason_enum_v1,
    validate_termination_reason_enum_v1,
    validate_walk_diagnostics_hash_body_contract_v1,
    verify_gp05_diag01_enum_exhaustiveness_vs_schema_static,
    verify_gp05_diag02_cycle_fingerprint_golden_static,
)
from vector.domains.cortex.traversal.walk_result_contract import (
    WalkResultContractError,
    validate_walk_result_hash_body_contract_v1,
)

_SHA256_A = "sha256:" + "a" * 64


def _minimal_anchor() -> dict:
    return {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "export_id": "00000000-0000-0000-0000-000000000002",
        "export_sequence": 1,
        "projection_content_hash": _SHA256_A,
        "snapshot_unix_ns": {"unix_ns": 1},
        "graph_as_of_unix_ns": {"unix_ns": 1},
    }


def _minimal_hash_body(**overrides: object) -> dict:
    base = {
        "octs_schema_version": 1,
        "temporal_anchor": _minimal_anchor(),
        "policy_hash": "sha256:" + "b" * 64,
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "termination_reason": "budget_exhausted",
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [],
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def test_wd_runtime_schema_version() -> None:
    assert WD_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_diag01_static_passes() -> None:
    out = verify_gp05_diag01_enum_exhaustiveness_vs_schema_static()
    assert out["id"] == "G-P05-DIAG-01"
    assert out["passed"] is True


def test_verify_gp05_diag02_static_passes() -> None:
    out = verify_gp05_diag02_cycle_fingerprint_golden_static()
    assert out["id"] == "G-P05-DIAG-02"
    assert out["passed"] is True


def test_fixture_dir() -> None:
    d = octs_walk_diagnostics_fixture_dir()
    assert (d / "cycle_fingerprint_edges_v1.json").is_file()


def test_compute_cycle_fingerprint_order_independent() -> None:
    a = "sha256:" + "1" * 64
    b = "sha256:" + "2" * 64
    c = "sha256:" + "3" * 64
    assert compute_cycle_fingerprint_v1([a, b, c]) == compute_cycle_fingerprint_v1([c, a, b])


def test_fs_wd01_unknown_termination() -> None:
    body = _minimal_hash_body(termination_reason="stopped because slow")
    with pytest.raises(WalkDiagnosticsContractError, match="FS-WD-01"):
        validate_termination_reason_enum_v1(body["termination_reason"])


def test_fs_wd02_missing_termination() -> None:
    body = _minimal_hash_body()
    del body["termination_reason"]
    with pytest.raises(WalkDiagnosticsContractError, match="FS-WD-02"):
        validate_walk_diagnostics_hash_body_contract_v1(body)


def test_rule_wd01_budget_forbids_nonempty_diagnostics() -> None:
    body = _minimal_hash_body(
        diagnostics={
            "cycle_fingerprint": "sha256:" + "c" * 64,
        },
    )
    with pytest.raises(WalkDiagnosticsContractError, match="RULE WD-01"):
        validate_walk_diagnostics_hash_body_contract_v1(body)


def test_fs_wd03_target_reached_path_mismatch() -> None:
    hop_path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    hop = json.loads(hop_path.read_text(encoding="utf-8"))
    body = _minimal_hash_body(
        termination_reason="target_reached",
        hop_receipts=[hop],
        path_edge_fingerprints_ordered=[],
    )
    with pytest.raises(WalkDiagnosticsContractError, match="FS-WD-03"):
        validate_hash_body_diagnostics_contract_v1(body)


def test_cycle_cut_requires_cycle_fingerprint() -> None:
    body = _minimal_hash_body(termination_reason="cycle_cut")
    with pytest.raises(WalkDiagnosticsContractError, match="cycle_cut requires"):
        validate_hash_body_diagnostics_contract_v1(body)

    body_ok = _minimal_hash_body(
        termination_reason="cycle_cut",
        diagnostics={"cycle_fingerprint": "sha256:" + "d" * 64},
    )
    validate_hash_body_diagnostics_contract_v1(body_ok)


def test_invalid_edge_at_t_requires_record() -> None:
    body = _minimal_hash_body(termination_reason="invalid_edge_at_t")
    with pytest.raises(WalkDiagnosticsContractError, match="invalid_edge_at_t requires"):
        validate_hash_body_diagnostics_contract_v1(body)

    body_ok = _minimal_hash_body(
        termination_reason="invalid_edge_at_t",
        diagnostics={
            "invalid_edge_record": {
                "offending_edge_fingerprint": "sha256:" + "e" * 64,
            },
        },
    )
    validate_hash_body_diagnostics_contract_v1(body_ok)


def test_skip_reason_enum_hop_receipt() -> None:
    hop_path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    hop = json.loads(hop_path.read_text(encoding="utf-8"))
    bad = {**hop, "skip_reason": "not_a_real_skip"}
    with pytest.raises(HopReceiptContractError, match="FS-WD-01"):
        validate_hop_receipt_list_for_hash_body_v1([bad])

    good = {**hop, "skip_reason": "not_in_allowlist"}
    validate_hop_receipt_list_for_hash_body_v1([good])


def test_validate_skip_reason_enum_direct() -> None:
    with pytest.raises(WalkDiagnosticsContractError):
        validate_skip_reason_enum_v1("bogus")


def test_full_contract_wires_diagnostics() -> None:
    body = _minimal_hash_body()
    validate_walk_result_hash_body_contract_v1(body)


def test_unknown_termination_raises_walk_result_contract() -> None:
    body = _minimal_hash_body(termination_reason="x")
    with pytest.raises(WalkResultContractError, match="FS-WD-01"):
        validate_walk_result_hash_body_contract_v1(body)
