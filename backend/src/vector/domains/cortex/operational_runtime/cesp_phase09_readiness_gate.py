"""Phase 08.5 Step 35 — static gate **G-P085-READY-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
    GP085_READY01_GATE_ID_V1,
    verify_gp085_ready01_static,
)


def verify_gp085_phase09_readiness_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-READY-01** verification."""
    check = verify_gp085_ready01_static()
    return {
        "id": GP085_READY01_GATE_ID_V1,
        "gate_id": GP085_READY01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_READY01_GATE_ID_V1],
        "checks": [check],
    }
