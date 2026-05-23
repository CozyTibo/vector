#!/usr/bin/env python3
"""Phase 2 step 2.4 — start M3 forty-eight-hour AA hold clock (T0 baseline JSON)."""

from __future__ import annotations

import argparse
import functools
import json
import os
import subprocess
import sys
import time
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

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c4_aa_clock_restart import (
    evaluate_aa_clock_hold_progress_v1,
    load_aa_clock_t0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p2_aa_clock import (
    CONTINUITY_AA_HOLD_HOURS_V1,
    build_aa_clock_t0_baseline_v1,
    continuity_aa_clock_baseline_path_v1,
    evaluate_p2_4_aa_clock_proof_v1,
)
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


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2.4 — daily 48h AA hold check (use continuity_p0_phase_c4_aa_clock_restart_proof "
            "for initial restart after A+B+C)"
        )
    )
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--pipeline-run", default="ce7df86d-b229-4467-ad28-1109ed119d34")
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--wait-for-deploy", type=int, default=600)
    parser.add_argument("--trace-only", action="store_true")
    parser.add_argument(
        "--wedge-free-ack",
        action="store_true",
        help="Only valid at C4 clock start — daily hold checks must use --ops-log-path (AA7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate only; do not write T0 baseline files",
    )
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    tenant_id = uuid.UUID(args.tenant)
    pipeline_run_id = uuid.UUID(args.pipeline_run) if args.pipeline_run.strip() else None
    deploy_started = datetime.now(UTC)
    clock_started = deploy_started

    deadline = time.monotonic() + max(0, args.wait_for_deploy)
    prod_deploy: dict = {}
    while True:
        prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
        if prod_deploy["verification"]["deploy_matches_closure_sha"] or args.trace_only:
            break
        if time.monotonic() >= deadline:
            break
        print(
            f"waiting for ECS {closure_sha[:12]}… "
            f"api={prod_deploy['api']['image_tag']} worker={prod_deploy['worker']['image_tag']}",
            file=sys.stderr,
        )
        time.sleep(30)

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        panel = build_continuity_proof_panel_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            wedge_free_ack=args.wedge_free_ack,
            repo_root=REPO_ROOT,
            baseline_date=args.baseline_date,
            at_clock_start=False,
        )
    panel_text = format_continuity_proof_panel_text_v1(panel)
    print(panel_text)

    t0_path = continuity_aa_clock_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    existing_t0 = load_aa_clock_t0_baseline_v1(t0_path)
    if int(existing_t0.get("clock_restart_generation") or 0) >= 2:
        t0_baseline = existing_t0
        hold_progress = evaluate_aa_clock_hold_progress_v1(
            t0_baseline=t0_baseline,
            panel=panel,
            now=clock_started,
        )
        t0_baseline = dict(t0_baseline)
        t0_baseline["hold_hours_elapsed"] = hold_progress["hold_hours_elapsed"]
        print(json.dumps({"hold_progress": hold_progress}, indent=2), file=sys.stderr)
    else:
        print(
            "WARN: no C4 restart T0 — run continuity_p0_phase_c4_aa_clock_restart_proof.py first",
            file=sys.stderr,
        )
        t0_baseline = build_aa_clock_t0_baseline_v1(
            panel=panel,
            closure_git_sha=closure_sha,
            tenant_id=tenant_id,
            wedge_free_ack=args.wedge_free_ack,
            clock_started_at=clock_started,
        )
        hold_progress = None

    proof = evaluate_p2_4_aa_clock_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        panel=panel,
        t0_baseline=t0_baseline,
        deploy_recorded_at=deploy_started,
        trace_only=args.trace_only,
    )
    print(json.dumps(proof, indent=2, default=str))

    if args.dry_run:
        return 0 if proof["p2_4_pass"] else 1

    if int(t0_baseline.get("clock_restart_generation") or 0) < 2:
        t0_path.parent.mkdir(parents=True, exist_ok=True)
        t0_path.write_text(json.dumps(t0_baseline, indent=2) + "\n", encoding="utf-8")
        print(f"T0 baseline written: {t0_path}")
    else:
        save_t0 = dict(t0_baseline)
        t0_path.parent.mkdir(parents=True, exist_ok=True)
        t0_path.write_text(json.dumps(save_t0, indent=2) + "\n", encoding="utf-8")
        print(f"T0 baseline updated (hold progress): {t0_path}")

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    baseline["step_2_4_aa48_clock"] = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p2_4_pass": proof["p2_4_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "clock_started_at": t0_baseline.get("clock_started_at"),
        "clock_deadline_at": t0_baseline.get("clock_deadline_at"),
        "hold_hours_required": CONTINUITY_AA_HOLD_HOURS_V1,
        "m3_autonomously_alive_at_t0": t0_baseline.get("m3_autonomously_alive_at_t0"),
        "gate_verdicts": t0_baseline.get("gate_verdicts"),
        "t0_baseline_path": str(t0_path.relative_to(REPO_ROOT)),
        "trace_only": args.trace_only,
    }
    save_continuity_p0_baseline_v1(baseline_path, baseline)
    print(f"continuity baseline updated: {baseline_path}")

    return 0 if proof["p2_4_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
