"""Cortex pass type identifiers (DB queue)."""

from __future__ import annotations

CANON_PASS = "canon_pass"
IDENTITY_PASS = "identity_pass"
GRAPH_PROJECTION_PASS = "graph_projection_pass"
DECLARED_DOMAIN_PASS = "declared_domain_pass"

PASS_TYPES = frozenset({CANON_PASS, IDENTITY_PASS, GRAPH_PROJECTION_PASS, DECLARED_DOMAIN_PASS})

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

ACTIVE_STATUSES = frozenset({STATUS_PENDING, STATUS_RUNNING})
