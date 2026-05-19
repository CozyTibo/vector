"""Phase 08.5 Step 34 — static gate **G-P085-ECON-02**."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
    GP085_ECON02_GATE_ID_V1,
    verify_gp085_econ02_static,
)


def verify_gp085_replay_storm_gate_static() -> dict[str, Any]:
    """Aggregate **G-P085-ECON-02** verification."""
    check = verify_gp085_econ02_static()
    return {
        "id": GP085_ECON02_GATE_ID_V1,
        "gate_id": GP085_ECON02_GATE_ID_V1,
        "passed": bool(check.get("passed")),
        "failure_codes": [] if check.get("passed") else [GP085_ECON02_GATE_ID_V1],
        "checks": [check],
    }
