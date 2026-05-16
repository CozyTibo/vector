"""Continuity degradation propagation."""

from __future__ import annotations

from typing import Any


def propagate_continuity_degradation_v1(
    *,
    source_posture: str,
    target_kind: str,
) -> dict[str, Any]:
    consequence = f"{target_kind}_degraded_from_{source_posture}"
    return {"source": source_posture, "target": target_kind, "consequence": consequence}
