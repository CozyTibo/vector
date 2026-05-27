"""Canon mappers for Linear teams, cycles, labels, initiatives, and issue relations."""

from __future__ import annotations

import uuid

from vector.domains.cortex.canon.mapper_registry import mapper_for_resource_type
from vector.domains.cortex.canon.resource_type_registry import (
    entity_type_for_resource_type,
    should_materialize_resource_type,
)
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields


def test_linear_org_types_registered_to_map() -> None:
    for rt, et in (
        ("linear.team", "team"),
        ("linear.cycle", "cycle"),
        ("linear.issue_label", "label"),
        ("linear.initiative", "initiative"),
        ("linear.issue_relation", "issue_relation"),
    ):
        assert should_materialize_resource_type(rt)
        assert entity_type_for_resource_type(rt) == et
        assert mapper_for_resource_type(rt) is not None


def test_linear_org_mappers_emit_entity_drafts() -> None:
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    connector = "linear"
    common = {
        "tenant_id": tenant_id,
        "connection_id": connection_id,
        "connector": connector,
        "raw_id": 1,
        "source_identity_key": "k",
        "source_revision_key": "rev",
        "fetched_at_iso": "2026-01-01T00:00:00+00:00",
    }
    cases: list[tuple[str, str, str, dict]] = [
        (
            "linear.team",
            "team-1",
            "team",
            {
                **core_envelope_fields(
                    connector=connector,
                    connection_id=connection_id,
                    source_object_type="linear.team",
                    source_object_id="team-1",
                ),
                "team": {"id": "team-1", "name": "Platform", "key": "PLAT"},
            },
        ),
        (
            "linear.cycle",
            "cy-1",
            "cycle",
            {
                **core_envelope_fields(
                    connector=connector,
                    connection_id=connection_id,
                    source_object_type="linear.cycle",
                    source_object_id="cy-1",
                ),
                "cycle": {
                    "id": "cy-1",
                    "name": "Cycle 12",
                    "team": {"id": "team-1"},
                },
            },
        ),
        (
            "linear.issue_label",
            "lbl-1",
            "label",
            {
                **core_envelope_fields(
                    connector=connector,
                    connection_id=connection_id,
                    source_object_type="linear.issue_label",
                    source_object_id="lbl-1",
                ),
                "issue_label": {"id": "lbl-1", "name": "P0", "color": "#ff0000"},
            },
        ),
        (
            "linear.initiative",
            "ini-1",
            "initiative",
            {
                **core_envelope_fields(
                    connector=connector,
                    connection_id=connection_id,
                    source_object_type="linear.initiative",
                    source_object_id="ini-1",
                ),
                "initiative": {"id": "ini-1", "name": "Q2 Goals"},
            },
        ),
        (
            "linear.issue_relation",
            "rel-1",
            "issue_relation",
            {
                **core_envelope_fields(
                    connector=connector,
                    connection_id=connection_id,
                    source_object_type="linear.issue_relation",
                    source_object_id="rel-1",
                ),
                "issue_relation": {
                    "id": "rel-1",
                    "type": "blocks",
                    "issue": {"id": "iss-1", "identifier": "ENG-1"},
                    "relatedIssue": {"id": "iss-2", "identifier": "ENG-2"},
                },
            },
        ),
    ]
    for resource_type, external_id, entity_type, payload in cases:
        mapper = mapper_for_resource_type(resource_type)
        assert mapper is not None
        result = mapper.map_row(
            **common,
            resource_type=resource_type,
            external_id=external_id,
            payload_body=payload,
        )
        assert result.draft is not None
        assert result.draft.entity_type == entity_type
        assert result.draft.connector == connector

    rel_mapper = mapper_for_resource_type("linear.issue_relation")
    assert rel_mapper is not None
    rel = rel_mapper.map_row(
        **common,
        resource_type="linear.issue_relation",
        external_id="rel-1",
        payload_body=cases[-1][3],
    )
    assert rel.draft is not None
    assert "blocks" in rel.draft.display_label
    assert rel.draft.attrs_json.get("issue_id") == "iss-1"
    assert rel.draft.attrs_json.get("related_issue_id") == "iss-2"
    assert rel.draft.work_item_ref is not None
