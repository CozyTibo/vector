"""Notion block deterministic transform routing."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.transform_routing_registry import (
    TRANSFORM_ROUTING_REGISTRY_VERSION,
    registration_for_pair,
    transform_routing_table,
)
from vector.domains.cortex.canonical.transform_runtime import _build_lineage_specs


def test_registry_includes_notion_block() -> None:
    table = transform_routing_table()
    assert ("notion", "notion.block") in table
    kind, _rule = table[("notion", "notion.block")]
    assert kind == CanonicalObjectKind.PAGE
    reg = registration_for_pair("notion", "notion.block")
    assert reg is not None
    assert reg.oracle_fixture_id == "p03_oracle_notion_block_v1"
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 5


def test_notion_block_lineage_hierarchy_and_excerpt() -> None:
    tenant = uuid.uuid4()
    bundle_id = "bundle.phase03.step03.logical_keys.v1"
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.block",
        external_id="blk_plan_001",
        source_identity_key="notion:notion.block:blk_plan_001",
        source_revision_key="rev-block-1",
        query_params={"start_cursor": "curs_007"},
        payload_body={
            "block": {
                "id": "blk_plan_001",
                "type": "paragraph",
                "parent_id": "page_001",
                "paragraph": {
                    "rich_text": [
                        {"plain_text": "Execution plan "},
                        {"plain_text": "Q3"},
                    ]
                },
            }
        },
    )
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.PAGE,
        rule_base="rule.registry.notion.notion.block",
    )
    assert lk == {
        "tenant_id": str(tenant),
        "mapping_bundle_id": bundle_id,
        "connector": "notion",
        "page_provider_id": "blk_plan_001",
    }
    assert emitted["block_type"] == "paragraph"
    assert emitted["parent_ref"] == "parent_id:page_001"
    assert emitted["rich_text_excerpt"] == "Execution plan Q3"
    assert emitted["sibling_cursor_hint"] == "curs_007"
    assert any(s.field_path == "attributes.parent_ref" for s in specs)
    assert any(s.field_path == "attributes.rich_text_excerpt" for s in specs)
