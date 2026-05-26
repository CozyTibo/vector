#!/usr/bin/env python3
"""Wave 0 — substrate truth audit snapshot for deploy baselines.

  python backend/scripts/substrate_truth_audit_snapshot.py --tenant <uuid> --json
  python backend/scripts/substrate_truth_audit_snapshot.py --tenant <uuid> --out DOCS/audits/baselines/foo.json
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
os.environ.setdefault("VECTOR_USE_MOCK_CONNECTORS", "false")

REPO_ROOT = Path(__file__).resolve().parents[2]
_env = REPO_ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

print = functools.partial(print, flush=True)  # noqa: A001

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import DEFAULT_TENANT_ID
from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import build_substrate_truth_v1

TENANT_DEFAULT = str(DEFAULT_TENANT_ID)


def _db_url() -> str:
    if os.environ.get("DATABASE_URL", "").strip():
        return os.environ["DATABASE_URL"].strip()
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Substrate truth audit snapshot (Wave 0)")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--out", type=str, default="", help="Write JSON to file")
    args = parser.parse_args()
    tenant_id = uuid.UUID(args.tenant.strip())

    engine = create_engine(_db_url())
    Session = sessionmaker(bind=engine)
    with Session() as session:
        snapshot = build_substrate_truth_v1(session, tenant_id=tenant_id)

    payload = {
        "baseline_kind": "substrate_truth_wave0",
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "captured_at_utc": snapshot.get("captured_at_utc"),
        "substrate_truth": snapshot,
        "acceptance_hints": {
            "overall_status_prefer": ["HEALTHY", "DEGRADED"],
            "isolated_pct_max": 90.0,
            "promotion_rule_count_min": 3,
        },
    }

    text = json.dumps(payload, indent=2, default=str)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n")
        print(f"wrote {out_path}")
    if args.json or not args.out:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
