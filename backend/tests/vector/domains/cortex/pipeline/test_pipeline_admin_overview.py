"""Pipeline overview helpers."""

from vector.domains.cortex.pipeline.pipeline_admin_overview import _ingestion_trigger_kind


def test_ingestion_trigger_kind_scheduled() -> None:
    assert _ingestion_trigger_kind(source_trigger="scheduled_lane", replay_mode=False) == "scheduled"
    assert _ingestion_trigger_kind(source_trigger="scheduled", replay_mode=False) == "scheduled"


def test_ingestion_trigger_kind_manual() -> None:
    assert _ingestion_trigger_kind(source_trigger="manual_admin", replay_mode=False) == "manual"
    assert (
        _ingestion_trigger_kind(source_trigger="pipeline_run_from_ingestion", replay_mode=False)
        == "manual"
    )


def test_ingestion_trigger_kind_replay() -> None:
    assert _ingestion_trigger_kind(source_trigger="manual_admin", replay_mode=True) == "replay"
    assert _ingestion_trigger_kind(source_trigger="manual_admin_replay", replay_mode=False) == "replay"
