"""Phase 08 Step 35 — constitutional freeze sign-off (**P08-FINAL-FREEZE**)."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.synthesis.doctrine_catalog import build_synthesis_program_doctrine_catalog_v1
from vector.domains.cortex.synthesis.normative import (
    PHASE08_CONSTITUTIONAL_FREEZE_BUNDLE_V1,
    PHASE08_DOCTRINE_FREEZE_STATUS_V1,
    build_phase08_normative_program_document_v1,
)
from vector.domains.cortex.synthesis.synthesis_constitutional_freeze import (
    GP08_FREEZE01_GATE_ID_V1,
    P08_FINAL_FREEZE_BUNDLE_ID_V1,
    PHASE08_DOCTRINE_FREEZE_STATUS_V1 as FREEZE_STATUS,
    build_synthesis_constitutional_freeze_catalog_v1,
    build_synthesis_constitutional_freeze_signoff_snapshot_v1,
    verify_gp08_freeze01_constitutional_freeze_static,
)
from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
    verify_gp08_seq06_wave_seven_complete_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "synthesis" / "PHASE08_CONSTITUTIONAL_CHANGELOG.md").is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_freeze_constants() -> None:
    assert P08_FINAL_FREEZE_BUNDLE_ID_V1 == PHASE08_CONSTITUTIONAL_FREEZE_BUNDLE_V1
    assert FREEZE_STATUS == PHASE08_DOCTRINE_FREEZE_STATUS_V1


def test_changelog_contains_final_freeze_bundle() -> None:
    text = (_repo_root() / "DOCS/cortex/synthesis/PHASE08_CONSTITUTIONAL_CHANGELOG.md").read_text(
        encoding="utf-8",
    )
    assert P08_FINAL_FREEZE_BUNDLE_ID_V1 in text


def test_gp08_freeze01_gate_passes() -> None:
    out = verify_gp08_freeze01_constitutional_freeze_static()
    assert out["id"] == GP08_FREEZE01_GATE_ID_V1
    assert out["passed"] is True, out


def test_wave_seven_complete() -> None:
    assert verify_gp08_seq06_wave_seven_complete_static()["passed"] is True


def test_constitutional_freeze_catalog_and_signoff() -> None:
    catalog = build_synthesis_constitutional_freeze_catalog_v1()
    assert catalog["gate_id"] == GP08_FREEZE01_GATE_ID_V1
    assert catalog["signoff_passed"] is True
    snap = build_synthesis_constitutional_freeze_signoff_snapshot_v1()
    assert snap["constitutional_freeze_passed"] is True
    assert snap["constitutional_freeze_bundle"] == P08_FINAL_FREEZE_BUNDLE_ID_V1


def test_program_catalog_exposes_freeze_banner() -> None:
    program = build_synthesis_program_doctrine_catalog_v1()
    assert program["doctrine_freeze_status"] == PHASE08_DOCTRINE_FREEZE_STATUS_V1
    assert program["freeze_banner"]["bundle_id"] == P08_FINAL_FREEZE_BUNDLE_ID_V1
    doc = build_phase08_normative_program_document_v1()
    assert doc["constitutional_freeze_bundle"] == P08_FINAL_FREEZE_BUNDLE_ID_V1
