#!/usr/bin/env python3
"""Phase 0 step 0.4 — run prod execution slice(s) and prove P0-B (phase 05 COMPLETED)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")
os.environ.setdefault("VECTOR_USE_MOCK_CONNECTORS", "false")

_env = Path(__file__).resolve().parents[2] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vector.domains.cortex.execution.run_tenant_execution import run_tenant_convergence_v1
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase05_proof import (
    evaluate_p0_b_phase05_proof_v1,
)

TENANT_DEFAULT = "c08ef32b-f89a-40f6-9566-e19b5329436f"
BASELINES = Path(__file__).resolve().parents[2] / "DOCS" / "audits" / "baselines"
DEFAULT_RUN = "ce7df86d-b229-4467-ad28-1109ed119d34"


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _load_baseline() -> dict:
    path = BASELINES / "continuity_p0_2026-05-22.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_baseline(data: dict) -> Path:
    BASELINES.mkdir(parents=True, exist_ok=True)
    path = BASELINES / "continuity_p0_2026-05-22.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="P0-B phase 05 prod proof")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--pipeline-run", default=DEFAULT_RUN)
    parser.add_argument(
        "--max-slices",
        type=int,
        default=8,
        help="Max inline run_tenant_convergence_v1 invocations (time-budget may need >1)",
    )
    parser.add_argument(
        "--proof-only",
        action="store_true",
        help="Skip execution; only evaluate and record proof SQL",
    )
    args = parser.parse_args()

    tenant_id = uuid.UUID(args.tenant)
    pipeline_run_id = uuid.UUID(args.pipeline_run)

    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)

    slice_results: list[dict] = []
    proof: dict = {}
    if not args.proof_only:
        for i in range(max(1, args.max_slices)):
            with SessionLocal() as session:
                out = run_tenant_convergence_v1(
                    session,
                    tenant_id=tenant_id,
                    reason=f"continuity_p0_step04_slice_{i}",
                )
                session.commit()
                slice_results.append(out)
                proof = evaluate_p0_b_phase05_proof_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                )
            if proof.get("p0_b_pass"):
                break
    else:
        with SessionLocal() as session:
            proof = evaluate_p0_b_phase05_proof_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
            )

    proof["recorded_at"] = datetime.now(UTC).isoformat()
    proof["execution_slices"] = slice_results
    proof["verification"] = {
        "step_04_pass": bool(proof.get("p0_b_pass")),
        "cont_inv_01_partial": bool(proof.get("checks", {}).get("phase_05_status_completed")),
        "cont_inv_02": bool(proof.get("checks", {}).get("no_schema_path_error")),
    }

    baseline = _load_baseline()
    baseline["step_0_4_phase05_proof"] = proof
    path = _save_baseline(baseline)
    print(json.dumps(proof, indent=2, default=str))
    print(f"wrote {path}", file=sys.stderr)

    return 0 if proof.get("p0_b_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
