#!/usr/bin/env python3
"""Phase B step B4 — phase 05 walks persisted when scheduling eligible prod proof."""

from __future__ import annotations

import argparse
import functools
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
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

from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    schedule_octs_walks_for_tenant_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase05_walks_persisted import (
    DEFAULT_TENANT_ID,
    evaluate_p0_b4_phase05_walks_persisted_proof_v1,
    snapshot_phase05_walks_persisted_v1,
    verify_b4_phase05_walks_persisted_wiring_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
    TraceOnlyProdSignoffError,
    add_trace_only_ci_argparse_v1,
    resolve_trace_only_cli_v1,
    save_p0_step_baseline_v1,
)

TENANT_DEFAULT = str(DEFAULT_TENANT_ID)


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def main() -> int:
    from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
        warn_deprecated_continuity_proof_script_v1,
    )

    warn_deprecated_continuity_proof_script_v1(__file__)

    parser = argparse.ArgumentParser(description="Phase B.4 phase 05 walks persisted prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--drive-schedule",
        action="store_true",
        help="Run schedule_octs_walks pass (after_phase_05 trigger)",
    )
    parser.add_argument("--dry-run", action="store_true")
    add_trace_only_ci_argparse_v1(parser)
    parser.add_argument("--use-deployed-closure", action="store_true")
    args = parser.parse_args()

    try:
        trace_only = resolve_trace_only_cli_v1(requested=args.trace_only)
    except TraceOnlyProdSignoffError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    if args.use_deployed_closure:
        from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
            snapshot_prod_ecs_deploy_v1,
        )

        closure_sha = str(snapshot_prod_ecs_deploy_v1()["api"]["image_tag"])
        print(f"using deployed API tag as closure: {closure_sha[:12]}…", file=sys.stderr)

    tenant_id = uuid.UUID(args.tenant)
    deploy_started = datetime.now(UTC)
    prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
    wiring = verify_b4_phase05_walks_persisted_wiring_v1()

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)
    schedule_drive: dict | None = None

    with SessionLocal() as session:
        snapshot = snapshot_phase05_walks_persisted_v1(session, tenant_id=tenant_id)
        need_drive = args.drive_schedule or int(
            snapshot.get("slices_with_walks_persisted_or_available") or 0
        ) == 0
        if need_drive and not trace_only:
            schedule_drive = schedule_octs_walks_for_tenant_v1(
                tenant_id=tenant_id,
                trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
                force=args.drive_schedule,
                session=session,
            )
            if not args.dry_run and schedule_drive.get("scheduled"):
                session.commit()
            snapshot = snapshot_phase05_walks_persisted_v1(session, tenant_id=tenant_id)

    proof = evaluate_p0_b4_phase05_walks_persisted_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        snapshot=snapshot,
        schedule_drive=schedule_drive,
        deploy_recorded_at=deploy_started,
        trace_only=trace_only,
    )
    proof["wiring"] = wiring
    print(json.dumps(proof, indent=2, default=str))

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    latest = dict(snapshot.get("latest_phase_05") or {})
    step_record = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p0_b4_pass": proof["p0_b4_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": wiring.get("wiring_ok"),
        "durable_walk_row_count": snapshot.get("durable_walk_row_count"),
        "slices_with_walks": snapshot.get("slices_with_walks_persisted_or_available"),
        "latest_walks_persisted": latest.get("walks_persisted"),
        "drive_schedule": args.drive_schedule,
        "dry_run": args.dry_run,
        "use_deployed_closure": args.use_deployed_closure,
    }
    saved = save_p0_step_baseline_v1(
        baseline_path,
        baseline,
        step_key="step_b4_phase05_walks_persisted",
        step_record=step_record,
        trace_only=trace_only,
        save_fn=save_continuity_p0_baseline_v1,
    )
    if saved is None:
        print("baseline write skipped (CI --trace-only)", file=sys.stderr)
    else:
        print(f"baseline updated: {saved}")

    return 0 if proof["p0_b4_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
