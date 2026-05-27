"""Extraction version in hash-based revision keys (production evolution Class C)."""

from __future__ import annotations

from vector.domains.cortex.ingestion.live_idempotency import derive_source_revision_key


def test_extraction_version_changes_hash_revision() -> None:
    body_v1 = {
        "connector_type": "linear",
        "issue": {"id": "iss-1", "title": "A"},
        "ingestion_version": {"extraction": 1},
    }
    body_v2 = {
        "connector_type": "linear",
        "issue": {"id": "iss-1", "title": "A"},
        "ingestion_version": {"extraction": 2},
    }
    r1 = derive_source_revision_key(body_v1)
    r2 = derive_source_revision_key(body_v2)
    assert r1.startswith("extract:1:hash:")
    assert r2.startswith("extract:2:hash:")
    assert r1 != r2


def test_provider_token_wins_over_extraction() -> None:
    body = {
        "issue": {"id": "x", "updatedAt": "2026-05-01T00:00:00Z"},
        "ingestion_version": {"extraction": 3},
    }
    assert derive_source_revision_key(body).startswith("provider:")
