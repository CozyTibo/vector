"""Registry payload matches admin contract (no DB)."""

from __future__ import annotations

import uuid

from vector.contracts.admin import AdminCortexIngestionExhaustCoverageResponse
from vector.domains.cortex.ingestion.exhaust_coverage_registry import build_admin_exhaust_coverage_payload


def test_exhaust_coverage_payload_validates() -> None:
    tid = uuid.uuid4()
    raw = build_admin_exhaust_coverage_payload(tenant_id=tid)
    model = AdminCortexIngestionExhaustCoverageResponse.model_validate(raw)
    assert model.tenant_id == tid
    assert len(model.connectors) == 5
    gh = next(c for c in model.connectors if c.connector == "github")
    assert gh.maturity_level == 3
    assert "github.pull_request" in [r.resource_type for r in gh.resources]
    lin = next(c for c in model.connectors if c.connector == "linear")
    assert lin.maturity_level == 3
    assert "linear.issue" not in lin.missing_resource_types
    notion = next(c for c in model.connectors if c.connector == "notion")
    assert notion.maturity_level == 3
    assert "notion.search_result" in [r.resource_type for r in notion.resources]
    calls = next(c for c in model.connectors if c.connector == "calls")
    assert calls.maturity_level == 3
    assert "calls.meeting" in [r.resource_type for r in calls.resources]
