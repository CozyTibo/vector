#!/usr/bin/env python3
"""Phase B step B5 — graph-hash autonomous chain (walk → TCRE → 07) prod proof."""

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
from vector.domains.cortex.substrate_pipeline.continuity_p0_graph_hash_autonomous_chain import (
    DEFAULT_TENANT_ID,
    evaluate_p0_b5_graph_hash_autonomous_chain_proof_v1,
    snapshot_graph_hash_autonomous_chain_v1,
    verify_b5_graph_hash_autonomous_chain_wiring_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
    TraceOnlyProdSignoffError,
    add_trace_only_ci_argparse_v1,
    resolve_trace_only_cli_v1,
    save_p0_step_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain import (
    run_graph_hash_autonomous_chain_v1,
    seed_stale_graph_hash_for_chain_v1,
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
    parser = argparse.ArgumentParser(description="Phase B.5 graph-hash autonomous chain prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument(
        "--drive-chain",
        action="store_true",
        help="Run full 04→07 chain on a new pipeline run (expensive; skips 02/03)",
    )
    parser.add_argument(
        "--include-upstream",
        action="store_true",
        help="With --drive-chain, also run phases 02–03",
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
    wiring = verify_b5_graph_hash_autonomous_chain_wiring_v1()

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)
    chain_drive: dict | None = None

    with SessionLocal() as session:
        snapshot = snapshot_graph_hash_autonomous_chain_v1(session, tenant_id=tenant_id)
        need_drive = args.drive_chain or int(snapshot.get("complete_chains_in_window") or 0) == 0
        if need_drive and not trace_only and not args.dry_run:
            seed_stale_graph_hash_for_chain_v1(session, tenant_id=tenant_id)
            chain_drive = run_graph_hash_autonomous_chain_v1(
                session,
                tenant_id=tenant_id,
                run_upstream_phases=args.include_upstream,
                force_graph_hash_schedule=True,
            )
            session.commit()
            snapshot = snapshot_graph_hash_autonomous_chain_v1(session, tenant_id=tenant_id)
        elif need_drive and args.dry_run:
            chain_drive = {"dry_run": True, "chain_ok": False}

    proof = evaluate_p0_b5_graph_hash_autonomous_chain_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        snapshot=snapshot,
        chain_drive=chain_drive,
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
    step_record = {
        "validated_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_sha,
        "tenant_id": str(tenant_id),
        "p0_b5_pass": proof["p0_b5_pass"],
        "checks": proof["checks"],
        "checks_advisory": proof.get("checks_advisory"),
        "wiring_ok": wiring.get("wiring_ok"),
        "complete_chains_in_window": snapshot.get("complete_chains_in_window"),
        "drive_chain": args.drive_chain,
        "dry_run": args.dry_run,
        "use_deployed_closure": args.use_deployed_closure,
    }
    saved = save_p0_step_baseline_v1(
        baseline_path,
        baseline,
        step_key="step_b5_graph_hash_autonomous_chain",
        step_record=step_record,
        trace_only=trace_only,
        save_fn=save_continuity_p0_baseline_v1,
    )
    if saved is None:
        print("baseline write skipped (CI --trace-only)", file=sys.stderr)
    else:
        print(f"baseline updated: {saved}")

    return 0 if proof["p0_b5_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
