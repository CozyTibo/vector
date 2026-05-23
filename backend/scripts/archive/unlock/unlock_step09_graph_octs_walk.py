#!/usr/bin/env python3
"""Step 9 — prod GRAPH/traversal wedge for OCTS execution continuity (Fizzer A5)."""

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

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import restart_execution_from_phase_v1  # noqa: E402
from vector.domains.cortex.identity.projection_export import (  # noqa: E402
    build_org_graph_projection_export_document,
    build_org_graph_projection_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_05_TRAVERSAL  # noqa: E402
from vector.domains.cortex.substrate_pipeline.substrate_traversal_execution import (  # noqa: E402
    run_substrate_traversal_materialization_v1,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import (  # noqa: E402
    resolve_octs_walk_store_v1,
)
from vector.domains.cortex.unlock.step09_octs_walk import (  # noqa: E402
    authoritative_hops_on_walk_payload_v1,
    evaluate_a5_octs_execution_continuity_v1,
    pick_start_node_ids_on_authoritative_edges_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink  # noqa: E402
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (  # noqa: E402
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)
MAX_STARTS = max(1, min(int(os.environ.get("UNLOCK_STEP09_MAX_STARTS", "8")), 32))
RUN_RESTART = os.environ.get("UNLOCK_STEP09_RUN_RESTART", "1").lower() not in ("0", "false", "no")
SKIP_MATERIALIZE = os.environ.get("UNLOCK_STEP09_SKIP_MATERIALIZE", "").lower() in ("1", "true", "yes")


def _db_url() -> str:
    return (
        f"postgresql+psycopg://{os.environ['DB_PROD_USER']}:{os.environ['DB_PROD_PASSWORD']}"
        f"@{os.environ['DB_PROD_HOST']}:{os.environ.get('DB_PROD_PORT', '5432')}"
        f"/{os.environ.get('DB_PROD_DATABASE', 'postgres')}"
    )


def _count_authoritative_links(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.revoked_at.is_(None),
            )
        )
        or 0
    )


def _summarize_walks(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    projection_edges: list[dict],
) -> dict:
    store = resolve_octs_walk_store_v1(db)
    records = store.list_walk_records_for_tenant_v1(tenant_id)
    completed = [r for r in records if r.status == "completed" and r.walk_payload]
    with_hop = 0
    samples: list[dict] = []
    for rec in completed:
        hops = authoritative_hops_on_walk_payload_v1(
            dict(rec.walk_payload or {}),
            projection_edges=projection_edges,
        )
        if hops >= 1:
            with_hop += 1
        if len(samples) < 5:
            telem = (rec.walk_payload or {}).get("telemetry") or {}
            hb = ((rec.walk_payload or {}).get("walk_result") or {}).get("hash_body") or {}
            samples.append(
                {
                    "walk_id": str(rec.walk_id),
                    "authoritative_hops": hops,
                    "hops_emitted": telem.get("hops_emitted"),
                    "path_fingerprints": len(hb.get("path_edge_fingerprints_ordered") or []),
                }
            )
    return {
        "walk_records_total": len(records),
        "completed_walks": len(completed),
        "walks_with_authoritative_hop": with_hop,
        "walk_samples": samples,
    }


def _recent_phase05_runs(db: Session, tenant_id: uuid.UUID, *, limit: int = 3) -> list[dict]:
    rows = db.execute(
        select(
            CortexSubstratePhaseRun.phase_id,
            CortexSubstratePhaseRun.status,
            CortexSubstratePhaseRun.output_json,
            CortexSubstratePhaseRun.started_at,
        )
        .join(
            CortexSubstratePipelineRun,
            CortexSubstratePipelineRun.id == CortexSubstratePhaseRun.pipeline_run_id,
        )
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePhaseRun.phase_id == PHASE_05_TRAVERSAL,
        )
        .order_by(CortexSubstratePhaseRun.started_at.desc())
        .limit(limit)
    ).all()
    out: list[dict] = []
    for phase_id, status, output_json, started_at in rows:
        oj = output_json if isinstance(output_json, dict) else {}
        out.append(
            {
                "phase_id": str(phase_id),
                "status": str(status),
                "walks_persisted": oj.get("walks_persisted"),
                "primary_octs_walk_id": oj.get("primary_octs_walk_id"),
                "started_at": started_at.isoformat() if started_at else None,
            }
        )
    return out


def main() -> dict:
    import sys
    from pathlib import Path as _PathGuard

    from vector.domains.cortex.substrate_pipeline.continuity_cleanup_freeze import (
        WedgeScriptBannedDuringHoldError,
        assert_wedge_script_allowed_v1,
    )

    try:
        assert_wedge_script_allowed_v1(__file__, repo_root=_PathGuard(__file__).resolve().parents[2])
    except WedgeScriptBannedDuringHoldError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    engine = create_engine(_db_url())
    out: dict = {
        "tenant_id": TENANT,
        "step": 9,
        "validated_at": datetime.now(UTC).isoformat(),
        "max_starts": MAX_STARTS,
    }
    with Session(engine) as db:
        out["authoritative_links_active"] = _count_authoritative_links(db, TID)
        inner = build_org_graph_projection_v1(db, tenant_id=TID)
        projection_edges = list(inner.get("edges") or [])
        out["projection"] = {
            "node_count": len(inner.get("nodes") or []),
            "edge_count": len(projection_edges),
            "authoritative_edge_count": sum(
                1 for e in projection_edges if str(e.get("link_authority") or "") == "authoritative"
            ),
        }
        out["walks_before"] = _summarize_walks(db, TID, projection_edges=projection_edges)

        if RUN_RESTART:
            try:
                restart_out = restart_execution_from_phase_v1(
                    db,
                    tenant_id=TID,
                    from_phase="GRAPH",
                    force=True,
                )
                db.commit()
                out["execution_restart"] = restart_out
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                out["execution_restart"] = {"restarted": False, "error": str(exc)}

        if not SKIP_MATERIALIZE:
            export_doc = build_org_graph_projection_export_document(db, tenant_id=TID)
            stable = str(export_doc.get("stable_hash_sha256") or "")
            inner_proj = export_doc.get("projection")
            start_ids: list[str] = []
            if isinstance(inner_proj, dict):
                start_ids = pick_start_node_ids_on_authoritative_edges_v1(
                    inner_proj,
                    limit=MAX_STARTS,
                )
            out["selected_start_node_ids"] = start_ids
            mat = run_substrate_traversal_materialization_v1(
                db,
                tenant_id=TID,
                graph_projection_stable_hash=stable or None,
                max_starts=MAX_STARTS,
                start_node_ids=start_ids or None,
            )
            db.commit()
            out["traversal_materialization"] = mat
        else:
            out["traversal_materialization"] = {"skipped": True}

        out["walks_after"] = _summarize_walks(db, TID, projection_edges=projection_edges)
        out["phase_05_recent"] = _recent_phase05_runs(db, TID)

        walks_after = out["walks_after"]
        mat = out.get("traversal_materialization") if isinstance(out.get("traversal_materialization"), dict) else {}
        persisted = mat.get("walks_persisted") if isinstance(mat, dict) else None
        a5_ok, a5_detail = evaluate_a5_octs_execution_continuity_v1(
            completed_walks=int(walks_after.get("completed_walks") or 0),
            walks_with_authoritative_hop=int(walks_after.get("walks_with_authoritative_hop") or 0),
            walks_persisted=int(persisted) if persisted is not None else None,
        )
        out["A5_pass"] = a5_ok
        out["A5_detail"] = a5_detail

    if int(out.get("authoritative_links_active") or 0) < 1:
        out["A5_pass"] = False
        out["A5_detail"] = "authoritative_links_active=0 (prerequisite for A5)"
    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = _Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step09_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("A5_pass"):
        raise SystemExit(1)
