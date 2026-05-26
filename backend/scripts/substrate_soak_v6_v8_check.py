#!/usr/bin/env python3
"""Wave 5 — 24h Fizzer soak checks V6–V8 from live substrate_truth_v1.

  python backend/scripts/substrate_soak_v6_v8_check.py --tenant <uuid> --json
  python backend/scripts/substrate_soak_v6_v8_check.py --tenant <uuid> --isolation-waiver
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

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

print = functools.partial(print, flush=True)  # noqa: A001

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from vector.domains.cortex.execution.execution_event_triggers import (  # noqa: E402
    DETAIL_KEY_LAST_GRAPH_HASH_V1,
)
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1  # noqa: E402
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (  # noqa: E402
    DEFAULT_TENANT_ID,
)
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (  # noqa: E402
    evaluate_soak_contract_v6_v8_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import (  # noqa: E402
    build_substrate_truth_v1,
)


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
    parser = argparse.ArgumentParser(description="Substrate soak V6–V8 (Wave 5)")
    parser.add_argument("--tenant", default=str(DEFAULT_TENANT_ID))
    parser.add_argument("--isolation-waiver", action="store_true")
    parser.add_argument("--prior-graph-hash", default="", help="Hash from prior soak sample for V7")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    tenant_id = uuid.UUID(args.tenant.strip())
    engine = create_engine(_db_url())
    Session = sessionmaker(bind=engine)
    with Session() as session:
        truth = build_substrate_truth_v1(session, tenant_id=tenant_id)
        lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
        if lease is not None and isinstance(truth.get("motion"), dict):
            detail = dict(lease.detail_json or {})
            truth["motion"]["last_graph_projection_hash"] = detail.get(DETAIL_KEY_LAST_GRAPH_HASH_V1)

    soak = evaluate_soak_contract_v6_v8_v1(
        truth,
        isolation_waiver=args.isolation_waiver,
        prior_graph_hash=args.prior_graph_hash.strip() or None,
    )
    payload = {"substrate_truth_excerpt": {"overall_status": truth.get("overall_status"), "graph": truth.get("graph")}, **soak}
    text = json.dumps(payload, indent=2, default=str)
    if args.json:
        print(text)
    else:
        for check in soak["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"{check['id']} {check['name']}: {status} {check.get('detail')}")
    return 0 if soak["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
