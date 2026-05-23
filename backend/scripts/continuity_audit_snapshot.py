#!/usr/bin/env python3
"""Phase C step C3 — unified continuity audit snapshot (panel + SQL + phase slices)."""

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

from vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot import (
    build_continuity_audit_snapshot_v1,
    format_continuity_audit_snapshot_text_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import DEFAULT_TENANT_ID

TENANT_DEFAULT = str(DEFAULT_TENANT_ID)


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified continuity audit snapshot (AA panel + substrate SQL + phase slices)"
    )
    parser.add_argument("--tenant", default=os.environ.get("PROOF_TENANT_ID", TENANT_DEFAULT))
    parser.add_argument("--pipeline-run", default="")
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--ops-log-path", default="")
    parser.add_argument("--wedge-free-ack", action="store_true")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--text-only", action="store_true", help="Print human text without JSON")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()

    tenant_id = uuid.UUID(args.tenant)
    pipeline_run_id = uuid.UUID(args.pipeline_run) if args.pipeline_run.strip() else None
    ops_log_text: str | None = None
    if args.ops_log_path:
        ops_log_text = Path(args.ops_log_path).read_text()

    db_url = args.database_url.strip() or _db_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        snapshot = build_continuity_audit_snapshot_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            window_hours=args.window_hours,
            ops_log_text=ops_log_text,
            wedge_free_ack=args.wedge_free_ack,
            repo_root=REPO_ROOT,
            baseline_date=args.baseline_date,
        )

    text = format_continuity_audit_snapshot_text_v1(snapshot)
    if args.text_only:
        print(text)
    elif args.as_json:
        print(json.dumps(snapshot, indent=2, default=str))
    else:
        print(text)
        print("")
        print(json.dumps(snapshot, indent=2, default=str))

    summary = dict(snapshot.get("summary") or {})
    panel_fail = int(summary.get("panel_fail_count") or 0)
    return 0 if panel_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
