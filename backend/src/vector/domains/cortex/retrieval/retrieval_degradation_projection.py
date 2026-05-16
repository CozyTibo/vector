"""Degradation envelope for retrieval results."""

from __future__ import annotations

from typing import Any


def build_retrieval_degradation_envelope_v1(
    *,
    degradation_posture: str,
    omission_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "degradation_posture": degradation_posture,
        "omission_summary": dict(omission_summary or {}),
        "propagation_visible": bool(omission_summary),
    }
