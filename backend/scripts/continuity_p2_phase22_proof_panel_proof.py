#!/usr/bin/env python3
"""Phase 2 step 2.2 — continuity_proof_panel prod proof + baseline."""

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
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    DEFAULT_TENANT_ID,
    build_continuity_proof_panel_v1,
    evaluate_p2_2_proof_panel_proof_v1,
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
    parser = argparse.ArgumentParser(description="Phase 2.2 continuity proof panel prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--pipeline-run", default="ce7df86d-b229-4467-ad28-1109ed119d34")
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--wait-for-deploy", type=int, default=600)
    parser.add_argument("--trace-only", action="store_true")
    parser.add_argument("--wedge-free-ack", action="store_true", default=True)
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    tenant_id = uuid.UUID(args.tenant)
    pipeline_run_id = uuid.UUID(args.pipeline_run) if args.pipeline_run.strip() else None
    deploy_started = datetime.now(UTC)

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
        )
    panel_text = format_continuity_proof_panel_text_v1(panel)
    print(panel_text)

    proof = evaluate_p2_2_proof_panel_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        panel=panel,
        panel_text=panel_text,
        deploy_recorded_at=deploy_started,
        trace_only=args.trace_only,
    )
    print(json.dumps(proof, indent=2, default=str))

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    baseline["step_2_2_continuity_proof_panel"] = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p2_2_pass": proof["p2_2_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "panel_summary": panel.get("summary"),
        "gate_verdicts": {
            gid: (panel.get("gates") or {}).get(gid, {}).get("verdict")
            for gid in panel.get("gate_order") or []
        },
        "trace_only": args.trace_only,
    }
    save_continuity_p0_baseline_v1(baseline_path, baseline)
    print(f"baseline updated: {baseline_path}")

    return 0 if proof["p2_2_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
