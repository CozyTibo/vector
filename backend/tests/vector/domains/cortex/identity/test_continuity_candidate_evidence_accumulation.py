"""Deterministic candidate-pair evidence accumulation (Phase 04)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from vector.domains.cortex.identity.continuity_candidate_evidence_accumulation import (
    ACCUMULATION_SCHEMA_VERSION,
    accumulate_candidate_pair_evidence,
)


def test_accumulate_groups_pair_and_counts_rules_and_connectors() -> None:
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    rows = [
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": str(e1),
            "target_entity_id": str(e2),
            "evidence_raw_record_ids": [10, 11],
            "rule_id": "rule.a",
        },
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": str(e2),
            "target_entity_id": str(e1),
            "evidence_raw_record_ids": [12],
            "rule_id": "rule.b",
        },
    ]
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    raw_by_id = {
        10: SimpleNamespace(connector="slack", fetched_at=t0),
        11: SimpleNamespace(connector="slack", fetched_at=t0),
        12: SimpleNamespace(connector="github", fetched_at=t0),
    }
    out = accumulate_candidate_pair_evidence(rows, raw_by_id=raw_by_id)
    assert out["accumulation_schema_version"] == ACCUMULATION_SCHEMA_VERSION
    assert out["pair_family_count"] == 1
    fam = out["pair_families"][0]
    assert fam["rule_count"] == 2
    assert fam["by_rule_id"]["rule.a"]["edge_count"] == 1
    assert fam["by_rule_id"]["rule.b"]["edge_count"] == 1
    assert set(fam["distinct_evidence_raw_record_ids"]) == {10, 11, 12}
    assert fam["by_connector"]["github"] == 1
    assert fam["by_connector"]["slack"] == 2
    assert isinstance(fam.get("deterministic_explain_lines"), list)
    assert fam.get("recurrence_calendar_day_count") == 1
