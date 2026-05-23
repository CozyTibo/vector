#!/usr/bin/env python3
"""Phase C step C5 — AA5 requires jobs_completed > 0 prod proof."""

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

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
    probe_prod_ecs_deploy_v1,
    save_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c5_aa5_synthesis_jobs_completed import (
    DEFAULT_TENANT_ID,
    evaluate_p0_c5_aa5_synthesis_jobs_completed_proof_v1,
    snapshot_c5_aa5_synthesis_truth_v1,
    verify_c5_aa5_synthesis_jobs_completed_wiring_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
    TraceOnlyProdSignoffError,
    add_trace_only_ci_argparse_v1,
    resolve_trace_only_cli_v1,
    save_p0_step_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
    warn_deprecated_continuity_proof_script_v1,
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
    warn_deprecated_continuity_proof_script_v1(__file__)

    parser = argparse.ArgumentParser(description="Phase C.5 AA5 synthesis jobs_completed prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--pipeline-run", default="")
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--dry-run", action="store_true")
    add_trace_only_ci_argparse_v1(parser)
    parser.add_argument("--use-deployed-closure", action="store_true")
    parser.add_argument("--wedge-free-ack", action="store_true")
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
    pipeline_run_id = uuid.UUID(args.pipeline_run) if args.pipeline_run.strip() else None
    deploy_started = datetime.now(UTC)
    prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
    wiring = verify_c5_aa5_synthesis_jobs_completed_wiring_v1()

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        snapshot = snapshot_c5_aa5_synthesis_truth_v1(session, tenant_id=tenant_id)
        panel = build_continuity_proof_panel_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            wedge_free_ack=args.wedge_free_ack,
        )
    panel_text = format_continuity_proof_panel_text_v1(panel)
    print(panel_text)

    proof = evaluate_p0_c5_aa5_synthesis_jobs_completed_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        snapshot=snapshot,
        panel=panel,
        deploy_recorded_at=deploy_started,
        trace_only=trace_only,
    )
    proof["wiring"] = wiring
    print(json.dumps(proof, indent=2, default=str))

    if args.dry_run:
        return 0 if proof["p0_c5_pass"] else 1

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    aa5 = dict((panel.get("gates") or {}).get("AA5") or {})
    step_record = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p0_c5_pass": proof["p0_c5_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": wiring.get("wiring_ok"),
        "aa5_verdict": aa5.get("verdict"),
        "aa5_detail": aa5.get("detail"),
        "started_only_aa5_fake_passes": snapshot.get("started_only_aa5_fake_passes"),
        "use_deployed_closure": args.use_deployed_closure,
    }
    saved = save_p0_step_baseline_v1(
        baseline_path,
        baseline,
        step_key="step_c5_aa5_synthesis_jobs_completed",
        step_record=step_record,
        trace_only=trace_only,
        save_fn=save_continuity_p0_baseline_v1,
    )
    if saved is None:
        print("baseline write skipped (CI --trace-only)", file=sys.stderr)
    else:
        print(f"baseline updated: {saved}")

    return 0 if proof["p0_c5_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
