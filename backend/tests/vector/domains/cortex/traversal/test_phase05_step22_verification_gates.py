"""P05-22 — **G-P05-*** verification gates catalog + PR static bundle."""

from __future__ import annotations

from vector.domains.cortex.traversal.verification_gates_catalog import (
    OCTS_CORRUPTION_GATE_BUNDLES_V1,
    list_octs_doctrine_gate_ids_v1,
    list_octs_gate_catalog_entries_v1,
    list_wired_verification_runners_v1,
    run_octs_pr_blocking_static_stages_v1,
    verify_oct_verification_gates_step22_static_bundle,
)


def test_doctrine_gate_id_count_matches_tracker_registry() -> None:
    assert len(list_octs_doctrine_gate_ids_v1()) == 54


def test_catalog_entries_cover_all_doctrine_ids() -> None:
    rows = list_octs_gate_catalog_entries_v1()
    assert {r.gate_id for r in rows} == set(list_octs_doctrine_gate_ids_v1())


def test_wired_gate_subset_of_doctrine_ids() -> None:
    wired = frozenset(list_wired_verification_runners_v1())
    assert wired <= set(list_octs_doctrine_gate_ids_v1())


def test_corruption_bundles_non_empty() -> None:
    assert "equivalence_corruption" in OCTS_CORRUPTION_GATE_BUNDLES_V1


def test_verify_oct_verification_gates_step22_static_bundle_passes() -> None:
    out = verify_oct_verification_gates_step22_static_bundle()
    assert out.get("passed") is True, out


def test_run_octs_pr_blocking_static_stages_v1_passes() -> None:
    out = run_octs_pr_blocking_static_stages_v1()
    assert out.get("passed") is True, out
