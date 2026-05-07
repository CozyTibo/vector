"""Cortex Phase 01 migration routing — which connector×tenant should use the Cortex ingestion path.

Specification: ``DOCS/cortex/01-ingestion/phase-01-step-0-connector-migration-safety-spec.md``.

Workers call :func:`should_route_ingestion_to_cortex`. Executor wiring is Phase 01+.
"""

from __future__ import annotations

import uuid

from vector.settings import Settings

SUPPORTED_CONNECTOR_IDS: frozenset[str] = frozenset(
    ("calls", "github", "linear", "notion", "slack")
)


def should_route_ingestion_to_cortex(
    settings: Settings,
    connector_id: str,
    tenant_id: uuid.UUID,
) -> bool:
    """Return True when flags select Cortex path for this connector and tenant.

    When True and no executor exists yet, callers should raise ``NotImplementedError`` with a
    clear message (admin stubs) or enqueue Cortex work (future).
    """
    if connector_id not in SUPPORTED_CONNECTOR_IDS:
        return False
    return settings.cortex_migration_route_active(connector_id, tenant_id)


def extract_tenant_id_from_enqueue_args(
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> uuid.UUID | None:
    """Best-effort tenant id from enqueue-style call sites (positional or ``tenant_id`` kw)."""
    raw = kwargs.get("tenant_id")
    if raw is not None:
        try:
            return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
        except (ValueError, TypeError):
            return None
    if args:
        try:
            return args[0] if isinstance(args[0], uuid.UUID) else uuid.UUID(str(args[0]))
        except (ValueError, TypeError, IndexError):
            return None
    return None
