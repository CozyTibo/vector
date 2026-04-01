#!/usr/bin/env python3
"""Write fixtures/generated/dataset.json from VECTOR_MOCK_SEED."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from mock_connectors.fixtures.company_generator import (  # noqa: E402
    dataset_to_json_dict,
    generate_dataset,
)


def main() -> None:
    seed = int(os.environ.get("VECTOR_MOCK_SEED", "42"))
    ds = generate_dataset(seed)
    payload = dataset_to_json_dict(ds)
    out_dir = _BACKEND / "mock_connectors" / "fixtures" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "dataset.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} (seed={seed})")


if __name__ == "__main__":
    main()
