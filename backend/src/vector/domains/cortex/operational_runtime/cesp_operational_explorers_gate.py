"""Phase 08.5 Step 31 — static gate **G-P085-CP-02**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_operational_explorers import (
    GP085_CP02_GATE_ID_V1,
    verify_gp085_cp02_static,
)


def verify_gp085_operational_explorers_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-CP-02** verification."""
    check = verify_gp085_cp02_static()
    return {
        "id": GP085_CP02_GATE_ID_V1,
        "gate_id": GP085_CP02_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_CP02_GATE_ID_V1],
        "checks": [check],
    }
