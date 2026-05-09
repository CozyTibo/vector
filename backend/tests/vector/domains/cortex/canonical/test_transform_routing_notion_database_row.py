"""Notion database_row deterministic transform routing."""

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


def test_registry_includes_notion_database_row() -> None:
    table = transform_routing_table()
    assert ("notion", "notion.database_row") in table
    kind, _rule = table[("notion", "notion.database_row")]
    assert kind == CanonicalObjectKind.DATABASE_ROW
    reg = registration_for_pair("notion", "notion.database_row")
    assert reg is not None
    assert reg.oracle_fixture_id == "p03_oracle_notion_database_row_v1"
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 3


def test_database_row_logical_key_and_relation_lineage() -> None:
    tenant = uuid.uuid4()
    bundle_id = "bundle.phase03.step03.logical_keys.v1"
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.database_row",
        external_id="row_launch_plan_001",
        source_identity_key="notion:notion.database_row:row_launch_plan_001",
        source_revision_key="rev-002",
        payload_body={
            "row": {
                "id": "row_launch_plan_001",
                "parent": {"type": "database_id", "database_id": "db_roadmap_q3"},
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Launch plan"}],
                    },
                    "DependsOn": {
                        "type": "relation",
                        "relation": [{"id": "row_dep_1"}, {"id": "row_dep_2"}, {"id": "row_dep_1"}],
                    },
                },
            }
        },
    )
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.DATABASE_ROW,
        rule_base="rule.registry.notion.notion.database_row",
    )
    assert lk == {
        "tenant_id": str(tenant),
        "mapping_bundle_id": bundle_id,
        "connector": "notion",
        "database_provider_id": "db_roadmap_q3",
        "row_provider_id": "row_launch_plan_001",
    }
    assert emitted["relation_refs"] == ["row_dep_1", "row_dep_2"]
    assert emitted["title"] == "Launch plan"
    assert any(s.field_path == "logical_key" for s in specs)
    assert any(s.field_path == "attributes.relation_refs" for s in specs)


def test_database_row_requires_database_id() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.database_row",
        external_id="row_launch_plan_001",
        source_identity_key="notion:notion.database_row:row_launch_plan_001",
        source_revision_key="rev-002",
        payload_body={"row": {"id": "row_launch_plan_001", "parent": {"type": "workspace"}}},
    )
    with pytest.raises(MaterializeError, match="database_row_missing_database_id"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.DATABASE_ROW,
            rule_base="rule.registry.notion.notion.database_row",
        )
