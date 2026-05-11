"""Phase 04 Step 18 — durable audit trail for identity operator-console POSTs (G-P04-23)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_identity_console_audit import CortexOrgIdentityConsoleAudit

IDENTITY_OPERATOR_AUDIT_SCHEMA_VERSION: Final[int] = 1


def append_identity_console_audit(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    surface: str,
    action_kind: str,
    ref_uuid: uuid.UUID | None = None,
    detail_json: dict[str, Any] | None = None,
) -> CortexOrgIdentityConsoleAudit:
    row = CortexOrgIdentityConsoleAudit(
        tenant_id=tenant_id,
        surface=surface.strip(),
        action_kind=action_kind.strip(),
        ref_uuid=ref_uuid,
        detail_json=dict(detail_json or {}),
    )
    session.add(row)
    session.flush()
    return row
