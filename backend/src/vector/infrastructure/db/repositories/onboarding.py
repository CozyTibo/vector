"""CRUD for onboarding_state (one row per tenant)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.onboarding.constants import (
    STATUS_IN_PROGRESS,
    STEP_WELCOME,
)
from vector.infrastructure.db.models.onboarding_state import OnboardingState


def get_onboarding_for_tenant(session: Session, tenant_id: uuid.UUID) -> OnboardingState | None:
    stmt = select(OnboardingState).where(OnboardingState.tenant_id == tenant_id)
    return session.scalar(stmt)


def get_or_create_onboarding(session: Session, tenant_id: uuid.UUID) -> OnboardingState:
    row = get_onboarding_for_tenant(session, tenant_id)
    if row is not None:
        return row
    now = datetime.now(UTC)
    row = OnboardingState(
        tenant_id=tenant_id,
        status=STATUS_IN_PROGRESS,
        current_step=STEP_WELCOME,
        answers_json={},
        version=1,
        started_at=now,
    )
    session.add(row)
    session.flush()
    return row


def merge_answers_json(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(existing)
    for k, v in patch.items():
        out[k] = v
    return out


def list_onboarding_for_tenants(
    session: Session,
    tenant_ids: list[uuid.UUID],
) -> dict[uuid.UUID, OnboardingState]:
    if not tenant_ids:
        return {}
    stmt = select(OnboardingState).where(OnboardingState.tenant_id.in_(tenant_ids))
    rows = list(session.scalars(stmt).all())
    return {r.tenant_id: r for r in rows}
