"""Wave 9 — final domain shape (five verbs, module budget, invariant laws)."""

from __future__ import annotations

from vector.domains.cortex.execution.scheduling import verify_wave9_final_domain_shape_v1
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    discover_repo_root_v1,
    verify_substrate_coherence_ci_gates_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_final_domain_shape_v1 import (
    SUBSTRATE_CRITICAL_MODULE_MAX_V1,
    SUBSTRATE_CRITICAL_MODULES_V1,
    SUBSTRATE_VERBS_OWNERSHIP_V1,
    build_substrate_domain_shape_catalog_v1,
    verify_l10_no_unlock_in_execution_identity_v1,
    verify_substrate_critical_modules_v1,
    verify_wave9_final_domain_shape_v1,
)


def test_critical_module_count_within_budget() -> None:
    assert len(SUBSTRATE_CRITICAL_MODULES_V1) <= SUBSTRATE_CRITICAL_MODULE_MAX_V1


def test_five_verbs_plus_truth() -> None:
    verbs = {row["verb"] for row in SUBSTRATE_VERBS_OWNERSHIP_V1}
    assert verbs == {"INGEST", "MATERIALIZE", "REPAIR", "PROMOTE", "EXPORT", "TRUTH"}


def test_domain_shape_catalog() -> None:
    cat = build_substrate_domain_shape_catalog_v1()
    assert cat["surface_kind"] == "substrate_domain_shape_v1"
    assert cat["critical_module_count"] == len(SUBSTRATE_CRITICAL_MODULES_V1)


def test_verify_substrate_critical_modules_v1() -> None:
    assert verify_substrate_critical_modules_v1() == []


def test_l10_execution_identity_unlock_free() -> None:
    assert verify_l10_no_unlock_in_execution_identity_v1() == []


def test_verify_wave9_final_domain_shape_v1() -> None:
    root = discover_repo_root_v1()
    assert verify_wave9_final_domain_shape_v1(repo_root=root) == []


def test_verify_wave9_scheduling_wrapper() -> None:
    assert verify_wave9_final_domain_shape_v1() == []


def test_coherence_ci_includes_wave9() -> None:
    assert verify_substrate_coherence_ci_gates_v1() == []
