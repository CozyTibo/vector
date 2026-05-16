"""Continuity frontier collapse projection."""

from __future__ import annotations

from typing import Any


def project_continuity_frontier_v1(topology: dict[str, Any]) -> dict[str, Any]:
    frontier_nodes = [
        n for n in topology.get("nodes") or [] if n.get("kind") == "continuity_unverified"
    ]
    return {
        "frontier_count": len(frontier_nodes),
        "frontier_nodes": frontier_nodes,
        "collapsed": len(frontier_nodes) == 0,
    }
