"""Phase 08.5 Step 11 — static gate **G-P085-PROMO-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    GP085_PROMO01_GATE_ID_V1,
    verify_gp085_promo01_static,
)


def verify_gp085_promotion_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-PROMO-01** verification."""
    check = verify_gp085_promo01_static()
    return {
        "id": GP085_PROMO01_GATE_ID_V1,
        "gate_id": GP085_PROMO01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_PROMO01_GATE_ID_V1],
        "checks": [check],
    }
