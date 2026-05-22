#!/usr/bin/env python3
"""Print AA1–AA7 continuity proof panel for a tenant (P1-G / Phase 2.2)."""

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

from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    DEFAULT_TENANT_ID,
    build_continuity_proof_panel_v1,
    format_continuity_proof_panel_text_v1,
)

TENANT_DEFAULT = str(DEFAULT_TENANT_ID)


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def main() -> int:
    parser = argparse.ArgumentParser(description="AA1–AA7 continuity proof panel")
    parser.add_argument("--tenant", default=os.environ.get("PROOF_TENANT_ID", TENANT_DEFAULT))
    parser.add_argument("--pipeline-run", default="")
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--ops-log-path", default="")
    parser.add_argument("--wedge-free-ack", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
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
        panel = build_continuity_proof_panel_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            window_hours=args.window_hours,
            ops_log_text=ops_log_text,
            wedge_free_ack=args.wedge_free_ack,
        )

    text = format_continuity_proof_panel_text_v1(panel)
    if args.as_json:
        print(json.dumps(panel, indent=2, default=str))
    else:
        print(text)

    summary = panel.get("summary") or {}
    return 0 if int(summary.get("fail_count") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
