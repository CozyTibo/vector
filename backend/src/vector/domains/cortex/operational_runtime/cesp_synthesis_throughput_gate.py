"""Phase 08.5 Step 26 — static gate **G-P085-SYN-03**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_synthesis_throughput_maturity import (
    verify_gp085_syn03_static,
)
from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
    GP085_SYN03_GATE_ID_V1,
)


def verify_gp085_synthesis_throughput_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-SYN-03** verification."""
    check = verify_gp085_syn03_static()
    return {
        "id": GP085_SYN03_GATE_ID_V1,
        "gate_id": GP085_SYN03_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_SYN03_GATE_ID_V1],
        "checks": [check],
    }
