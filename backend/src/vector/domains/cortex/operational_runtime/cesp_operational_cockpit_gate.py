"""Phase 08.5 Step 30 — static gate **G-P085-CP-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.operational_cockpit import (
    GP085_CP01_GATE_ID_V1,
    verify_gp085_cp01_static,
)


def verify_gp085_operational_cockpit_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-CP-01** verification."""
    check = verify_gp085_cp01_static()
    return {
        "id": GP085_CP01_GATE_ID_V1,
        "gate_id": GP085_CP01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_CP01_GATE_ID_V1],
        "checks": [check],
    }
