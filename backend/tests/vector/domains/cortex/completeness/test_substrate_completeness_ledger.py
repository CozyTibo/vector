"""Substrate completeness ledger — deterministic stage envelopes + propagation."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.completeness._completeness_common import (
    build_stage_envelope_v1,
    derive_substrate_state_from_stages,
)
from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_degradation_propagation_chain_v1,
)


def test_stage_envelope_digest_stable() -> None:
    a = build_stage_envelope_v1(
        stage_id="ingestion",
        label="Raw exhaust",
        total_objects=100,
        processed_count=90,
        degraded_count=5,
        detail_route="/admin",
    )
    b = build_stage_envelope_v1(
        stage_id="ingestion",
        label="Raw exhaust",
        total_objects=100,
        processed_count=90,
        degraded_count=5,
        detail_route="/admin",
    )
    assert a["stage_receipt_digest"] == b["stage_receipt_digest"]


def test_propagation_chain_from_ingestion_gap() -> None:
    stages = [
        {
            "stage_id": "ingestion",
            "omission_classes": {"partial_api_failure": 2},
        },
        {"stage_id": "canonical", "omission_classes": {}},
        {"stage_id": "traversal", "omission_classes": {}},
    ]
    chain = build_degradation_propagation_chain_v1(stages)
    assert any(c["triggering_omission_class"] == "partial_api_failure" for c in chain)


def test_substrate_state_critical_on_stage() -> None:
    stages = [{"substrate_state": "healthy"}, {"substrate_state": "critical"}]
    assert derive_substrate_state_from_stages(stages) == "critical"


def test_build_ledger_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke with mocked session scalars."""
    from vector.domains.cortex.completeness import substrate_completeness_ledger as ledger_mod

    session = MagicMock()
    session.scalar.return_value = 0
    session.scalars.return_value.all.return_value = []

    monkeypatch.setattr(
        ledger_mod,
        "project_ingestion_completeness_v1",
        lambda *a, **k: build_stage_envelope_v1(
            stage_id="ingestion", label="Raw", total_objects=0, processed_count=0, detail_route="/i"
        ),
    )
    monkeypatch.setattr(
        ledger_mod,
        "project_canonical_completeness_v1",
        lambda *a, **k: build_stage_envelope_v1(
            stage_id="canonical", label="C", total_objects=0, processed_count=0, detail_route="/c"
        ),
    )
    monkeypatch.setattr(
        ledger_mod,
        "project_identity_completeness_v1",
        lambda *a, **k: build_stage_envelope_v1(
            stage_id="identity", label="I", total_objects=0, processed_count=0, detail_route="/id"
        ),
    )
    monkeypatch.setattr(
        ledger_mod,
        "project_graph_completeness_v1",
        lambda *a, **k: build_stage_envelope_v1(
            stage_id="graph", label="G", total_objects=0, processed_count=0, detail_route="/g"
        ),
    )
    monkeypatch.setattr(
        ledger_mod,
        "project_traversal_completeness_v1",
        lambda *a, **k: build_stage_envelope_v1(
            stage_id="traversal", label="T", total_objects=0, processed_count=0, detail_route="/t"
        ),
    )
    monkeypatch.setattr(
        ledger_mod,
        "project_tcre_completeness_v1",
        lambda *a, **k: build_stage_envelope_v1(
            stage_id="tcre", label="R", total_objects=0, processed_count=0, detail_route="/r"
        ),
    )
    out = ledger_mod.build_substrate_completeness_ledger_v1(session, tenant_id=uuid.uuid4())
    assert out["substrate_state"] in ("healthy", "degraded", "critical")
    assert len(out["pipeline_stages"]) == 6
    assert out["ledger_digest"]
