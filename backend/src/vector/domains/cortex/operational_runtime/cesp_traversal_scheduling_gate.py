"""Phase 08.5 Step 14 — static gate **G-P085-WALK-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    GP085_WALK01_GATE_ID_V1,
    verify_gp085_walk01_static,
)


def verify_gp085_traversal_scheduling_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-WALK-01** verification."""
    check = verify_gp085_walk01_static()
    return {
        "id": GP085_WALK01_GATE_ID_V1,
        "gate_id": GP085_WALK01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_WALK01_GATE_ID_V1],
        "checks": [check],
    }
