"""Permutation profile for replay ordering (deterministic)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_permutation_profile_v1(
    *,
    walk_policy: Mapping[str, Any],
    exploration_mode: bool,
) -> dict[str, Any]:
    return {
        "exploration_mode": bool(exploration_mode),
        "max_depth": int(walk_policy.get("max_depth") or 0),
        "max_frontier": int(walk_policy.get("max_frontier") or 0),
        "ordering": "deterministic_lexicographic",
    }
