"""Tests for war-room step-1 baseline snapshot contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vector.domains.cortex.unlock.baseline_snapshot import (
    BASELINE_REQUIRED_TOP_LEVEL_KEYS,
    extract_alive_baseline_metrics,
    validate_baseline_snapshot,
)

_REPO_ROOT = Path(__file__).resolve().parents[6]
FIXTURE = _REPO_ROOT / "DOCS/audits/baselines/fizzer_step01_2026-05-21.json"


@pytest.fixture
def fizzer_step01_payload() -> dict:
    if not FIXTURE.is_file():
        pytest.skip(f"baseline fixture missing: {FIXTURE}")
    return json.loads(FIXTURE.read_text())


def test_fixture_has_required_top_level_keys(fizzer_step01_payload: dict) -> None:
    assert BASELINE_REQUIRED_TOP_LEVEL_KEYS <= fizzer_step01_payload.keys()


def test_validate_baseline_snapshot_accepts_fizzer_fixture(fizzer_step01_payload: dict) -> None:
    validate_baseline_snapshot(fizzer_step01_payload)


def test_validate_baseline_snapshot_rejects_incomplete() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        validate_baseline_snapshot({"tenant_id": "x"})


def test_extract_alive_baseline_metrics(fizzer_step01_payload: dict) -> None:
    metrics = extract_alive_baseline_metrics(fizzer_step01_payload)
    assert metrics["tenant_id"] == "c08ef32b-f89a-40f6-9566-e19b5329436f"
    assert metrics["A1_org_entities_active"] == 0
    assert metrics["A2_authoritative_links"] == 0
    assert metrics["primary_bundle_id"] == "bundle.phase03.step03.logical_keys.v1"
