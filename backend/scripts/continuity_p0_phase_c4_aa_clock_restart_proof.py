#!/usr/bin/env python3
"""Phase C step C4 — restart 48h AA M3 hold clock after Phase A+B+C strict gates."""

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
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c4_aa_clock_restart import (
    build_aa_clock_c4_restart_t0_v1,
    evaluate_abc_prerequisites_from_baseline_v1,
    evaluate_aa_clock_hold_progress_v1,
    evaluate_p0_c4_aa_clock_restart_proof_v1,
    load_aa_clock_t0_baseline_v1,
    mark_prior_t0_superseded_v1,
    save_aa_clock_t0_baseline_v1,
    verify_c4_aa_clock_restart_wiring_v1,
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
from vector.domains.cortex.substrate_pipeline.continuity_p2_aa_clock import (
    CONTINUITY_AA_HOLD_HOURS_V1,
    continuity_aa_clock_baseline_path_v1,
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
    warn_deprecated_continuity_proof_script_v1(__file__)

    parser = argparse.ArgumentParser(
        description="Phase C.4 — restart 48h AA clock after A+B+C (supersedes false T0)"
    )
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--pipeline-run", default="", help="Optional pipeline run for AA panel")
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--p0-baseline-date", default="2026-05-22")
    parser.add_argument("--clock-baseline-date", default="2026-05-22")
    parser.add_argument("--wedge-free-ack", action="store_true")
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
    pipeline_run_id = uuid.UUID(args.pipeline_run) if args.pipeline_run.strip() else None
    deploy_started = datetime.now(UTC)
    clock_started = deploy_started

    p0_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.p0_baseline_date,
    )
    p0_baseline = load_continuity_p0_baseline_v1(p0_path)
    abc = evaluate_abc_prerequisites_from_baseline_v1(p0_baseline)
    if not abc.get("all_prerequisites_pass"):
        print(json.dumps({"abc_prerequisites": abc}, indent=2), file=sys.stderr)
        if not trace_only:
            return 2

    prod_deploy = probe_prod_ecs_deploy_v1(expected_sha=closure_sha)
    wiring = verify_c4_aa_clock_restart_wiring_v1()

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

    t0_path = continuity_aa_clock_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.clock_baseline_date,
    )
    prior_t0 = load_aa_clock_t0_baseline_v1(t0_path)
    prior_nonempty = bool(prior_t0)

    if prior_nonempty and not args.dry_run and not trace_only:
        archived = mark_prior_t0_superseded_v1(
            prior_t0,
            superseded_at=clock_started,
            superseded_by_step="step_c4_aa48_clock_restart",
            new_clock_started_at=clock_started,
        )
        archive_path = t0_path.with_name(
            t0_path.stem + "_superseded_pre_c4" + t0_path.suffix
        )
        save_aa_clock_t0_baseline_v1(archive_path, archived)
        print(f"prior T0 archived: {archive_path}", file=sys.stderr)

    t0_baseline = build_aa_clock_c4_restart_t0_v1(
        panel=panel,
        closure_git_sha=closure_sha,
        tenant_id=tenant_id,
        abc_prerequisites=abc,
        prior_t0=prior_t0 if prior_nonempty else None,
        wedge_free_ack=args.wedge_free_ack,
        clock_started_at=clock_started,
    )
    hold_progress = evaluate_aa_clock_hold_progress_v1(t0_baseline=t0_baseline, panel=panel)

    proof = evaluate_p0_c4_aa_clock_restart_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        panel=panel,
        t0_baseline=t0_baseline,
        abc_prerequisites=abc,
        prior_t0=prior_t0 if prior_nonempty else None,
        hold_progress=hold_progress,
        deploy_recorded_at=deploy_started,
        trace_only=trace_only,
    )
    proof["wiring"] = wiring
    proof["hold_progress"] = hold_progress
    print(json.dumps(proof, indent=2, default=str))

    if args.dry_run:
        return 0 if proof["p0_c4_pass"] else 1

    if not trace_only:
        save_aa_clock_t0_baseline_v1(t0_path, t0_baseline)
        print(f"C4 T0 clock baseline written: {t0_path}", file=sys.stderr)

        step_record = {
            "validated_at": datetime.now(UTC).isoformat(),
            "closure_git_sha": closure_sha,
            "tenant_id": str(tenant_id),
            "p0_c4_pass": proof["p0_c4_pass"],
            "checks": proof["checks"],
            "checks_advisory": proof.get("checks_advisory"),
            "wiring_ok": wiring.get("wiring_ok"),
            "clock_started_at": t0_baseline.get("clock_started_at"),
            "clock_deadline_at": t0_baseline.get("clock_deadline_at"),
            "hold_hours_required": CONTINUITY_AA_HOLD_HOURS_V1,
            "prior_t0_superseded": prior_nonempty,
            "prior_t0_clock_started_at": t0_baseline.get("prior_t0_clock_started_at"),
            "abc_prerequisites_all_pass": abc.get("all_prerequisites_pass"),
            "all_aa_gates_pass_at_restart": hold_progress.get("all_aa_gates_pass_now"),
            "t0_baseline_path": str(t0_path.relative_to(REPO_ROOT)),
            "use_deployed_closure": args.use_deployed_closure,
        }
        saved = save_p0_step_baseline_v1(
            p0_path,
            p0_baseline,
            step_key="step_c4_aa48_clock_restart",
            step_record=step_record,
            trace_only=False,
            save_fn=save_continuity_p0_baseline_v1,
        )
        if saved:
            print(f"continuity P0 baseline updated: {saved}", file=sys.stderr)

    return 0 if proof["p0_c4_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
