"""Phase 08.5 Step 25 — static gate **G-P085-SYN-02**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.synthesis_idle_starved_classification import (
    verify_gp085_syn02_static,
)
from vector.domains.cortex.synthesis.synthesis_idle_classification import (
    GP085_SYN02_GATE_ID_V1,
)


def verify_gp085_synthesis_idle_starved_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-SYN-02** verification."""
    check = verify_gp085_syn02_static()
    return {
        "id": GP085_SYN02_GATE_ID_V1,
        "gate_id": GP085_SYN02_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_SYN02_GATE_ID_V1],
        "checks": [check],
    }
