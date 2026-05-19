"""Phase 08.5 Step 05 — static gate **G-P085-CONT-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_continuity import (
    GP085_CONT01_GATE_ID_V1,
    verify_gp085_cont01_state_machine_static,
)


def verify_gp085_continuation_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-CONT-01** verification."""
    check = verify_gp085_cont01_state_machine_static()
    return {
        "id": GP085_CONT01_GATE_ID_V1,
        "gate_id": GP085_CONT01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_CONT01_GATE_ID_V1],
        "checks": [check],
    }
