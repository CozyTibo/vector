#!/usr/bin/env python3
"""Wave S2 — identity continuity audit snapshot (promotion rules, anchor boundary, candidates).

  python backend/scripts/identity_continuity_audit_snapshot.py --tenant <uuid> --json
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
from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
    build_semantic_readiness_v1,
    format_semantic_readiness_text_v1,
)

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


def build_identity_continuity_audit_snapshot_v1(session, *, tenant_id: uuid.UUID) -> dict:
    core = build_semantic_readiness_v1(session, tenant_id=tenant_id)
    return {
        "baseline_kind": "identity_continuity_wave_s2",
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "captured_at_utc": core.get("captured_at_utc"),
        "semantic_readiness": core,
        "identity_continuity": core.get("identity_continuity"),
        "graph_truth": core.get("graph_truth"),
        "acceptance": {
            "promotion_rule_count_green_min": 3,
            "candidate_inflation_ratio_green_max": 3.0,
            "anchors_missing_entity_pct_green_max": 50.0,
            "second_link_type": "deferred_no_new_type_without_prod_evidence",
        },
        "repro_command": "python backend/scripts/identity_continuity_audit_snapshot.py --tenant <id> --json",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Identity continuity audit snapshot")
    parser.add_argument("--tenant", "--tenant-id", dest="tenant", default=os.environ.get("PROOF_TENANT_ID", TENANT_DEFAULT))
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--database-url", default="")
    args = parser.parse_args()

    tenant_id = uuid.UUID(args.tenant)
    db_url = args.database_url.strip() or _db_url()
    SessionLocal = sessionmaker(bind=create_engine(db_url))

    with SessionLocal() as session:
        snapshot = build_identity_continuity_audit_snapshot_v1(session, tenant_id=tenant_id)

    text = format_semantic_readiness_text_v1(snapshot["semantic_readiness"])
    payload = json.dumps(snapshot, indent=2, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n")
        print(f"wrote {args.out}")
    if args.as_json:
        print(payload)
    else:
        print(text)
        print("")
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
