"""Cleanup / freeze policies — proof collapse, AA7 hold, per-island sign-off, registry inspect."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_cleanup_freeze import (
    aa7_wedge_free_ack_allowed_v1,
    verify_cleanup_freeze_wiring_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
    CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1,
    deprecated_continuity_proof_script_names_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    evaluate_aa7_no_wedge_scripts_v1,
)

REPO_ROOT = Path(__file__).resolve().parents[6]


def test_cleanup_freeze_wiring_ok() -> None:
    wiring = verify_cleanup_freeze_wiring_v1(repo_root=REPO_ROOT)
    assert wiring["wiring_ok"] is True
    assert wiring["deprecated_proof_script_count"] >= 20


def test_deprecated_catalog_excludes_canonical_snapshot() -> None:
    names = deprecated_continuity_proof_script_names_v1(
        scripts_dir=REPO_ROOT / "backend" / "scripts"
    )
    assert CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1 not in names
    assert "continuity_p0_phase_d5_legacy_coordinator_enqueue_deletion_proof.py" in names


def test_aa7_fails_during_hold_without_ops_log() -> None:
    gate = evaluate_aa7_no_wedge_scripts_v1(
        ops_log_text=None,
        wedge_free_ack=False,
        aa_hold_active=True,
        wedge_free_ack_allowed=False,
    )
    assert gate["verdict"] == "FAIL"
    assert gate["detail"] == "wedge_scripts_banned_during_48h_hold"


def test_aa7_rejects_wedge_ack_during_daily_hold() -> None:
    gate = evaluate_aa7_no_wedge_scripts_v1(
        ops_log_text="clean ops log without wedge",
        wedge_free_ack=True,
        aa_hold_active=True,
        wedge_free_ack_allowed=False,
    )
    assert gate["verdict"] == "FAIL"
    assert gate["detail"] == "wedge_free_ack_not_allowed_during_hold"


def test_aa7_wedge_ack_only_at_clock_start() -> None:
    assert aa7_wedge_free_ack_allowed_v1(aa_hold_active=True, at_clock_start=True) is True
    assert aa7_wedge_free_ack_allowed_v1(aa_hold_active=True, at_clock_start=False) is False
    assert aa7_wedge_free_ack_allowed_v1(aa_hold_active=False, at_clock_start=False) is True
