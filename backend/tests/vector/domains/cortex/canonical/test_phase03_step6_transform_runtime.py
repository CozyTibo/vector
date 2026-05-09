"""Phase 03 Step 6 — deterministic hash + transform runtime constants."""

from __future__ import annotations

from vector.domains.cortex.canonical.transform_runtime import (
    ENGINE_BUILD_REF,
    TRANSFORM_RUNTIME_SCHEMA_VERSION,
    canonical_json_hash,
    stub_routing_pairs,
)


def test_canonical_json_hash_stable_across_key_order() -> None:
    a = {"z": 1, "nested": {"b": 2, "a": 3}}
    b = {"nested": {"a": 3, "b": 2}, "z": 1}
    assert canonical_json_hash(a) == canonical_json_hash(b)


def test_transform_runtime_constants() -> None:
    assert TRANSFORM_RUNTIME_SCHEMA_VERSION == 10
    assert ENGINE_BUILD_REF


def test_stub_routing_pairs_support_resource_type_scope() -> None:
    notion_block = stub_routing_pairs(resource_type="notion.block")
    assert notion_block == [("notion", "notion.block")]
    notion_all = stub_routing_pairs(connector="notion")
    assert ("notion", "notion.page") in notion_all
    assert ("notion", "notion.database_row") in notion_all
    assert ("slack", "slack.message_reply") in stub_routing_pairs(connector="slack")
    assert ("github", "github.repository") in stub_routing_pairs(connector="github")
