"""Static metadata for Phase 04 Step 16 org failure + remediation (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_FAILURE_REMEDIATION_SURFACE_VERSION: Final[int] = 1


def build_org_failure_remediation_pointer_section() -> dict[str, Any]:
    return {
        "org_failure_remediation_surface_version": ORG_FAILURE_REMEDIATION_SURFACE_VERSION,
        "org_failures_route": "GET /admin/tenants/{tenant_id}/cortex/identity/failures",
        "org_remediation_validate_route": (
            "POST /admin/tenants/{tenant_id}/cortex/identity/remediation/validate"
        ),
        "org_failure_classes_documented": [
            "org_link_replay_job_failed",
            "org_link_replay_missing_receipts",
            "org_link_temporal_overlap",
        ],
        "org_remediation_classes_documented": [
            "org_ambiguity_triage_ack",
            "org_link_replay_retry",
        ],
        "org_failure_remediation_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-failure-remediation-doctrine.md",
        ],
    }
