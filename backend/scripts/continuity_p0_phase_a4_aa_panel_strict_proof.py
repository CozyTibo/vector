#!/usr/bin/env python3
"""Phase A step A4 — strict AA1/AA6 continuity proof panel prod proof."""

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

from vector.domains.cortex.substrate_pipeline.continuity_p0_aa_panel_strict import (
    DEFAULT_TENANT_ID,
    evaluate_p0_a4_aa_panel_strict_proof_v1,
    verify_a4_aa_panel_strict_wiring_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
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
    parser = argparse.ArgumentParser(description="Phase A.4 strict AA1/AA6 panel prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--trace-only", action="store_true")
    parser.add_argument(
        "--use-deployed-closure",
        action="store_true",
        help="Use prod API ECS tag as closure SHA (same as A.2/A.3)",
    )
    args = parser.parse_args()

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
    if args.trace_only:
        prod_deploy["verification"]["deploy_matches_closure_sha"] = True

    wiring = verify_a4_aa_panel_strict_wiring_v1()
    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        panel = build_continuity_proof_panel_v1(
            session,
            tenant_id=tenant_id,
            window_hours=args.window_hours,
            wedge_free_ack=True,
        )
    panel_text = format_continuity_proof_panel_text_v1(panel)

    proof = evaluate_p0_a4_aa_panel_strict_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        panel=panel,
        panel_text=panel_text,
        deploy_recorded_at=deploy_started,
        trace_only=args.trace_only,
    )
    proof["wiring"] = wiring
    print(json.dumps(proof, indent=2, default=str))

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    gates = dict(panel.get("gates") or {})
    aa1_ev = dict((gates.get("AA1") or {}).get("evidence") or {})
    aa6_ev = dict((gates.get("AA6") or {}).get("evidence") or {})
    baseline["step_a4_aa_panel_strict"] = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p0_a4_pass": proof["p0_a4_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": wiring.get("wiring_ok"),
        "strict_aa_panel_schema_version": panel.get("strict_aa_panel_schema_version"),
        "aa1_verdict": (gates.get("AA1") or {}).get("verdict"),
        "aa6_verdict": (gates.get("AA6") or {}).get("verdict"),
        "aa1_jobs_completed": aa1_ev.get("jobs_completed"),
        "aa1_lawful_empty": aa1_ev.get("lawful_empty"),
        "aa6_forward_progress_signals": aa6_ev.get("forward_progress_signals"),
        "aa6_mat_only_pass": aa6_ev.get("mat_only_pass"),
        "m3_autonomously_alive": bool((panel.get("summary") or {}).get("m3_autonomously_alive")),
        "trace_only": args.trace_only,
    }
    save_continuity_p0_baseline_v1(baseline_path, baseline)
    print(f"baseline updated: {baseline_path}")

    return 0 if proof["p0_a4_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
