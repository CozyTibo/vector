#!/usr/bin/env python3
"""Wave S4 step 18 — reconcile stale synthesis jobs (running/queued) for a tenant.

  cd backend
  python scripts/synthesis_failed_jobs_reconcile.py --tenant <uuid>
  python scripts/synthesis_failed_jobs_reconcile.py --tenant <uuid> --apply --out receipt.json
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

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
    reconcile_stale_queued_synthesis_jobs_v1,
    reconcile_stale_synthesis_jobs_v1,
    snapshot_synthesis_job_status_histogram_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.settings import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile stale cortex_synthesis_jobs rows")
    parser.add_argument("--tenant", required=True, help="Tenant UUID")
    parser.add_argument("--apply", action="store_true", help="Persist reconciliation (default dry-run)")
    parser.add_argument("--out", type=Path, help="Write JSON receipt")
    args = parser.parse_args()
    tenant_id = uuid.UUID(args.tenant.strip())
    dry_run = not args.apply

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        before = snapshot_synthesis_job_status_histogram_v1(session, tenant_id=tenant_id)
        running = reconcile_stale_synthesis_jobs_v1(
            session,
            tenant_id=tenant_id,
            stale_after_seconds=int(settings.cortex_synthesis_job_running_stale_seconds),
            dry_run=dry_run,
        )
        queued = reconcile_stale_queued_synthesis_jobs_v1(
            session,
            tenant_id=tenant_id,
            stale_after_seconds=int(settings.cortex_synthesis_job_queued_stale_seconds),
            dry_run=dry_run,
        )
        if not dry_run:
            session.commit()
        after = snapshot_synthesis_job_status_histogram_v1(session, tenant_id=tenant_id)
        failed_total = int(
            session.scalar(
                select(func.count())
                .select_from(CortexSynthesisJob)
                .where(
                    CortexSynthesisJob.tenant_id == tenant_id,
                    CortexSynthesisJob.status == "failed",
                )
            )
            or 0
        )

    receipt = {
        "tenant_id": str(tenant_id),
        "dry_run": dry_run,
        "jobs_before": before,
        "jobs_after": after,
        "running_reconcile": running,
        "queued_reconcile": queued,
        "failed_job_rows": failed_total,
    }
    print(json.dumps(receipt, indent=2))
    if args.out:
        args.out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
