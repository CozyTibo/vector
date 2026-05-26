"""Phase C3 — unified continuity audit snapshot."""

from __future__ import annotations

import uuid
from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot import (
    AUDIT_SNAPSHOT_SURFACE_KIND,
    PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
    build_continuity_audit_snapshot_v1,
    format_continuity_audit_snapshot_text_v1,
    summarize_p0_baseline_steps_v1,
)


def test_summarize_baseline_steps_reads_step_keys() -> None:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        default_repo_root_v1,
    )

    repo = default_repo_root_v1()
    rollup = summarize_p0_baseline_steps_v1(repo_root=repo, baseline_date="2026-05-22")
    assert rollup["baseline_present"] is True
    assert rollup["step_count"] >= 5


def test_format_snapshot_text_includes_panel_and_sql() -> None:
    snapshot = {
        "tenant_id": str(uuid.uuid4()),
        "generated_at": "2026-05-23T00:00:00+00:00",
        "canonical_entrypoint": "backend/scripts/continuity_audit_snapshot.py",
        "panel_text": "=== Cortex Continuity Proof Panel (AA1–AA7) ===\nAA1",
        "substrate_sql": {"lease": {"obligation_minus_target": 0, "obligation_epoch_gap_ok": True}},
    }
    text = format_continuity_audit_snapshot_text_v1(snapshot)
    assert "AA1" in text
    assert "Substrate SQL" in text


def test_build_snapshot_monkeypatched(monkeypatch) -> None:
    tenant_id = uuid.uuid4()

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot."
        "build_continuity_proof_panel_v1",
        lambda *_a, **_k: {
            "surface_kind": "continuity_proof_panel",
            "summary": {"fail_count": 0, "pass_count": 7, "m3_autonomously_alive": True},
            "gates": {},
            "gate_order": [],
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot."
        "format_continuity_proof_panel_text_v1",
        lambda panel: "PANEL",
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot."
        "build_substrate_sql_snapshot_v1",
        lambda *_a, **_k: {
            "surface_kind": "continuity_substrate_sql_snapshot",
            "obligation_epoch_gap_ok": True,
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot."
        "snapshot_phase08_empty_scope_truth_v1",
        lambda *_a, **_k: {"phase_c1_schema_version": 1},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot."
        "snapshot_c2_synthesis_scope_caps_v1",
        lambda *_a, **_k: {"phase_c2_schema_version": 1},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot."
        "build_cleanup_freeze_snapshot_v1",
        lambda *_a, **_k: {"surface_kind": "continuity_cleanup_freeze", "wiring": {"wiring_ok": True}},
    )

    out = build_continuity_audit_snapshot_v1(None, tenant_id=tenant_id)  # type: ignore[arg-type]
    assert out["surface_kind"] == AUDIT_SNAPSHOT_SURFACE_KIND
    assert out["phase_c3_schema_version"] == PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION
    assert "c1_phase08_empty_scope_truth" in out["phase_snapshots"]
    assert len(out["deprecated_proof_scripts"]) >= 10
    assert out["cleanup_freeze"]["surface_kind"] == "continuity_cleanup_freeze"
