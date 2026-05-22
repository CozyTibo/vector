"""Step 5 A1 validation helpers."""

from __future__ import annotations

from vector.domains.cortex.unlock.step05_identity_backfill import evaluate_a1_org_handles_v1


def test_a1_passes_at_target_count() -> None:
    ok, detail = evaluate_a1_org_handles_v1(
        org_entities_active=12_000,
        entities_upserted=11_000,
        anchors_scanned=19_000,
    )
    assert ok is True
    assert "10000" in detail


def test_a1_passes_wedge_minimum() -> None:
    ok, _ = evaluate_a1_org_handles_v1(
        org_entities_active=500,
        entities_upserted=400,
        anchors_scanned=500,
    )
    assert ok is True


def test_a1_passes_prod_anchor_yield() -> None:
    ok, detail = evaluate_a1_org_handles_v1(
        org_entities_active=7286,
        entities_upserted=5000,
        anchors_scanned=19_961,
    )
    assert ok is True
    assert "prod_anchor_yield" in detail


def test_a1_fails_zero_upsert_and_zero_entities() -> None:
    ok, detail = evaluate_a1_org_handles_v1(
        org_entities_active=0,
        entities_upserted=0,
        anchors_scanned=1000,
    )
    assert ok is False
    assert "entities_upserted=0" in detail
