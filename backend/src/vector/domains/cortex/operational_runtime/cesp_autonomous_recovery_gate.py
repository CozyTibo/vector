"""Phase 08.5 Step 29 — static gate **G-P085-HEALTH-02**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_autonomous_recovery_score import (
    GP085_HEALTH02_GATE_ID_V1,
    verify_gp085_health02_static,
)


def verify_gp085_autonomous_recovery_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-HEALTH-02** verification."""
    check = verify_gp085_health02_static()
    return {
        "id": GP085_HEALTH02_GATE_ID_V1,
        "gate_id": GP085_HEALTH02_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_HEALTH02_GATE_ID_V1],
        "checks": [check],
    }
