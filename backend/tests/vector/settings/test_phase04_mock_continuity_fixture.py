"""P04-20 — Phase 04 continuity sidecar on generated mock datasets."""

from __future__ import annotations

from mock_connectors.fixtures.company_generator import dataset_to_json_dict, generate_dataset
from mock_connectors.scripts.validate_mock_dataset import _check_phase04_continuity_fixture


def test_generated_dataset_includes_phase04_continuity_fixture() -> None:
    ds = generate_dataset(42)
    data = dataset_to_json_dict(ds)
    cf = data.get("continuity_fixture")
    assert isinstance(cf, dict)
    assert cf.get("schema_version") == "phase04_mock_fixture_v1"
    assert isinstance(cf.get("scenario_key"), str)


def test_phase04_continuity_checks_pass_on_default_dataset() -> None:
    ds = generate_dataset(7)
    data = dataset_to_json_dict(ds)
    errs = _check_phase04_continuity_fixture(data, data["linear"])
    assert errs == []
