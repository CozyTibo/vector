"""Phase 03 Step 9 — deterministic canonical entity id + provider identity projection."""

from __future__ import annotations

import uuid

from vector.domains.cortex.canonical.identity_runtime import (
    DEFAULT_PHASE04_BOUNDARY,
    IDENTITY_RUNTIME_SCHEMA_VERSION,
    PHASE03_CANONICAL_ENTITY_NAMESPACE,
    deterministic_canonical_entity_id,
    provider_identity_from_logical_key,
)


def test_identity_runtime_schema_version() -> None:
    assert IDENTITY_RUNTIME_SCHEMA_VERSION >= 1


def test_phase04_boundary_defaults_declare_phase_04_authority() -> None:
    assert DEFAULT_PHASE04_BOUNDARY["human_identity_resolution"] == "phase_04_only"
    assert DEFAULT_PHASE04_BOUNDARY["linkage_merge_authority"] == "none"


def test_provider_identity_strips_scope_keys() -> None:
    lk = {
        "tenant_id": "t",
        "mapping_bundle_id": "b",
        "connector": "slack",
        "conversation_provider_id": "c1",
        "message_provider_id": "m1",
    }
    prof = provider_identity_from_logical_key(lk)
    assert "tenant_id" not in prof
    assert "mapping_bundle_id" not in prof
    assert prof["connector"] == "slack"


def test_deterministic_canonical_entity_id_stable() -> None:
    tid = uuid.uuid4()
    h = "abc" * 20
    a = deterministic_canonical_entity_id(
        tenant_id=tid,
        bundle_id="bundle.x",
        canonical_object_kind="message",
        provider_identity_hash=h,
    )
    b = deterministic_canonical_entity_id(
        tenant_id=tid,
        bundle_id="bundle.x",
        canonical_object_kind="message",
        provider_identity_hash=h,
    )
    assert a == b


def test_namespace_is_fixed_derivation() -> None:
    assert str(PHASE03_CANONICAL_ENTITY_NAMESPACE).count("-") == 4
