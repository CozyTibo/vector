"""Phase 08.5 Step 22 — static gate **G-P085-RET-02**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    GP085_RET02_GATE_ID_V1,
    verify_gp085_ret02_static,
)


def verify_gp085_retrieval_starvation_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-RET-02** verification."""
    check = verify_gp085_ret02_static()
    return {
        "id": GP085_RET02_GATE_ID_V1,
        "gate_id": GP085_RET02_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_RET02_GATE_ID_V1],
        "checks": [check],
    }
