"""Phase 08.5 Step 23 — static gate **G-P085-RET-PROP-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.retrieval_completeness_propagation import (
    GP085_RET_PROP01_GATE_ID_V1,
    verify_gp085_ret_prop01_static,
)


def verify_gp085_retrieval_propagation_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-RET-PROP-01** verification."""
    check = verify_gp085_ret_prop01_static()
    return {
        "id": GP085_RET_PROP01_GATE_ID_V1,
        "gate_id": GP085_RET_PROP01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_RET_PROP01_GATE_ID_V1],
        "checks": [check],
    }
