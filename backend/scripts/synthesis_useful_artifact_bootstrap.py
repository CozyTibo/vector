#!/usr/bin/env python3
"""Wave S4 step 20 — snapshot useful published synthesis artifacts (Fizzer sign-off).

  cd backend
  python scripts/synthesis_useful_artifact_bootstrap.py --tenant c08ef32b-f89a-40f6-9566-e19b5329436f
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")

REPO_ROOT = Path(__file__).resolve().parents[2]
_env = REPO_ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

print = functools.partial(print, flush=True)  # noqa: A001

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.synthesis.synthesis_useful_artifact_v1 import (
    FIZZER_TENANT_ID_V1,
    snapshot_published_useful_artifacts_v1,
)
from vector.settings import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Wave S4 useful synthesis artifact snapshot")
    parser.add_argument("--tenant", default=FIZZER_TENANT_ID_V1)
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    tenant_id = uuid.UUID(args.tenant.strip())

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        snap = snapshot_published_useful_artifacts_v1(
            session,
            tenant_id=tenant_id,
            lookback_days=args.lookback_days,
        )

    print(json.dumps(snap, indent=2))
    if args.out:
        args.out.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return 0 if snap.get("acceptance_met") else 1


if __name__ == "__main__":
    raise SystemExit(main())
