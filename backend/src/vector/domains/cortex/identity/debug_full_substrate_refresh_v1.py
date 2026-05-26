"""Debug-only full substrate refresh (formerly routine ``identity_continuity_rebuild``)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob

_LOGGER = logging.getLogger(__name__)

DEBUG_FULL_SUBSTRATE_REFRESH_SURFACE_KIND_V1 = "debug_full_substrate_refresh_v1"
DEBUG_FULL_SUBSTRATE_REFRESH_ACK_KEY_V1 = "debug_full_substrate_refresh_acknowledged"


def run_debug_full_substrate_refresh_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    materialize_batch_limit: int = 2000,
    anchor_limit: int = 5_000,
    run_determinism_repair: bool = True,
    dry_run: bool = False,
    debug_acknowledged: bool = False,
    replay_job: CortexOrgLinkReplayJob | None = None,
) -> dict[str, Any]:
    """Canonical drain + identity refresh — **not** the authoritative operator repair path."""
    if not debug_acknowledged:
        msg = "debug_full_substrate_refresh_requires_acknowledgement"
        raise ValueError(msg)
    _LOGGER.warning(
        "debug_full_substrate_refresh tenant_id=%s bundle_id=%s — bypasses convergence-native repair",
        tenant_id,
        bundle_id[:16] if bundle_id else "—",
    )
    from vector.domains.cortex.identity.continuity_rebuild import run_identity_continuity_rebuild

    return run_identity_continuity_rebuild(
        session,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        materialize_batch_limit=materialize_batch_limit,
        anchor_limit=anchor_limit,
        run_determinism_repair=run_determinism_repair,
        dry_run=dry_run,
        replay_job=replay_job,
    )
