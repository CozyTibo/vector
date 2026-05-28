"""Cortex pass type identifiers (DB queue)."""

from __future__ import annotations

CANON_PASS = "canon_pass"
IDENTITY_PASS = "identity_pass"

PASS_TYPES = frozenset({CANON_PASS, IDENTITY_PASS})

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

ACTIVE_STATUSES = frozenset({STATUS_PENDING, STATUS_RUNNING})
