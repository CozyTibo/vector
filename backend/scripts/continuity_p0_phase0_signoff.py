#!/usr/bin/env python3
"""Phase 0 step 0.6 — P0 sign-off gate; record step_0_6 in continuity baseline."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_signoff import (
    apply_step_0_6_to_baseline_v1,
    evaluate_p0_signoff_v1,
)

TENANT_DEFAULT = "c08ef32b-f89a-40f6-9566-e19b5329436f"
DEFAULT_RUN = "ce7df86d-b229-4467-ad28-1109ed119d34"


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0 step 0.6 P0 sign-off")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--pipeline-run", default=DEFAULT_RUN)
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--ci-only",
        action="store_true",
        help="Evaluate P0-D + baseline only (no prod DB)",
    )
    args = parser.parse_args()

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    if not baseline.get("phase0_complete"):
        print("FAIL: run step 0.5 closure first (phase0_complete missing)", file=sys.stderr)
        return 1

    tenant_id = uuid.UUID(args.tenant)
    pipeline_run_id = uuid.UUID(args.pipeline_run) if args.pipeline_run else None

    if args.ci_only:
        from vector.domains.cortex.substrate_pipeline.continuity_p0_signoff import (
            verify_p0_d_ci_gates_v1,
        )

        signoff = {
            "step": "0.6_p0_signoff",
            "recorded_at": datetime.now(UTC).isoformat(),
            "p0_d_ci": verify_p0_d_ci_gates_v1(repo_root=REPO_ROOT),
            "baseline_phase0_complete": True,
            "verification": {"step_06_pass": False, "note": "ci_only_partial"},
        }
    else:
        engine = create_engine(_db_url())
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as session:
            signoff = evaluate_p0_signoff_v1(
                session,
                tenant_id=tenant_id,
                baseline=baseline,
                repo_root=REPO_ROOT,
                pipeline_run_id=pipeline_run_id,
            )
        signoff["recorded_at"] = datetime.now(UTC).isoformat()

    baseline = apply_step_0_6_to_baseline_v1(baseline, signoff)
    save_continuity_p0_baseline_v1(baseline_path, baseline)

    print(json.dumps(signoff, indent=2, default=str))
    print(f"wrote {baseline_path}", file=sys.stderr)

    if not signoff.get("p0_signoff_pass") and not signoff.get("verification", {}).get("step_06_pass"):
        if not args.ci_only:
            return 1
    return 0 if signoff.get("verification", {}).get("step_06_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
