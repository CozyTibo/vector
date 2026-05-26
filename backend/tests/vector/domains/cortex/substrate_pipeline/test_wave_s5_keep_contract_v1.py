"""S5.3 — KEEP list contract tests."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.wave_s5_keep_contract_v1 import (
    KEEP_SURFACES_V1,
    verify_s5_3_keep_contract_v1,
)


def test_s5_3_keep_contract_all_surfaces_present() -> None:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        default_repo_root_v1,
    )

    root = default_repo_root_v1()
    result = verify_s5_3_keep_contract_v1(repo_root=root)
    assert result["s5_3_ok"] is True, result["errors"]
    assert result["keep_surface_count"] == len(KEEP_SURFACES_V1)
