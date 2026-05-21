"""M3 — Celery beat registers ingestion + convergence sweep only."""

from __future__ import annotations

from vector.domains.cortex.execution.scheduling import (
    CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1,
    LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1,
    verify_convergence_sweep_in_celery_beat_v1,
    verify_legacy_substrate_beats_absent_from_celery_beat_v1,
)


def test_celery_beat_has_convergence_sweep_only_for_substrate() -> None:
    assert verify_convergence_sweep_in_celery_beat_v1() == []
    assert verify_legacy_substrate_beats_absent_from_celery_beat_v1() == []


def test_legacy_substrate_beat_task_names_documented() -> None:
    assert "continuity_watchdog" in LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1[0]
    assert "substrate_progression_tick" in LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1[1]


def test_convergence_sweep_beat_key_present() -> None:
    from app.celery_app import celery_app

    beat = dict(celery_app.conf.beat_schedule or {})
    assert CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1 in beat
    assert "cortex-ingestion-scheduler-tick" in beat
    assert len(beat) == 2
