"""Convergence lease statuses and phase cursor identifiers."""

from __future__ import annotations

from typing import Final

LEASE_STATUS_IDLE: Final[str] = "idle"
LEASE_STATUS_DIRTY: Final[str] = "dirty"
LEASE_STATUS_RUNNING: Final[str] = "running"
LEASE_STATUS_WAITING: Final[str] = "waiting"
LEASE_STATUS_STALLED: Final[str] = "stalled"

LEASE_STATUSES_ACTIVE: Final[frozenset[str]] = frozenset(
    {LEASE_STATUS_DIRTY, LEASE_STATUS_RUNNING, LEASE_STATUS_WAITING, LEASE_STATUS_STALLED}
)
