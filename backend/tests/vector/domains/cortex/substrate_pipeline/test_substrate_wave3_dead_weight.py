"""Wave 3 — dead Celery tasks, orphan auto-promotion, debounce settings removed."""

from __future__ import annotations

from app.celery_app import celery_app
from vector.domains.cortex.execution.scheduling import verify_wave3_dead_weight_v1
from vector.domains.cortex.identity.link_ledger_metadata import build_link_ledger_pointer_section
from vector.settings import Settings


def test_verify_wave3_dead_weight_v1() -> None:
    assert verify_wave3_dead_weight_v1() == []


def test_legacy_link_celery_tasks_not_registered() -> None:
    assert "vector.cortex.identity.regenerate_link_candidates" not in celery_app.tasks
    assert "vector.cortex.identity.replay_authoritative_links" not in celery_app.tasks


def test_wave3_settings_absent_from_settings_model() -> None:
    removed = (
        "cortex_post_ingestion_substrate_refresh_debounce_seconds",
        "cortex_post_ingestion_substrate_refresh_max_wait_seconds",
        "cortex_post_ingestion_backpressure_extra_debounce_seconds",
        "cortex_orphan_stitching_auto_schedule_promotion",
    )
    for name in removed:
        assert name not in Settings.model_fields


def test_link_ledger_metadata_wave3_tombstones() -> None:
    doc = build_link_ledger_pointer_section()
    assert doc["celery_task_regenerate_link_candidates"] is None
    assert "vector.cortex.identity.regenerate_link_candidates" in doc["legacy_celery_tasks_removed_wave3"]
