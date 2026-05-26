"""S5.6 — deploy alignment wiring tests."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.wave_s5_deploy_align_v1 import (
    verify_s5_6_deploy_align_wiring_v1,
)


def test_s5_6_deploy_workflow_wires_ecs_probe() -> None:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        default_repo_root_v1,
    )

    root = default_repo_root_v1()
    result = verify_s5_6_deploy_align_wiring_v1(repo_root=root)
    assert result["s5_6_ok"] is True, result["errors"]
