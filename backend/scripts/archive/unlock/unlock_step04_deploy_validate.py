#!/usr/bin/env python3
"""Step 4 — prod deploy validation: deferral release + A4 canonical motion (Fizzer)."""

from __future__ import annotations

import json
import os
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

# Local wedge scripts must not require container secret paths from prod .env.
for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys_path = Path(__file__).resolve().parents[1] / "src"
import sys

sys.path.insert(0, str(sys_path))

from vector.domains.cortex.canonical.forward_progress.candidate_selection import (  # noqa: E402
    untreated_routable_drainable_exists_v1,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import (  # noqa: E402
    count_deferrals,
    release_deferrals_when_missing_parent_ref_materialized_v1,
    release_deferrals_with_materialized_parents,
)
from vector.domains.cortex.canonical.forward_progress.drain_runtime import (  # noqa: E402
    drain_forward_progress_backlog,
)
from vector.domains.cortex.canonical.transform_runtime import (  # noqa: E402
    resolve_default_bundle_id_for_stub_transform,
)
from vector.domains.cortex.unlock.step04_deploy_validation import (  # noqa: E402
    evaluate_a4_canonical_motion_v1,
)
TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
BATCH_LIMIT = max(1, min(int(os.environ.get("UNLOCK_STEP04_BATCH_LIMIT", "100")), 500))
TID = uuid.UUID(TENANT)
DEPLOY_SHA = os.environ.get("UNLOCK_DEPLOY_GIT_SHA", "").strip() or None


def _db_url() -> str:
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _lease_row(tenant_id: uuid.UUID) -> dict | None:
    with psycopg.connect(
        host=os.environ["DB_PROD_HOST"],
        port=int(os.environ.get("DB_PROD_PORT", "5432")),
        user=os.environ["DB_PROD_USER"],
        password=os.environ["DB_PROD_PASSWORD"],
        dbname=os.environ.get("DB_PROD_DATABASE", "postgres"),
        connect_timeout=30,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT fsm_state, phase_cursor,
                          detail_json->>'last_canonical_outcome' AS last_canonical_outcome
                   FROM cortex_tenant_convergence_leases WHERE tenant_id = %s""",
                (str(tenant_id),),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "fsm_state": row[0],
        "phase_cursor": row[1],
        "last_canonical_outcome": row[2],
    }


def main() -> dict:
    from types import SimpleNamespace

    engine = create_engine(_db_url())
    cfg = SimpleNamespace(
        cortex_canonical_forward_progress_max_batches_per_slice=int(
            os.environ.get("CORTEX_CANONICAL_FORWARD_PROGRESS_MAX_BATCHES_PER_SLICE", "3")
        ),
        cortex_canonical_topology_wait_cooldown_seconds=int(
            os.environ.get("CORTEX_CANONICAL_TOPOLOGY_WAIT_COOLDOWN_SECONDS", "30")
        ),
        cortex_post_ingestion_canonical_batch_limit=int(
            os.environ.get("CORTEX_POST_INGESTION_CANONICAL_BATCH_LIMIT", "200")
        ),
        cortex_canonical_permanent_orphan_deferral_threshold=int(
            os.environ.get("CORTEX_CANONICAL_PERMANENT_ORPHAN_DEFERRAL_THRESHOLD", "100")
        ),
        cortex_canonical_pass_cooldown_max_seconds=int(
            os.environ.get("CORTEX_CANONICAL_PASS_COOLDOWN_MAX_SECONDS", "120")
        ),
    )
    out: dict = {
        "tenant_id": TENANT,
        "deploy_git_sha": DEPLOY_SHA,
        "validated_at": datetime.now(UTC).isoformat(),
        "step": 4,
    }
    with Session(engine) as db:
        bundle_id = resolve_default_bundle_id_for_stub_transform(db, TID)
        if not bundle_id:
            out["error"] = "no_transformable_bundle"
            return out
        out["bundle_id"] = bundle_id
        out["deferrals_before"] = count_deferrals(db, tenant_id=TID, bundle_id=bundle_id)
        out["drainable_before"] = untreated_routable_drainable_exists_v1(
            db, tenant_id=TID, bundle_id=bundle_id
        )

        released_missing = release_deferrals_when_missing_parent_ref_materialized_v1(
            db, tenant_id=TID, bundle_id=bundle_id
        )
        released_parents = release_deferrals_with_materialized_parents(
            db, tenant_id=TID, bundle_id=bundle_id
        )
        db.commit()
        out["released_missing_parent_ref"] = released_missing
        out["released_materialized_parents"] = released_parents
        out["deferrals_after_release"] = count_deferrals(db, tenant_id=TID, bundle_id=bundle_id)
        out["drainable_after_release"] = untreated_routable_drainable_exists_v1(
            db, tenant_id=TID, bundle_id=bundle_id
        )

        skip_drain = os.environ.get("UNLOCK_STEP04_SKIP_DRAIN", "").lower() in ("1", "true", "yes")
        max_attempts = max(1, min(int(os.environ.get("UNLOCK_STEP04_DRAIN_ATTEMPTS", "2")), 20))
        lim = min(BATCH_LIMIT, int(cfg.cortex_post_ingestion_canonical_batch_limit))
        drain_attempts: list[dict] = []
        drain_summary: dict = {}
        if skip_drain:
            drain_summary = {"total_succeeded": 0, "canonical_outcome": "skipped_wedge_only"}
        for attempt in range(0 if skip_drain else max_attempts):
            release_deferrals_when_missing_parent_ref_materialized_v1(
                db, tenant_id=TID, bundle_id=bundle_id
            )
            release_deferrals_with_materialized_parents(db, tenant_id=TID, bundle_id=bundle_id)
            drain_summary = drain_forward_progress_backlog(
                db,
                tenant_id=TID,
                bundle_id=bundle_id,
                batch_limit=lim,
                settings=cfg,
            )
            db.commit()
            drain_attempts.append(
                {
                    "attempt": attempt + 1,
                    "total_succeeded": drain_summary.get("total_succeeded"),
                    "canonical_outcome": drain_summary.get("canonical_outcome"),
                }
            )
            if int(drain_summary.get("total_succeeded") or 0) > 0:
                break
            if not untreated_routable_drainable_exists_v1(db, tenant_id=TID, bundle_id=bundle_id):
                break

        out["drain_attempts"] = drain_attempts
        out["drain_summary"] = {
            "total_succeeded": drain_summary.get("total_succeeded"),
            "canonical_outcome": drain_summary.get("canonical_outcome"),
            "convergence_health": drain_summary.get("convergence_health"),
            "deferral_counts": drain_summary.get("deferral_counts"),
            "untreated_routable_estimate": drain_summary.get("untreated_routable_estimate"),
            "progress_made": drain_summary.get("progress_made"),
        }

    lease = _lease_row(TID)
    out["lease_after"] = lease
    a4_ok, a4_detail = evaluate_a4_canonical_motion_v1(
        drain_summary=out.get("drain_summary") if isinstance(out.get("drain_summary"), dict) else None,
        lease_last_canonical_outcome=(
            str(lease.get("last_canonical_outcome")) if isinstance(lease, dict) else None
        ),
        released_missing_parent_ref=int(out.get("released_missing_parent_ref") or 0),
        deferrals_before_total=int((out.get("deferrals_before") or {}).get("deferred_total") or 0),
        deferrals_after_total=int((out.get("deferrals_after_release") or {}).get("deferred_total") or 0),
    )
    out["A4_pass"] = a4_ok
    out["A4_detail"] = a4_detail
    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step04_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("A4_pass"):
        raise SystemExit(1)
