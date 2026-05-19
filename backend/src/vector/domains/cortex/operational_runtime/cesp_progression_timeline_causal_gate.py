"""Phase 08.5 Step 32 — static gate **G-P085-CP-03**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_progression_timeline_causal import (
    GP085_CP03_GATE_ID_V1,
    verify_gp085_cp03_static,
)


def verify_gp085_progression_timeline_causal_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-CP-03** verification."""
    check = verify_gp085_cp03_static()
    return {
        "id": GP085_CP03_GATE_ID_V1,
        "gate_id": GP085_CP03_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_CP03_GATE_ID_V1],
        "checks": [check],
    }
