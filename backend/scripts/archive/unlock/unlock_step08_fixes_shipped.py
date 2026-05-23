#!/usr/bin/env python3
"""Step 8 — verify Fix 3–5 shipped (promotion hook + admin operator APIs)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vector.domains.cortex.unlock.step08_fixes_shipped import evaluate_step08_fixes_shipped_v1  # noqa: E402


def main() -> dict:
    out = evaluate_step08_fixes_shipped_v1()
    out["validated_at"] = datetime.now(UTC).isoformat()
    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step08_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("step8_pass"):
        raise SystemExit(1)
