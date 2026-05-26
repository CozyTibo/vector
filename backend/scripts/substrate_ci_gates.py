#!/usr/bin/env python3
"""Wave 5/6 — run substrate coherence CI gates (M9 + waves 1–6 static verifiers)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (  # noqa: E402
    discover_repo_root_v1,
    run_substrate_ci_gate_report_v1,
)


def main() -> int:
    report = run_substrate_ci_gate_report_v1(repo_root=discover_repo_root_v1())
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        for err in report.get("coherence_errors") or []:
            print(f"coherence: {err}", file=sys.stderr)
        for err in report.get("wiring_errors") or []:
            print(f"wiring: {err}", file=sys.stderr)
        return 1
    print("substrate_ci_gates: pass", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
