"""S4.5 — synthesis job inspector wiring."""

from __future__ import annotations

import inspect

from vector.domains.cortex.synthesis.synthesis_job_inspector_v1 import (
    SYNTHESIS_JOB_INSPECTOR_SCHEMA_VERSION,
    _inspect_claims_v1,
)


def test_inspector_flags_ungrounded_claims() -> None:
    body = {
        "claims": [
            {"claim_id": "clm-0001", "synthesis_citations": []},
            {
                "claim_id": "clm-0002",
                "synthesis_citations": [
                    {"retrieval_lookup_id": "sha256:" + "a" * 64, "source_artifact_kind": "org_link"}
                ],
            },
        ]
    }
    rows = _inspect_claims_v1(body)
    assert rows[0]["ungrounded"] is True
    assert rows[1]["ungrounded_execution"] is True


def test_admin_route_wiring_static() -> None:
    from vector.api.http.routes import admin_cortex_synthesis as routes_mod

    src = inspect.getsource(routes_mod.register_cortex_synthesis_routes)
    assert "/jobs/{job_id}/inspector" in src
    assert "build_synthesis_job_inspector_v1" in src
    assert SYNTHESIS_JOB_INSPECTOR_SCHEMA_VERSION == 1
