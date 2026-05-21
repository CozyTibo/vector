"""Tenant execution lease statuses and FSM states (M5)."""

from __future__ import annotations

from typing import Final

# Lease row status (worker scheduling)
LEASE_STATUS_IDLE: Final[str] = "idle"
LEASE_STATUS_DIRTY: Final[str] = "dirty"
LEASE_STATUS_RUNNING: Final[str] = "running"
LEASE_STATUS_WAITING: Final[str] = "waiting"
LEASE_STATUS_STALLED: Final[str] = "stalled"

LEASE_STATUSES_ACTIVE: Final[frozenset[str]] = frozenset(
    {LEASE_STATUS_DIRTY, LEASE_STATUS_RUNNING, LEASE_STATUS_WAITING, LEASE_STATUS_STALLED}
)

# FSM states (authoritative execution cursor)
FSM_IDLE: Final[str] = "IDLE"
FSM_INGESTING: Final[str] = "INGESTING"
FSM_CANONICAL_DRAINING: Final[str] = "CANONICAL_DRAINING"
FSM_IDENTITY: Final[str] = "IDENTITY"
FSM_GRAPH: Final[str] = "GRAPH"
FSM_TRAVERSAL: Final[str] = "TRAVERSAL"
FSM_AWAITING_TCRE: Final[str] = "AWAITING_TCRE"
FSM_RETRIEVAL: Final[str] = "RETRIEVAL"
FSM_SYNTHESIS: Final[str] = "SYNTHESIS"
FSM_BLOCKED: Final[str] = "BLOCKED"
FSM_STALLED: Final[str] = "STALLED"
