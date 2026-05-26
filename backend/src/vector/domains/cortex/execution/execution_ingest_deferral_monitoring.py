"""P2-E — GitHub ingest caps + deferral release monitoring (Phase 3 step 3.4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.deferral_store import (
    count_deferrals,
    probe_deferral_releases_v1,
    summarize_deferral_pressure,
    summarize_topology_parent_gaps,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.ingestion.exhaust_coverage_registry import build_admin_exhaust_coverage_payload
from vector.domains.cortex.ingestion.github_ingest_caps_ecs import (
    FIX6_RECOMMENDED_GITHUB_CAPS_V1,
    snapshot_fix6_github_ingest_caps_v1,
)
from vector.settings import Settings, get_settings

P2_E_STEP: Final[str] = "3.4_p2e_ingest_deferral_monitoring"
DETAIL_KEY_DEFERRAL_RELEASE_MONITOR_V1: Final[str] = "deferral_release_monitor"

# Extended caps beyond Fix-6 trio — timeline/reviews must stay aligned (CONT-INV-07).
P2E_EXTENDED_GITHUB_CAP_FIELDS_V1: Final[tuple[str, ...]] = (
    "cortex_github_prs_max_pages_per_repo",
    "cortex_github_pr_fetch_max_repos",
    "cortex_github_repo_time_budget_seconds",
    "cortex_github_timeline_max_pages_per_issue_or_pr",
    "cortex_github_reviews_max_pages_per_pr",
    "cortex_github_commits_max_pages_per_repo",
    "cortex_github_deployments_max_pages_per_repo",
)


def is_ingest_deferral_monitoring_enabled_v1() -> bool:
    try:
        return bool(get_settings().cortex_execution_ingest_deferral_monitoring_enabled)
    except Exception:  # noqa: BLE001
        return True


def snapshot_github_ingest_caps_extended_v1(*, settings: Settings | None = None) -> dict[str, Any]:
    """Fix-6 trio + extended GitHub caps for operator honesty."""
    cfg = settings or get_settings()
    fix6 = snapshot_fix6_github_ingest_caps_v1(settings=cfg)
    extended: dict[str, Any] = {}
    for field in P2E_EXTENDED_GITHUB_CAP_FIELDS_V1:
        value = int(getattr(cfg, field))
        rec_min = FIX6_RECOMMENDED_GITHUB_CAPS_V1.get(field)
        extended[field] = {
            "value": value,
            "recommended_min": rec_min[0] if rec_min else None,
            "ceiling": rec_min[1] if rec_min else None,
            "meets_recommended": value >= rec_min[0] if rec_min else True,
        }
    meets_fix6 = all(c.get("meets_recommended") for c in fix6.values())
    meets_extended = all(
        row.get("meets_recommended") is not False for row in extended.values()
    )
    return {
        "fix6_caps": fix6,
        "extended_caps": extended,
        "meets_fix6_recommended": meets_fix6,
        "meets_extended_recommended": meets_extended,
    }


def build_exhaust_registry_honesty_v1(*, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Static exhaust registry summary (declared depth vs substrate maturity)."""
    payload = build_admin_exhaust_coverage_payload(tenant_id=tenant_id)
    connectors = list(payload.get("connectors") or [])
    github = next((c for c in connectors if c.get("connector") == "github"), None)
    slack = next((c for c in connectors if c.get("connector") == "slack"), None)
    return {
        "surface_kind": "exhaust_registry_honesty",
        "connector_count": len(connectors),
        "github": (
            {
                "maturity_level": github.get("maturity_level"),
                "missing_resource_types": github.get("missing_resource_types"),
                "resource_row_count": len(github.get("resources") or []),
            }
            if github
            else None
        ),
        "slack": (
            {
                "maturity_level": slack.get("maturity_level"),
                "missing_resource_types": slack.get("missing_resource_types"),
            }
            if slack
            else None
        ),
        "docs": {
            "connector_exhaust_matrix": payload.get("connector_exhaust_matrix_doc"),
            "ingestion_depth_model": payload.get("ingestion_depth_model_doc"),
        },
    }


def build_deferral_release_monitor_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Deferral counts, pressure breakdown, topology parent gaps."""
    bid = (bundle_id or "").strip() or resolve_default_bundle_id_for_stub_transform(
        session, tenant_id
    )
    if not bid:
        return {
            "surface_kind": "deferral_release_monitor",
            "bundle_id": None,
            "deferral_counts": {},
            "deferral_pressure": [],
            "topology_parent_gaps": [],
        }
    counts = count_deferrals(session, tenant_id=tenant_id, bundle_id=bid)
    return {
        "surface_kind": "deferral_release_monitor",
        "bundle_id": bid,
        "deferral_counts": counts,
        "deferral_pressure": summarize_deferral_pressure(
            session, tenant_id=tenant_id, bundle_id=bid
        ),
        "topology_parent_gaps": summarize_topology_parent_gaps(
            session, tenant_id=tenant_id, bundle_id=bid
        ),
    }


def record_deferral_release_monitor_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    deferral_counts: dict[str, int],
    deferral_pressure: list[dict[str, Any]] | None = None,
    released_total: int | None = None,
) -> dict[str, Any]:
    """Persist latest deferral monitor snapshot on lease ``detail_json``."""
    if not is_ingest_deferral_monitoring_enabled_v1():
        return {"persisted": False, "reason": "monitoring_disabled"}
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None:
        return {"persisted": False, "reason": "no_lease"}
    detail = dict(lease.detail_json or {})
    manifest = dict(detail.get(DETAIL_KEY_DEFERRAL_RELEASE_MONITOR_V1) or {})
    manifest.update(
        {
            "updated_at": datetime.now(UTC).isoformat(),
            "bundle_id": bundle_id,
            "deferral_counts": dict(deferral_counts),
            "deferral_pressure_sample": list(deferral_pressure or [])[:8],
            "released_total_last_slice": released_total,
        }
    )
    detail[DETAIL_KEY_DEFERRAL_RELEASE_MONITOR_V1] = manifest
    lease.detail_json = detail
    session.flush()
    return manifest


def build_ingest_deferral_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin inspect block: ingest caps + deferral release monitor + exhaust honesty."""
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    lease_manifest = {}
    if lease is not None:
        lease_manifest = dict((lease.detail_json or {}).get(DETAIL_KEY_DEFERRAL_RELEASE_MONITOR_V1) or {})
    return {
        "surface_kind": "ingest_deferral_monitoring",
        "monitoring_enabled": is_ingest_deferral_monitoring_enabled_v1(),
        "ingest_caps": snapshot_github_ingest_caps_extended_v1(),
        "deferral_release": build_deferral_release_monitor_v1(session, tenant_id=tenant_id),
        "exhaust_registry": build_exhaust_registry_honesty_v1(tenant_id=tenant_id),
        "lease_deferral_release_manifest": lease_manifest,
    }
