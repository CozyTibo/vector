"""P2-B — event-driven execution triggers (ingest dirty, identity promotion, graph-hash walks)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.convergence_dispatch import mark_dirty_and_enqueue_convergence_v1
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.identity.projection_export import build_org_graph_projection_export_document
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
    schedule_octs_walks_for_tenant_v1,
)

_LOGGER = logging.getLogger(__name__)

P2_B_STEP = "2b_event_triggers"
DETAIL_KEY_EVENT_TRIGGERS_V1: Final[str] = "event_triggers"
DETAIL_KEY_LAST_GRAPH_HASH_V1: Final[str] = "last_graph_projection_stable_hash_sha256"

EVENT_TRIGGER_INGEST_V1: Final[str] = "post_ingestion_mark_dirty"
EVENT_TRIGGER_IDENTITY_PROMOTION_V1: Final[str] = "identity_projection_promotion"
EVENT_TRIGGER_GRAPH_HASH_V1: Final[str] = "graph_projection_hash_changed"


def is_execution_event_triggers_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_execution_event_triggers_enabled)
    except Exception:  # noqa: BLE001
        return True


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_event_triggers_detail(lease: Any) -> dict[str, Any]:
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    raw = detail.get(DETAIL_KEY_EVENT_TRIGGERS_V1)
    return dict(raw) if isinstance(raw, dict) else {}


def _persist_event_triggers_detail(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    patch: dict[str, Any],
) -> dict[str, Any]:
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None:
        return {"persisted": False, "reason": "no_lease"}
    detail = dict(lease.detail_json or {})
    triggers = _read_event_triggers_detail(lease)
    triggers.update(patch)
    triggers["updated_at"] = _now_iso()
    detail[DETAIL_KEY_EVENT_TRIGGERS_V1] = triggers
    lease.detail_json = detail
    session.flush()
    return triggers


def trigger_post_ingestion_execution_v1(
    *,
    tenant_id: uuid.UUID,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Ingest completion: mark tenant dirty + enqueue convergence slice."""
    if not is_execution_event_triggers_enabled_v1():
        return {"triggered": False, "reason": "event_triggers_disabled"}
    out = mark_dirty_and_enqueue_convergence_v1(
        tenant_id=tenant_id,
        reason=reason,
        telemetry_trigger=f"{EVENT_TRIGGER_INGEST_V1}:{reason}",
    )
    return {
        "trigger": EVENT_TRIGGER_INGEST_V1,
        "triggered": bool(out.get("scheduled")),
        "dispatch": out,
    }


def trigger_identity_promotion_after_substrate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    substrate: dict[str, Any],
) -> dict[str, Any]:
    """Identity projection completion: bounded lawful graph-density promotion pass."""
    if not is_execution_event_triggers_enabled_v1():
        return {"triggered": False, "reason": "event_triggers_disabled"}
    from vector.domains.cortex.identity.continuity_rebuild import (
        schedule_graph_density_promotion_after_identity_substrate_v1,
    )

    promotion = schedule_graph_density_promotion_after_identity_substrate_v1(
        session,
        tenant_id=tenant_id,
        substrate=substrate,
    )
    manifest = {
        "trigger": EVENT_TRIGGER_IDENTITY_PROMOTION_V1,
        "triggered": promotion is not None,
        "at": _now_iso(),
        "promotion_scheduled": bool((promotion or {}).get("scheduled")),
        "schedule_reason": (promotion or {}).get("reason")
        or ((promotion or {}).get("evaluation") or {}).get("schedule_reason"),
    }
    _persist_event_triggers_detail(
        session,
        tenant_id=tenant_id,
        patch={"last_identity_promotion": manifest},
    )
    return {"trigger": EVENT_TRIGGER_IDENTITY_PROMOTION_V1, **manifest, "promotion": promotion}


def trigger_graph_hash_walk_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    graph_projection_stable_hash: str | None,
    pipeline_run_id: uuid.UUID | None = None,
    force_schedule: bool = False,
) -> dict[str, Any]:
    """When authoritative graph projection hash changes, schedule OCTS walks (P2-B)."""
    new_hash = (graph_projection_stable_hash or "").strip()
    if not is_execution_event_triggers_enabled_v1():
        return {
            "trigger": EVENT_TRIGGER_GRAPH_HASH_V1,
            "triggered": False,
            "reason": "event_triggers_disabled",
            "graph_hash": new_hash or None,
        }

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    prior = str(detail.get(DETAIL_KEY_LAST_GRAPH_HASH_V1) or "").strip()
    changed = bool(new_hash) and new_hash != prior

    schedule_out: dict[str, Any] | None = None
    if (changed or force_schedule) and new_hash:
        schedule_out = schedule_octs_walks_for_tenant_v1(
            tenant_id=tenant_id,
            trigger=TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
            pipeline_run_id=pipeline_run_id,
            graph_projection_stable_hash=new_hash,
            force=force_schedule,
            session=session,
        )

    manifest = {
        "trigger": EVENT_TRIGGER_GRAPH_HASH_V1,
        "triggered": changed or force_schedule,
        "at": _now_iso(),
        "prior_hash": prior or None,
        "new_hash": new_hash or None,
        "hash_changed": changed,
        "walk_schedule": schedule_out,
        "walks_scheduled": bool((schedule_out or {}).get("scheduled")),
    }
    if lease is not None and new_hash:
        lease_detail = dict(lease.detail_json or {})
        lease_detail[DETAIL_KEY_LAST_GRAPH_HASH_V1] = new_hash
        triggers = _read_event_triggers_detail(lease)
        triggers["last_graph_hash_walk"] = manifest
        triggers["updated_at"] = _now_iso()
        lease_detail[DETAIL_KEY_EVENT_TRIGGERS_V1] = triggers
        lease.detail_json = lease_detail
        session.flush()

    if changed:
        _LOGGER.info(
            "graph_hash_changed_walk_schedule tenant_id=%s prior=%s new=%s scheduled=%s",
            tenant_id,
            prior[:12] if prior else "—",
            new_hash[:12],
            bool((schedule_out or {}).get("scheduled")),
        )

    return manifest


def resolve_live_graph_projection_hash_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> str | None:
    export_doc = build_org_graph_projection_export_document(session, tenant_id=tenant_id)
    return str(export_doc.get("stable_hash_sha256") or "").strip() or None


def build_event_triggers_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin / proof surface for P2-B trigger state."""
    from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
        build_substrate_traversal_scheduling_catalog_v1,
    )

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    live_hash = resolve_live_graph_projection_hash_v1(session, tenant_id=tenant_id)
    stored_hash = str(detail.get(DETAIL_KEY_LAST_GRAPH_HASH_V1) or "").strip() or None
    catalog = build_substrate_traversal_scheduling_catalog_v1()
    return {
        "surface_kind": "execution_event_triggers",
        "event_triggers_enabled": is_execution_event_triggers_enabled_v1(),
        "live_graph_projection_stable_hash": live_hash,
        "stored_graph_projection_stable_hash": stored_hash,
        "graph_hash_in_sync": bool(live_hash and stored_hash and live_hash == stored_hash),
        "event_triggers_detail": _read_event_triggers_detail(lease),
        "schedule_triggers": list(catalog.get("schedule_triggers") or []),
        "graph_hash_trigger_registered": TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1
        in (catalog.get("schedule_triggers") or []),
    }
