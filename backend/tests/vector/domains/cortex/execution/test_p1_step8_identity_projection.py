"""P1 step 8 — phase 03 identity projection without org-link replay job enqueue."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_p1_step8_identity_projection_boundary_v1
from vector.domains.cortex.identity import continuity_rebuild as id_mod
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod


def test_verify_p1_step8_identity_projection_boundary() -> None:
    assert verify_p1_step8_identity_projection_boundary_v1() == []


def test_phase03_runner_uses_single_projection_entrypoint() -> None:
    src = inspect.getsource(pr_mod.run_phase_03_identity_v1)
    assert src.count("run_identity_substrate_projection_for_pipeline_v1(") == 1
    assert "finalize_identity_substrate_operator_audit" not in src
    assert "identity_substrate_audit_replay_job_id" not in src
    assert "execute_org_link_replay_job" not in src


def test_identity_projection_receipt_builder_has_no_job_persist() -> None:
    src = inspect.getsource(id_mod.build_identity_substrate_projection_receipt_v1)
    assert "_persist_standalone_audit_job" not in src
    assert "audit_replay_job_id" not in src
