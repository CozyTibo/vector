"""Static metadata for Phase 04 link ledger admin surface (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

LINK_LEDGER_RUNTIME_SURFACE_VERSION: Final[int] = 8


def build_link_ledger_pointer_section() -> dict[str, Any]:
    return {
        "link_ledger_runtime_surface_version": LINK_LEDGER_RUNTIME_SURFACE_VERSION,
        "link_ledger_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/links",
        "link_ledger_detail_route": "GET /admin/tenants/{tenant_id}/cortex/identity/links/{link_id}",
        "link_ledger_revoke_route": "POST /admin/tenants/{tenant_id}/cortex/identity/links/{link_id}/revoke",
        "link_temporal_timeline_route": "GET /admin/tenants/{tenant_id}/cortex/identity/links/timeline",
        "link_hint_bucket_route": "GET /admin/tenants/{tenant_id}/cortex/identity/links/hints",
        "link_candidate_queue_route": "GET /admin/tenants/{tenant_id}/cortex/identity/link-candidates",
        "celery_task_regenerate_link_candidates": None,
        "celery_task_replay_authoritative_links": None,
        "legacy_celery_tasks_removed_wave3": [
            "vector.cortex.identity.regenerate_link_candidates",
            "vector.cortex.identity.replay_authoritative_links",
        ],
        "link_ledger_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-link-ledger-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-candidate-vs-authoritative-linkage-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-hint-and-prohibited-link-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-temporal-validity-and-revocation-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-continuity-replay-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-linkage-rule-engine-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-execution-primitive-persistence-doctrine.md",
        ],
    }
