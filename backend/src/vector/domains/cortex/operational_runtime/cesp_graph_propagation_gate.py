"""Phase 08.5 Step 13 — static gate **G-P085-GRAPH-PROP-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
    GP085_GRAPH_PROP01_GATE_ID_V1,
    verify_gp085_graph_prop01_static,
)


def verify_gp085_graph_propagation_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-GRAPH-PROP-01** verification."""
    check = verify_gp085_graph_prop01_static()
    return {
        "id": GP085_GRAPH_PROP01_GATE_ID_V1,
        "gate_id": GP085_GRAPH_PROP01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_GRAPH_PROP01_GATE_ID_V1],
        "checks": [check],
    }
