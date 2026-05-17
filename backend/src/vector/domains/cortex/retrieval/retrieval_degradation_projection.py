"""Degradation envelope for retrieval results (class floors + omission visibility)."""

from __future__ import annotations

from typing import Any, Final

RETRIEVAL_LEGALITY_CLASS_DEGRADATION_FLOOR_V1: Final[dict[str, str]] = {
    "retrieval_replay_safe": "stable",
    "retrieval_degraded": "degraded",
    "retrieval_partial": "partial",
    "retrieval_unverifiable": "degraded",
    "retrieval_forbidden": "degraded",
}


def apply_retrieval_legality_degradation_floor_v1(
    *,
    degradation_posture: str,
    retrieval_legality_class: str,
) -> str:
    """Apply legality-class floor to degradation posture (monotonic: never lighter than floor)."""
    floor = RETRIEVAL_LEGALITY_CLASS_DEGRADATION_FLOOR_V1.get(
        retrieval_legality_class, "degraded"
    )
    rank = {"stable": 0, "partial": 1, "degraded": 2}
    current = rank.get(degradation_posture, 2)
    required = rank.get(floor, 2)
    if required > current:
        return floor
    return degradation_posture


def build_retrieval_degradation_envelope_v1(
    *,
    degradation_posture: str,
    omission_summary: dict[str, Any],
    retrieval_legality_class: str | None = None,
    r_leg_violations: list[str] | None = None,
) -> dict[str, Any]:
    posture = degradation_posture
    if retrieval_legality_class is not None:
        posture = apply_retrieval_legality_degradation_floor_v1(
            degradation_posture=posture,
            retrieval_legality_class=retrieval_legality_class,
        )
    return {
        "degradation_posture": posture,
        "omission_summary": dict(omission_summary or {}),
        "propagation_visible": bool(omission_summary),
        "retrieval_legality_class_floor": retrieval_legality_class,
        "r_leg_violations": list(r_leg_violations or []),
    }
