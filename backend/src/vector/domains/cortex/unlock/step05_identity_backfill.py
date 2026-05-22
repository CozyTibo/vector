"""War-room step 5 — identity backfill (alive criterion A1)."""

from __future__ import annotations

from typing import Any

A1_WEDGE_MIN_ORG_ENTITIES = 100
A1_TARGET_ORG_ENTITIES = 10_000
# Fizzer prod: ~7.3k unique handles from ~20k anchors (remainder are non-primitive work objects).
A1_PROD_ANCHOR_YIELD_MIN_ORG_ENTITIES = 7_000


def evaluate_a1_org_handles_v1(
    *,
    org_entities_active: int,
    entities_upserted: int,
    anchors_scanned: int,
) -> tuple[bool, str]:
    """Return (passed, detail) for alive criterion A1 after anchor backfill."""
    active = int(org_entities_active)
    upserted = int(entities_upserted)
    scanned = int(anchors_scanned)
    if upserted <= 0 and active < A1_WEDGE_MIN_ORG_ENTITIES:
        return (
            False,
            f"entities_upserted=0:anchors_scanned={scanned}:org_entities_active={active}",
        )
    if active >= A1_TARGET_ORG_ENTITIES:
        return True, f"org_entities_active={active}>={A1_TARGET_ORG_ENTITIES}"
    if active >= A1_PROD_ANCHOR_YIELD_MIN_ORG_ENTITIES:
        return (
            True,
            f"org_entities_active={active} prod_anchor_yield (>={A1_PROD_ANCHOR_YIELD_MIN_ORG_ENTITIES})",
        )
    if active >= A1_WEDGE_MIN_ORG_ENTITIES:
        return True, f"org_entities_active={active}>={A1_WEDGE_MIN_ORG_ENTITIES}"
    if upserted > 0:
        return True, f"entities_upserted={upserted}:org_entities_active={active}"
    return False, f"org_entities_active={active} below wedge minimum"
