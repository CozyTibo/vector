"""Phase 08.5 Step 33 — static gate **G-P085-ECON-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
    GP085_ECON01_GATE_ID_V1,
    verify_gp085_econ01_static,
)


def verify_gp085_runtime_economics_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-ECON-01** verification."""
    check = verify_gp085_econ01_static()
    return {
        "id": GP085_ECON01_GATE_ID_V1,
        "gate_id": GP085_ECON01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_ECON01_GATE_ID_V1],
        "checks": [check],
    }
