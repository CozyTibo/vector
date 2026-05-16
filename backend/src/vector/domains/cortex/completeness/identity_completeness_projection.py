"""Identity resolution completeness (merge evidence accounting)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.domains.cortex.identity.control_plane import build_identity_control_plane


def project_identity_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    cp = build_identity_control_plane(session, tenant_id=tenant_id)
    cards = cp.get("cards") or {}
    handles = int((cards.get("org_handles") or {}).get("value") or 0)
    ambiguous = int((cards.get("ambiguous_identities") or {}).get("value") or 0)
    orphans = int((cards.get("orphaned_references") or {}).get("value") or 0)
    pending_merges = int((cards.get("pending_merges") or {}).get("value") or 0)
    replay_drift = int((cards.get("replay_drift") or {}).get("value") or 0)
    candidates = int((cards.get("candidate_links") or {}).get("value") or 0)
    authoritative = int((cards.get("authoritative_links") or {}).get("value") or 0)

    total = handles
    omission_classes: dict[str, int] = {}
    if ambiguous:
        omission_classes["unresolved_actor"] = ambiguous
    if replay_drift:
        omission_classes["replay_conflicted_identity"] = replay_drift
    if orphans:
        omission_classes["orphan_identity_cluster"] = orphans
    if pending_merges:
        omission_classes["continuity_unverified"] = pending_merges

    freshness = str(cp.get("freshness_label") or "unknown")
    replay_posture = "unsafe" if replay_drift else ("partial" if ambiguous or orphans else "stable")
    if freshness == "stale":
        replay_posture = "partial"

    substrate_state = "critical" if handles == 0 else (
        "degraded" if ambiguous + orphans + replay_drift > 0 else "healthy"
    )
    unresolved = ambiguous + orphans
    degraded = replay_drift
    resolved = max(0, handles - unresolved - degraded)

    return build_stage_envelope_v1(
        stage_id="identity",
        label="Identity",
        total_objects=handles,
        processed_count=handles,
        degraded_count=degraded,
        unresolved_count=unresolved,
        omitted_count=pending_merges,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=str(cp.get("computed_at") or ""),
        drift_warnings=[f"freshness={freshness}"] if freshness != "fresh" else [],
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/identity",
        metrics={
            "resolved_identity_percent": pct(resolved, total if total else 1),
            "authoritative_links": authoritative,
            "candidate_links": candidates,
            "ambiguous_identities": ambiguous,
            "orphan_references": orphans,
            "replay_drift_total": replay_drift,
            "identity_policy_surface": "identity_control_plane_v1",
        },
    )
