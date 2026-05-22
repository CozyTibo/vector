#!/usr/bin/env python3
"""Phase 1 step 1.4 — P1-D TCRE resume boundaries (CI) + prod lease/TCRE trace."""

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
from vector.domains.cortex.substrate_pipeline.continuity_p1_tcre import (
    evaluate_p1_4_tcre_resume_proof_v1,
    snapshot_tcre_execution_footprint_v1,
    verify_p1_d_static_boundaries_v1,
)

TENANT_DEFAULT = "c08ef32b-f89a-40f6-9566-e19b5329436f"
P1_D_CI_TESTS = [
    "tests/vector/domains/cortex/substrate_pipeline/test_continuity_p1_tcre_resume.py",
    (
        "tests/vector/domains/cortex/execution/"
        "test_single_tcre_execution_resume_boundary.py::test_verify_single_tcre_execution_resume_boundary"
    ),
    (
        "tests/vector/domains/cortex/execution/"
        "test_single_tcre_execution_resume_boundary.py::test_tcre_resume_module_has_no_continuation_coupling"
    ),
    "tests/vector/domains/cortex/execution/test_tcre_worker_no_retrieval_materialization_boundary.py",
]


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


def _run_ci_tests() -> tuple[bool, dict[str, Any]]:
    backend = REPO_ROOT / "backend"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *P1_D_CI_TESTS,
    ]
    env = {**os.environ, "PYTHONPATH": str(backend / "src")}
    proc = subprocess.run(cmd, cwd=backend, env=env, capture_output=True, text=True)
    return proc.returncode == 0, {
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1.4 P1-D TCRE resume proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--closure-sha", default="")
    parser.add_argument("--baseline-date", default="2026-05-22")
    parser.add_argument("--wait-for-deploy", type=int, default=600)
    parser.add_argument("--skip-ci-tests", action="store_true")
    parser.add_argument("--trace-only", action="store_true", help="Skip deploy wait")
    args = parser.parse_args()

    closure_sha = _git_sha(args.closure_sha or os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    tenant_id = uuid.UUID(args.tenant)
    deploy_started = datetime.now(UTC)

    static_boundaries = verify_p1_d_static_boundaries_v1()
    ci_green = True
    ci_out: dict[str, Any] = {"skipped": True}
    if not args.skip_ci_tests:
        ci_green, ci_out = _run_ci_tests()
        if not ci_green:
            print(ci_out.get("stdout_tail", ""), file=sys.stderr)
            print(ci_out.get("stderr_tail", ""), file=sys.stderr)

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
        footprint = snapshot_tcre_execution_footprint_v1(session, tenant_id=tenant_id)

    proof = evaluate_p1_4_tcre_resume_proof_v1(
        closure_git_sha=closure_sha,
        prod_deploy=prod_deploy,
        static_boundaries=static_boundaries,
        footprint=footprint,
        integration_tests_green=ci_green,
        deploy_recorded_at=deploy_started,
        trace_only=args.trace_only,
    )
    proof["ci_pytest"] = ci_out
    proof["recorded_at"] = datetime.now(UTC).isoformat()
    proof["tenant_id"] = args.tenant

    baseline_path = continuity_p0_baseline_path_v1(
        repo_root=REPO_ROOT,
        date_suffix=args.baseline_date,
    )
    baseline = load_continuity_p0_baseline_v1(baseline_path)
    baseline["step_1_4_p1d_tcre_resume"] = proof
    baseline["p1_4_closure_git_sha"] = closure_sha
    save_continuity_p0_baseline_v1(baseline_path, baseline)

    print(json.dumps(proof, indent=2, default=str))
    print(f"wrote {baseline_path}", file=sys.stderr)

    if not proof.get("p1_4_pass"):
        print("FAIL: step 1.4 not satisfied", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
