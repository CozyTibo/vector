"""Notion database deterministic transform routing."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.transform_routing_registry import (
    TRANSFORM_ROUTING_REGISTRY_VERSION,
    registration_for_pair,
    transform_routing_table,
)
from vector.domains.cortex.canonical.transform_runtime import (
    MaterializeError,
    _build_lineage_specs,
)


def test_registry_includes_notion_database() -> None:
    table = transform_routing_table()
    assert ("notion", "notion.database") in table
    kind, _rule = table[("notion", "notion.database")]
    assert kind == CanonicalObjectKind.PAGE
    reg = registration_for_pair("notion", "notion.database")
    assert reg is not None
    assert reg.oracle_fixture_id == "p03_oracle_notion_database_v1"
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 4


def test_notion_database_page_key_and_schema_lineage() -> None:
    tenant = uuid.uuid4()
    bundle_id = "bundle.phase03.step03.logical_keys.v1"
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.database",
        external_id="db_roadmap_q3",
        source_identity_key="notion:notion.database:db_roadmap_q3",
        source_revision_key="rev-db-1",
        payload_body={
            "database": {
                "id": "db_roadmap_q3",
                "title": [{"plain_text": "Roadmap Q3"}],
                "properties": {
                    "Name": {"type": "title"},
                    "Owner": {"type": "people"},
                    "DependsOn": {"type": "relation"},
                },
            }
        },
    )
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.PAGE,
        rule_base="rule.registry.notion.notion.database",
    )
    assert lk == {
        "tenant_id": str(tenant),
        "mapping_bundle_id": bundle_id,
        "connector": "notion",
        "page_provider_id": "db_roadmap_q3",
    }
    assert emitted["schema_property_names"] == ["DependsOn", "Name", "Owner"]
    assert emitted["relation_property_names"] == ["DependsOn"]
    assert emitted["title"] == "Roadmap Q3"
    assert any(s.field_path == "attributes.schema_property_names" for s in specs)
    assert any(s.field_path == "attributes.relation_property_names" for s in specs)


def test_notion_database_requires_provider_id() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.database",
        external_id="",
        source_identity_key="notion:notion.database:x",
        source_revision_key="rev-db-1",
        payload_body={"database": {"properties": {}}},
    )
    with pytest.raises(MaterializeError, match="page_missing_provider_id"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.PAGE,
            rule_base="rule.registry.notion.notion.database",
        )
