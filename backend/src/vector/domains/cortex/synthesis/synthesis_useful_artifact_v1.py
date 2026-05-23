"""Wave S4 step 20 — useful published synthesis (execution/island brief with evidenced claims)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_empty_claims_gate_v1 import (
    _USEFUL_ARTIFACT_KINDS_V1,
    count_verifiable_claims_v1,
)

SYNTHESIS_USEFUL_ARTIFACT_SCHEMA_VERSION: Final[int] = 1
WAVE_S4_STEP_20: Final[str] = "wave_s4_synthesis_useful_artifact"
FIZZER_TENANT_ID_V1: Final[str] = "c08ef32b-f89a-40f6-9566-e19b5329436f"


def snapshot_published_useful_artifacts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """Count published artifacts with ≥1 verifiable claim in lookback window."""
    since = datetime.now(tz=UTC) - timedelta(days=max(1, lookback_days))
    tid = str(tenant_id)
    rows = session.execute(
        text(
            """
            SELECT id, artifact_kind, body_json, published_at
            FROM cortex_synthesis_artifacts
            WHERE tenant_id = :tenant
              AND published IS TRUE
              AND published_at >= :since
            ORDER BY published_at DESC
            LIMIT 200
            """
        ),
        {"tenant": tid, "since": since},
    ).mappings().all()
    useful: list[dict[str, Any]] = []
    for row in rows:
        body = row["body_json"] if isinstance(row["body_json"], dict) else {}
        kind = str(row["artifact_kind"] or body.get("artifact_kind") or "")
        verifiable = count_verifiable_claims_v1(body)
        if verifiable < 1:
            continue
        if kind not in _USEFUL_ARTIFACT_KINDS_V1 and kind != "degradation_brief":
            continue
        useful.append(
            {
                "artifact_id": str(row["id"]),
                "artifact_kind": kind,
                "verifiable_claim_count": verifiable,
                "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            }
        )
    primary = useful[0] if useful else None
    return {
        "schema_version": SYNTHESIS_USEFUL_ARTIFACT_SCHEMA_VERSION,
        "tenant_id": tid,
        "lookback_days": lookback_days,
        "published_useful_count": len(useful),
        "primary_useful_artifact": primary,
        "useful_artifacts": useful[:10],
        "acceptance_met": len(useful) >= 1,
    }
