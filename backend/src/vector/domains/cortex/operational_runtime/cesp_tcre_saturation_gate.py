"""Phase 08.5 Step 18 — static gate **G-P085-TCRE-01**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    GP085_TCRE01_GATE_ID_V1,
    verify_gp085_tcre01_static,
)


def verify_gp085_tcre_saturation_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-TCRE-01** verification."""
    check = verify_gp085_tcre01_static()
    return {
        "id": GP085_TCRE01_GATE_ID_V1,
        "gate_id": GP085_TCRE01_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_TCRE01_GATE_ID_V1],
        "checks": [check],
    }
