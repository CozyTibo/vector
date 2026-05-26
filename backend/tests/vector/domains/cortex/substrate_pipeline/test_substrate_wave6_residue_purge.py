"""Wave 6 — domain residue purge static gates."""

from __future__ import annotations

from vector.domains.cortex.execution.scheduling import verify_wave6_residue_purge_v1
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    verify_substrate_coherence_ci_gates_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_residue_v1 import (
    verify_forbidden_substrate_substrings_v1,
    verify_no_substrate_residue_v1,
    verify_sync_executor_not_in_production_imports_v1,
)


def test_verify_no_substrate_residue_v1() -> None:
    assert verify_no_substrate_residue_v1() == []


def test_verify_forbidden_substrings_clean() -> None:
    assert verify_forbidden_substrate_substrings_v1() == []


def test_cortex_ingestion_sync_uses_sync_router() -> None:
    assert verify_sync_executor_not_in_production_imports_v1() == []


def test_verify_wave6_residue_purge_v1() -> None:
    assert verify_wave6_residue_purge_v1() == []


def test_substrate_coherence_ci_includes_wave6() -> None:
    assert verify_substrate_coherence_ci_gates_v1() == []
