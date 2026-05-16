"""Continuity breakpoint detection."""

from __future__ import annotations

from typing import Any


def project_continuity_breakpoints_v1(topology: dict[str, Any]) -> list[dict[str, Any]]:
    breakpoints: list[dict[str, Any]] = []
    for n in topology.get("nodes") or []:
        if n.get("kind") in ("replay_conflicted", "continuity_unverified"):
            breakpoints.append({"node_id": n.get("node_id"), "kind": n.get("kind")})
    return breakpoints
