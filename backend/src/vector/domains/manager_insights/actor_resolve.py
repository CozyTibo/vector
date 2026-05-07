"""Resolve manager-insight actor identities.

Legacy canonical identity tables were removed; resolver currently falls back to ``None``.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

ActorResolveFn = Callable[[str, str | None], uuid.UUID | None]


def make_actor_resolver(session: Session, tenant_id: uuid.UUID) -> ActorResolveFn:
    """Return ``resolve_actor(connector, external_id)``.

    The legacy canonical store no longer exists, so no cross-system actor mapping is available.
    """

    del session, tenant_id

    def resolve_actor(connector: str, external_id: str | None) -> None:
        del connector, external_id
        return None

    return resolve_actor
