"""Phase 03 Step 10 — canonical replay divergence classification + runtime constants."""

from __future__ import annotations

from types import SimpleNamespace

from vector.domains.cortex.canonical.ontology import ONTOLOGY_SCHEMA_VERSION, build_phase03_step01_ontology_public_document
from vector.domains.cortex.canonical.replay_runtime import (
    REPLAY_DIVERGENCE_CLASSES,
    REPLAY_RUNTIME_SCHEMA_VERSION,
    classify_replay_divergence,
)
from vector.domains.cortex.canonical.transform_runtime import ENGINE_BUILD_REF


def _resolved(
    *,
    lk_hash: str = "lk1",
    snap_hash: str = "s1",
    kind_value: str = "issue",
    payload_hash: str = "ph1",
) -> SimpleNamespace:
    return SimpleNamespace(
        logical_key_hash=lk_hash,
        emitted_snapshot_hash=snap_hash,
        kind=SimpleNamespace(value=kind_value),
        raw=SimpleNamespace(payload_hash=payload_hash),
    )


def test_replay_runtime_schema_version() -> None:
    assert REPLAY_RUNTIME_SCHEMA_VERSION >= 1
    assert "C0" in REPLAY_DIVERGENCE_CLASSES


def test_classify_c0_first_materialization() -> None:
    div, _detail = classify_replay_divergence(
        job_kind="rebuild",
        prior=None,
        resolved=_resolved(),
        tenant_trust_state="healthy",
        source_bundle_id=None,
        pinned_bundle_id="b1",
        compatibility_edge_present=True,
    )
    assert div == "C0"


def test_classify_c0_stored_matches_oracle() -> None:
    prior = SimpleNamespace(
        logical_key_hash="lk1",
        emitted_snapshot_hash="s1",
        engine_build_ref=ENGINE_BUILD_REF,
        canonical_object_kind="issue",
    )
    div, _detail = classify_replay_divergence(
        job_kind="rebuild",
        prior=prior,
        resolved=_resolved(),
        tenant_trust_state="healthy",
        source_bundle_id=None,
        pinned_bundle_id="b1",
        compatibility_edge_present=True,
    )
    assert div == "C0"


def test_classify_c3_blocking_trust() -> None:
    prior = SimpleNamespace(
        logical_key_hash="lk0",
        emitted_snapshot_hash="s0",
        engine_build_ref=ENGINE_BUILD_REF,
        canonical_object_kind="issue",
    )
    div, detail = classify_replay_divergence(
        job_kind="rebuild",
        prior=prior,
        resolved=_resolved(lk_hash="lk2", snap_hash="s2"),
        tenant_trust_state="corrupted",
        source_bundle_id=None,
        pinned_bundle_id="b1",
        compatibility_edge_present=True,
    )
    assert div == "C3"
    assert detail["trust_state"] == "corrupted"


def test_classify_c2_regeneration_drift() -> None:
    prior = SimpleNamespace(
        logical_key_hash="lk0",
        emitted_snapshot_hash="s0",
        engine_build_ref=ENGINE_BUILD_REF,
        canonical_object_kind="issue",
    )
    div, detail = classify_replay_divergence(
        job_kind="regeneration",
        prior=prior,
        resolved=_resolved(lk_hash="lk2", snap_hash="s2"),
        tenant_trust_state="healthy",
        source_bundle_id="bundle.a",
        pinned_bundle_id="bundle.b",
        compatibility_edge_present=True,
    )
    assert div == "C2"
    assert detail["note"] == "expected_regeneration_or_mapping_drift"


def test_classify_c4_rebuild_unexpected_drift() -> None:
    prior = SimpleNamespace(
        logical_key_hash="lk0",
        emitted_snapshot_hash="s0",
        engine_build_ref=ENGINE_BUILD_REF,
        canonical_object_kind="issue",
    )
    div, detail = classify_replay_divergence(
        job_kind="rebuild",
        prior=prior,
        resolved=_resolved(lk_hash="lk2", snap_hash="s2"),
        tenant_trust_state="healthy",
        source_bundle_id=None,
        pinned_bundle_id="b1",
        compatibility_edge_present=True,
    )
    assert div == "C4"
    assert "unexpected_projection_drift" in detail["note"]


def test_classify_c5_missing_compatibility_edge() -> None:
    prior = SimpleNamespace(
        logical_key_hash="lk0",
        emitted_snapshot_hash="s0",
        engine_build_ref=ENGINE_BUILD_REF,
        canonical_object_kind="issue",
    )
    div, detail = classify_replay_divergence(
        job_kind="regeneration",
        prior=prior,
        resolved=_resolved(lk_hash="lk2", snap_hash="s2"),
        tenant_trust_state="healthy",
        source_bundle_id="bundle.a",
        pinned_bundle_id="bundle.b",
        compatibility_edge_present=False,
    )
    assert div == "C5"


def test_ontology_includes_replay_pointer_section() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == ONTOLOGY_SCHEMA_VERSION
    assert doc["replay_job_run_route"]
    assert doc["replay_divergence_taxonomy"]
    assert doc["replay_runtime_doctrine_anchors"]
