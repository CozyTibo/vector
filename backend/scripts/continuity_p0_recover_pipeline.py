#!/usr/bin/env python3
"""Phase 0 step 0.3 — recover Fizzer pipeline run and enqueue execution (P0-C)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")
os.environ.setdefault("VECTOR_USE_MOCK_CONNECTORS", "false")

_env = Path(__file__).resolve().parents[2] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    RecoveryStrategyV1,
    recover_continuity_p0_pipeline_v1,
)

TENANT_DEFAULT = "c08ef32b-f89a-40f6-9566-e19b5329436f"
BASELINES = Path(__file__).resolve().parents[2] / "DOCS" / "audits" / "baselines"


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _load_baseline() -> dict:
    path = BASELINES / "continuity_p0_2026-05-22.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_baseline(data: dict) -> Path:
    BASELINES.mkdir(parents=True, exist_ok=True)
    path = BASELINES / "continuity_p0_2026-05-22.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="P0-C pipeline recovery for continuity Phase 0")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument(
        "--strategy",
        choices=("new_run", "recover_in_place"),
        default="new_run",
        help="new_run: post_ingestion run + mirror 02-04; recover_in_place: reset failed run",
    )
    parser.add_argument("--source-run", default="", help="optional failed pipeline run uuid")
    parser.add_argument(
        "--resume-from-phase",
        default="phase_05_traversal",
        help="for recover_in_place: requeue from this phase (e.g. phase_06_tcre after 05 completed)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="commit DB recovery only; defer Celery enqueue to prod sweeper (no local Redis)",
    )
    args = parser.parse_args()

    tenant_id = uuid.UUID(args.tenant)
    source_run = uuid.UUID(args.source_run) if args.source_run.strip() else None
    strategy: RecoveryStrategyV1 = args.strategy

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        if args.dry_run:
            from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
                get_latest_failed_pipeline_run_v1,
            )

            failed = get_latest_failed_pipeline_run_v1(session, tenant_id=tenant_id)
            print(
                json.dumps(
                    {
                        "dry_run": True,
                        "strategy": strategy,
                        "latest_failed_run_id": str(failed.id) if failed else None,
                        "latest_failed_status": failed.status if failed else None,
                    },
                    indent=2,
                )
            )
            return 0

        out = recover_continuity_p0_pipeline_v1(
            session,
            tenant_id=tenant_id,
            strategy=strategy,
            source_pipeline_run_id=source_run,
            resume_from_phase=args.resume_from_phase,
            enqueue_celery=not args.db_only,
        )
        session.commit()
        print(json.dumps(out, indent=2))

        if not out.get("recovered"):
            return 1

        baseline = _load_baseline()
        run_status = (out.get("reopen") or {}).get("pipeline_status") or out.get("pipeline_status")
        baseline["step_0_3_pipeline_recovery"] = {
            **(baseline.get("step_0_3_pipeline_recovery") or {}),
            **out,
            "recorded_at": datetime.now(UTC).isoformat(),
            "verification": {
                "step_03_pass": run_status == "running" and out.get("pipeline_run_id") is not None,
                "prior_failed_run_superseded": bool(out.get("prior_failed_run_id")),
            },
        }
        path = _save_baseline(baseline)
        print(f"wrote {path}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
