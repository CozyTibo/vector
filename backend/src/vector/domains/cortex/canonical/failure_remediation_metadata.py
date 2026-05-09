"""Static metadata for Phase 03 Step 14 failure + remediation (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

FAILURE_REMEDIATION_SURFACE_VERSION: Final[int] = 1


def build_failure_remediation_pointer_section() -> dict[str, Any]:
    return {
        "failure_remediation_surface_version": FAILURE_REMEDIATION_SURFACE_VERSION,
        "canonical_failures_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/failures",
        "canonical_remediation_validate_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/remediation/validate"
        ),
        "failure_degradation_taxonomy": [
            "healthy",
            "degraded",
            "partial",
            "unresolved",
            "unverifiable",
            "conflicting",
            "corrupted",
        ],
        "failure_classes_documented": [
            "transform_materialize_error",
            "replay_forbidden_divergence",
            "replay_job_failed",
        ],
        "remediation_classes_documented": [
            "scoped_rebuild",
            "ambiguity_triage_ack",
        ],
        "failure_remediation_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-failure-degradation-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-remediation-recovery-doctrine.md",
        ],
    }
