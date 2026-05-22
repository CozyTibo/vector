#!/usr/bin/env python3
"""Step 11 — §9.1 alive criteria panel capture (Track A T0 + 48h hold clock)."""

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

from vector.domains.cortex.identity.projection_export import build_org_graph_projection_v1  # noqa: E402
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1  # noqa: E402
from vector.domains.cortex.retrieval.retrieval_skip_registry import normalize_skip_reasons_from_stats_v1  # noqa: E402
from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1  # noqa: E402
from vector.domains.cortex.unlock.step09_octs_walk import authoritative_hops_on_walk_payload_v1  # noqa: E402
from vector.domains.cortex.unlock.step11_alive_panel import (  # noqa: E402
    TRACK_A_PANEL_HOLD_HOURS_V1,
    build_alive_panel_evaluation_v1,
    merge_retrieval_skip_counts_from_report,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (  # noqa: E402
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord  # noqa: E402
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity  # noqa: E402
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink  # noqa: E402
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate  # noqa: E402
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (  # noqa: E402
    CortexRetrievalMaterializationReport,
)
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (  # noqa: E402
    CortexTenantConvergenceLease,
)

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)
# Step 4 wedge reference for A4 deferral-drop evidence (optional env override).
STEP04_DEFERRALS_BEFORE = int(os.environ.get("UNLOCK_STEP11_STEP04_DEFERRALS_BEFORE", "8181"))
STEP04_RELEASED = int(os.environ.get("UNLOCK_STEP11_STEP04_RELEASED", "7715"))
STEP04_TOTAL_SUCCEEDED = int(os.environ.get("UNLOCK_STEP11_STEP04_TOTAL_SUCCEEDED", "2"))


def _db_url() -> str:
    return (
        f"postgresql+psycopg://{os.environ['DB_PROD_USER']}:{os.environ['DB_PROD_PASSWORD']}"
        f"@{os.environ['DB_PROD_HOST']}:{os.environ.get('DB_PROD_PORT', '5432')}"
        f"/{os.environ.get('DB_PROD_DATABASE', 'postgres')}"
    )


def _lease_snapshot(db: Session, tenant_id: uuid.UUID) -> dict:
    row = db.scalars(
        select(CortexTenantConvergenceLease).where(CortexTenantConvergenceLease.tenant_id == tenant_id)
    ).first()
    if row is None:
        return {}
    detail = dict(row.detail_json or {})
    return {
        "fsm_state": row.fsm_state,
        "phase_cursor": row.phase_cursor,
        "last_canonical_outcome": detail.get("last_canonical_outcome"),
        "convergence_health": detail.get("convergence_health"),
    }


def _summarize_walks(db: Session, tenant_id: uuid.UUID) -> dict:
    inner = build_org_graph_projection_v1(db, tenant_id=tenant_id)
    edges = list(inner.get("edges") or [])
    store = resolve_octs_walk_store_v1(db)
    completed = 0
    with_hop = 0
    for rec in store.list_walk_records_for_tenant_v1(tenant_id):
        if str(rec.status) != "completed" or not rec.walk_payload:
            continue
        completed += 1
        hops = authoritative_hops_on_walk_payload_v1(
            dict(rec.walk_payload or {}),
            projection_edges=edges,
        )
        if hops >= 1:
            with_hop += 1
    return {"completed_walks": completed, "walks_with_authoritative_hop": with_hop}


def _retrieval_panel_metrics(db: Session, tenant_id: uuid.UUID) -> dict:
    row = db.scalars(
        select(CortexRetrievalMaterializationReport)
        .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
        .order_by(CortexRetrievalMaterializationReport.created_at.desc())
        .limit(1)
    ).first()
    if row is None:
        return {
            "entries_materialized": 0,
            "accepted_rows": 0,
            "published_index_epoch": get_published_index_epoch_v1(db, tenant_id=tenant_id),
            "skip_code_counts": {},
        }
    skips = list(row.skip_reasons_json or [])
    return {
        "entries_materialized": int(row.accepted_rows or 0),
        "accepted_rows": int(row.accepted_rows or 0),
        "published_index_epoch": row.retrieval_epoch or get_published_index_epoch_v1(db, tenant_id=tenant_id),
        "report_id": str(row.id),
        "report_created_at": row.created_at.isoformat() if row.created_at else None,
        "skip_code_counts": merge_retrieval_skip_counts_from_report(skips),
        "skip_reasons_normalized": normalize_skip_reasons_from_stats_v1(
            [{"source": s.get("source"), "code": s.get("upstream_code")} for s in skips if isinstance(s, dict)]
        ),
    }


def main() -> dict:
    engine = create_engine(_db_url())
    captured_at = datetime.now(UTC).isoformat()
    out: dict = {
        "tenant_id": TENANT,
        "step": 11,
        "validated_at": captured_at,
        "track_a_panel_hold_hours": TRACK_A_PANEL_HOLD_HOURS_V1,
    }
    with Session(engine) as db:
        org_entities = int(
            db.scalar(
                select(func.count())
                .select_from(CortexOrgEntity)
                .where(
                    CortexOrgEntity.tenant_id == TID,
                    CortexOrgEntity.tombstoned_at.is_(None),
                    CortexOrgEntity.lifecycle_state == "active",
                )
            )
            or 0
        )
        auth_links = int(
            db.scalar(
                select(func.count())
                .select_from(CortexOrgLink)
                .where(
                    CortexOrgLink.tenant_id == TID,
                    CortexOrgLink.link_authority == "authoritative",
                    CortexOrgLink.revoked_at.is_(None),
                )
            )
            or 0
        )
        candidates = int(
            db.scalar(
                select(func.count()).select_from(CortexOrgLinkCandidate).where(
                    CortexOrgLinkCandidate.tenant_id == TID
                )
            )
            or 0
        )
        raw_total = int(
            db.scalar(
                select(func.count())
                .select_from(RawIngestionRecord)
                .where(RawIngestionRecord.tenant_id == TID)
            )
            or 0
        )
        mat_total = int(
            db.scalar(
                select(func.count())
                .select_from(CortexCanonicalTransformMaterialization)
                .where(CortexCanonicalTransformMaterialization.tenant_id == TID)
            )
            or 0
        )

        lease = _lease_snapshot(db, TID)
        walks = _summarize_walks(db, TID)
        retrieval = _retrieval_panel_metrics(db, TID)

        out["metrics"] = {
            "org_entities_active": org_entities,
            "authoritative_links_active": auth_links,
            "link_candidates": candidates,
            "raw_total": raw_total,
            "mat_total": mat_total,
            "raw_minus_mat_admin_gap": raw_total - mat_total,
            "lease": lease,
            "walks": walks,
            "retrieval": retrieval,
            "step04_wedge_reference": {
                "deferrals_before": STEP04_DEFERRALS_BEFORE,
                "deferrals_after": STEP04_DEFERRALS_BEFORE - STEP04_RELEASED,
                "released_missing_parent_ref": STEP04_RELEASED,
                "total_succeeded": STEP04_TOTAL_SUCCEEDED,
            },
        }

        panel = build_alive_panel_evaluation_v1(
            org_entities_active=org_entities,
            authoritative_links_active=auth_links,
            link_candidates=candidates,
            lease_last_canonical_outcome=lease.get("last_canonical_outcome"),
            released_missing_parent_ref=STEP04_RELEASED,
            deferrals_before_total=STEP04_DEFERRALS_BEFORE,
            deferrals_after_total=max(0, STEP04_DEFERRALS_BEFORE - STEP04_RELEASED),
            drain_total_succeeded=STEP04_TOTAL_SUCCEEDED,
            drain_canonical_outcome="partial_progress",
            completed_walks=int(walks["completed_walks"]),
            walks_with_authoritative_hop=int(walks["walks_with_authoritative_hop"]),
            entries_materialized=int(retrieval["entries_materialized"]),
            retrieval_skip_code_counts=dict(retrieval["skip_code_counts"]),
            raw_minus_mat_admin_gap=raw_total - mat_total,
            panel_captured_at=captured_at,
        )
        out["panel"] = panel
        out["step11_pass"] = panel["step11_pass"]
        out["step11_detail"] = panel["step11_detail"]
        out["track_a_signoff_pending"] = panel["track_a_signoff_pending"]

    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = _Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step11_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("step11_pass"):
        raise SystemExit(1)
