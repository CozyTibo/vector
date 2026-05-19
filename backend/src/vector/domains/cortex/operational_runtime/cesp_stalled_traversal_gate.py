"""Phase 08.5 Step 16 — static gate **G-P085-WALK-03**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery import (
    GP085_WALK03_GATE_ID_V1,
    verify_gp085_walk03_static,
)


def verify_gp085_stalled_traversal_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-WALK-03** verification."""
    check = verify_gp085_walk03_static()
    return {
        "id": GP085_WALK03_GATE_ID_V1,
        "gate_id": GP085_WALK03_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_WALK03_GATE_ID_V1],
        "checks": [check],
    }
