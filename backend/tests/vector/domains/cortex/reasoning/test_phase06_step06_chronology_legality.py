"""P06-06 — Chronology legality (projection + CHRON‑FORB‑1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_legality import (
    CHRONOLOGY_LEGALITY_CLASSES,
    PHASE06_CHRONOLOGY_LEGALITY_RUNTIME_SCHEMA_VERSION,
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    ChronologyLegalityError,
    default_reasoning_policy_pack_path,
    load_default_reasoning_policy_pack,
    project_chronology_legality_class_v1,
    should_emit_cd_chron_from_policy,
    validate_chron_forb1,
    verify_default_policy_pack_digest,
    verify_gp06_chron01_default_policy_rows_static,
    verify_gp06_chron02_projection_closure_static,
    find_chronology_skew_projection_row,
)


def test_chronology_legality_runtime_schema_version() -> None:
    assert PHASE06_CHRONOLOGY_LEGALITY_RUNTIME_SCHEMA_VERSION >= 1


def test_default_fixture_digest() -> None:
    verify_default_policy_pack_digest()


def test_strict_clean_projects_strict() -> None:
    pack = load_default_reasoning_policy_pack()
    c, idx, part = project_chronology_legality_class_v1(
        {
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": [],
        },
        pack,
    )
    assert c == "chronology_strict"
    assert part is False
    assert isinstance(idx, int)


def test_unresolved_clean_projects_unresolved() -> None:
    pack = load_default_reasoning_policy_pack()
    c, _, _ = project_chronology_legality_class_v1(
        {
            "replay_safe_ordering": "unresolved",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": [],
        },
        pack,
    )
    assert c == "chronology_unresolved"


def test_chron_forb1_rejects_unresolved_strict() -> None:
    with pytest.raises(ChronologyLegalityError, match="CHRON-FORB-1"):
        validate_chron_forb1(
            "unresolved",
            "chronology_strict",
            skew_detected=False,
            partitioned_exception_applied=False,
        )


def test_cd_chron_flag_partial_with_default_pack() -> None:
    pack = load_default_reasoning_policy_pack()
    assert should_emit_cd_chron_from_policy(chronology_legality_class="chronology_partial", policy=pack) is True
    assert should_emit_cd_chron_from_policy(chronology_legality_class="chronology_strict", policy=pack) is False


def test_find_row_excludes_partitioned_from_primary_scan() -> None:
    rows = [
        {
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "chronology_legality_class": "chronology_unresolved",
        },
        {
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "chronology_legality_class": "chronology_strict",
            "partitioned_exception": True,
        },
    ]
    base = find_chronology_skew_projection_row(
        rows,
        replay_safe_ordering="strict",
        skew_detected=False,
        late_arrival=False,
        export_sequence_conflict=False,
    )
    assert base is not None
    assert base["chronology_legality_class"] == "chronology_unresolved"
    exc_row = find_chronology_skew_projection_row(
        rows,
        replay_safe_ordering="strict",
        skew_detected=False,
        late_arrival=False,
        export_sequence_conflict=False,
        partitioned_exception=True,
    )
    assert exc_row is not None
    assert exc_row["chronology_legality_class"] == "chronology_strict"


def test_partitioned_override_swaps_class() -> None:
    pack = {
        "chronology_skew_projection_v1": [
            {
                "replay_safe_ordering": "strict",
                "skew_detected": False,
                "late_arrival": False,
                "export_sequence_conflict": False,
                "chronology_legality_class": "chronology_unresolved",
            },
            {
                "replay_safe_ordering": "strict",
                "skew_detected": False,
                "late_arrival": False,
                "export_sequence_conflict": False,
                "chronology_legality_class": "chronology_strict",
                "partitioned_exception": True,
            },
        ],
        "degradation_thresholds": {},
    }
    c, _, part = project_chronology_legality_class_v1(
        {
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": ["partitioned"],
        },
        pack,
    )
    assert c == "chronology_strict"
    assert part is True


def test_no_match_raises() -> None:
    pack: dict[str, list[object]] = {"chronology_skew_projection_v1": []}
    with pytest.raises(ChronologyLegalityError, match="no chronology"):
        project_chronology_legality_class_v1(
            {
                "replay_safe_ordering": "strict",
                "skew_detected": False,
                "late_arrival": False,
                "export_sequence_conflict": False,
            },
            pack,
        )


def test_verify_gp06_chron01_static_passes() -> None:
    assert verify_gp06_chron01_default_policy_rows_static()["passed"] is True


def test_verify_gp06_chron02_static_passes() -> None:
    assert verify_gp06_chron02_projection_closure_static()["passed"] is True


def test_digest_constant_documented() -> None:
    assert len(TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST) == 64


def test_chronology_law_classes_match_doctrine() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "chronology-legality-law.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            for c in CHRONOLOGY_LEGALITY_CLASSES:
                assert f"`{c}`" in text
            return
    pytest.fail("chronology-legality-law.md not found")


def test_state_machine_doc_references_projection() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "chronology-replay-legality-state-machine.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "ChronologyLegalityProjectionV1" in text
            assert "CHRON" in text and "FORB" in text
            return
    pytest.fail("chronology-replay-legality-state-machine.md not found")


def test_default_pack_path_resolves() -> None:
    p = default_reasoning_policy_pack_path()
    assert p.name == "ReasoningPolicyPackV1_Default.json"
