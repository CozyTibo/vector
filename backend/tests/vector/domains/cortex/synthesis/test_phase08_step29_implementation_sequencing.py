"""P08-29 — implementation sequencing (waves 0–7) + Phase 09 handoff."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.synthesis.normative import PHASE08_STEP_PROGRAM_COUNT
from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
    GP08_SEQ01_GATE_ID_V1,
    PHASE08_SYNTHESIS_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_CRITICAL_PATH_MODULE_CHAIN_V1,
    SYNTHESIS_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1,
    SYNTHESIS_IMPLEMENTATION_WAVE_IDS_V1,
    SYNTHESIS_IMPLEMENTATION_WAVES_ZERO_THROUGH_FIVE_V1,
    SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_LITERAL_V1,
    SYNTHESIS_TRACKER_STEP_WAVE_RANGES_V1,
    build_synthesis_implementation_sequencing_catalog_v1,
    build_synthesis_phase09_readiness_checklist_v1,
    build_synthesis_tracker_step_wave_map_v1,
    evaluate_all_synthesis_implementation_waves_v1,
    evaluate_synthesis_implementation_wave_v1,
    evaluate_synthesis_implementation_waves_v1,
    verify_gp08_seq01_implementation_sequencing_catalog_static,
    verify_gp08_seq02_tracker_wave_mapping_static,
    verify_gp08_seq03_critical_path_modules_static,
    verify_gp08_seq04_waves_zero_through_five_complete_static,
    verify_gp08_seq05_phase09_readiness_handoff_static,
    verify_gp08_seq06_wave_seven_complete_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-implementation-sequencing-plan.md"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_constants_and_spec_ref() -> None:
    assert PHASE08_SYNTHESIS_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION >= 1
    assert "phase-08-implementation-sequencing-plan" in SYNTHESIS_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1
    assert SYNTHESIS_IMPLEMENTATION_WAVE_IDS_V1 == ("0", "1", "2", "3", "4", "5", "6", "7")
    assert SYNTHESIS_IMPLEMENTATION_WAVES_ZERO_THROUGH_FIVE_V1 == ("0", "1", "2", "3", "4", "5")
    assert len(SYNTHESIS_CRITICAL_PATH_MODULE_CHAIN_V1) == 10
    assert SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_LITERAL_V1 == "SynthesisIntelligenceArtifactV1"


def test_sequencing_doc_present() -> None:
    root = _repo_root()
    path = root / "DOCS" / "cortex" / "synthesis" / "phase-08-implementation-sequencing-plan.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Sequencing waves" in text
    assert "| **0** |" in text
    assert "anti_goals → job_contract" in text


def test_tracker_wave_map_covers_35_steps() -> None:
    rows = build_synthesis_tracker_step_wave_map_v1()
    assert len(rows) == PHASE08_STEP_PROGRAM_COUNT == 35
    assert int(rows[0]["tracker_step"]) == 1
    assert int(rows[-1]["tracker_step"]) == 35
    assert rows[0]["wave_label"] == SYNTHESIS_TRACKER_STEP_WAVE_RANGES_V1[0][2]


def test_all_seq_oracles_pass() -> None:
    assert verify_gp08_seq01_implementation_sequencing_catalog_static()["id"] == GP08_SEQ01_GATE_ID_V1
    assert verify_gp08_seq01_implementation_sequencing_catalog_static()["passed"] is True
    assert verify_gp08_seq02_tracker_wave_mapping_static()["passed"] is True
    assert verify_gp08_seq03_critical_path_modules_static()["passed"] is True
    assert verify_gp08_seq04_waves_zero_through_five_complete_static()["passed"] is True
    assert verify_gp08_seq05_phase09_readiness_handoff_static()["passed"] is True
    assert verify_gp08_seq06_wave_seven_complete_static()["passed"] is True


def test_waves_zero_through_five_complete() -> None:
    for wid in SYNTHESIS_IMPLEMENTATION_WAVES_ZERO_THROUGH_FIVE_V1:
        wave = evaluate_synthesis_implementation_wave_v1(wid)
        assert wave["passed"] is True, wave
    assert evaluate_synthesis_implementation_waves_v1()["passed"] is True


def test_wave_six_sequencing_meta_passes() -> None:
    wave = evaluate_synthesis_implementation_wave_v1("6")
    assert wave["passed"] is True, wave


def test_wave_seven_pipeline_complete() -> None:
    wave = evaluate_synthesis_implementation_wave_v1("7")
    assert wave["passed"] is True, wave


def test_catalog_and_phase09_checklist() -> None:
    cat = build_synthesis_implementation_sequencing_catalog_v1()
    assert cat["all_waves_0_5_passed"] is True
    assert cat["phase09_readiness_passed"] is True
    assert cat["all_waves_passed"] is True
    p09 = build_synthesis_phase09_readiness_checklist_v1()
    assert all(item["passed"] for item in p09)
    assert evaluate_all_synthesis_implementation_waves_v1()["passed"] is True
