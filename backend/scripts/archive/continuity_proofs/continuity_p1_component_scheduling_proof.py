#!/usr/bin/env python3
"""Phase 1 step 1.1 — prod proof for P3′ component traversal scheduling (Fizzer)."""

from __future__ import annotations

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

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
    propagate_graph_completeness_stage_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    evaluate_traversal_schedule_v1,
)

TENANT_DEFAULT = "c08ef32b-f89a-40f6-9566-e19b5329436f"
BASELINES = REPO_ROOT / "DOCS" / "audits" / "baselines"


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def main() -> int:
    tenant_id = uuid.UUID(TENANT_DEFAULT)
    engine = create_engine(_db_url())
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        schedule = evaluate_traversal_schedule_v1(
            session,
            tenant_id=tenant_id,
            trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
        )
        graph_stage = propagate_graph_completeness_stage_v1(session, tenant_id=tenant_id)
        manifest = dict(
            (graph_stage.get("metrics") or {}).get("graph_completeness_propagation") or {}
        )

    proof = {
        "step": "1.1_p3_prime_component_scheduling",
        "tenant_id": TENANT_DEFAULT,
        "recorded_at": datetime.now(UTC).isoformat(),
        "schedule_evaluation": schedule,
        "graph_propagation_manifest": manifest,
        "checks": {
            "traversal_propagation_mode_component": schedule.get("traversal_propagation_mode")
            == "component",
            "islands_eligible_gte_1": int(schedule.get("islands_eligible_count") or 0) >= 1,
            "traversal_propagation_not_blocked": schedule.get("traversal_propagation_blocked")
            is False,
            "should_schedule_after_phase_05": schedule.get("should_schedule") is True,
            "manifest_islands_eligible_gte_1": int(manifest.get("islands_eligible_count") or 0)
            >= 1,
            "cont_inv_03_partial": int(schedule.get("islands_eligible_count") or 0) >= 1,
        },
    }
    proof["p1_1_pass"] = all(proof["checks"].values())
    proof["verification"] = {
        "step_11_pass": proof["p1_1_pass"],
        "cleared_for_step_12_deploy": proof["p1_1_pass"],
    }

    baseline_path = BASELINES / "continuity_p0_2026-05-22.json"
    baseline: dict = {}
    if baseline_path.is_file():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["step_1_1_p3_component_scheduling"] = proof
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(proof, indent=2, default=str))
    print(f"wrote {baseline_path}", file=sys.stderr)
    return 0 if proof["p1_1_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
