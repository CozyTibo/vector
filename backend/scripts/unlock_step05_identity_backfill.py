#!/usr/bin/env python3
"""Step 5 — prod identity backfill from canonical anchors (Fizzer A1)."""

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

from vector.domains.cortex.identity.backfill import run_anchor_handle_backfill  # noqa: E402
from vector.domains.cortex.unlock.step05_identity_backfill import evaluate_a1_org_handles_v1  # noqa: E402
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity  # noqa: E402

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)
ANCHOR_LIMIT = max(100, min(int(os.environ.get("UNLOCK_STEP05_ANCHOR_LIMIT", "20000")), 50_000))
CHUNK_SIZE = max(100, min(int(os.environ.get("UNLOCK_STEP05_CHUNK_SIZE", "2000")), 10_000))
START_OFFSET = max(0, int(os.environ.get("UNLOCK_STEP05_START_OFFSET", "0")))
DRY_RUN = os.environ.get("UNLOCK_STEP05_DRY_RUN", "").lower() in ("1", "true", "yes")


def _db_url() -> str:
    return (
        f"postgresql+psycopg://{os.environ['DB_PROD_USER']}:{os.environ['DB_PROD_PASSWORD']}"
        f"@{os.environ['DB_PROD_HOST']}:{os.environ.get('DB_PROD_PORT', '5432')}"
        f"/{os.environ.get('DB_PROD_DATABASE', 'postgres')}"
    )


def _count_active_entities(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
            )
        )
        or 0
    )


def main() -> dict:
    engine = create_engine(_db_url())
    out: dict = {
        "tenant_id": TENANT,
        "step": 5,
        "validated_at": datetime.now(UTC).isoformat(),
        "anchor_limit": ANCHOR_LIMIT,
        "dry_run": DRY_RUN,
    }
    with Session(engine) as db:
        out["org_entities_active_before"] = _count_active_entities(db, TID)
        chunks: list[dict] = []
        total_upserted = 0
        total_scanned = 0
        offset = START_OFFSET
        while offset < ANCHOR_LIMIT:
            lim = min(CHUNK_SIZE, ANCHOR_LIMIT - offset)
            backfill = run_anchor_handle_backfill(
                db,
                tenant_id=TID,
                dry_run=DRY_RUN,
                anchor_limit=lim,
                anchor_offset=offset,
                skip_candidate_regen=True,
            )
            if not DRY_RUN:
                db.commit()
                db.expire_all()
            scanned = int(backfill.get("anchors_scanned") or 0)
            upserted = int(backfill.get("entities_upserted") or 0)
            total_scanned += scanned
            total_upserted += upserted
            chunks.append(
                {
                    "offset": offset,
                    "anchors_scanned": scanned,
                    "entities_upserted": upserted,
                    "run_id": backfill.get("run_id"),
                }
            )
            offset += lim
            if scanned < lim:
                break
        out["chunks"] = chunks
        out["backfill"] = {
            "anchors_scanned": total_scanned,
            "entities_upserted": total_upserted,
            "chunk_count": len(chunks),
        }
        out["org_entities_active_after"] = _count_active_entities(db, TID)
        out["entity_by_kind"] = [
            {"entity_kind": str(kind), "n": int(n or 0)}
            for kind, n in db.execute(
                select(CortexOrgEntity.entity_kind, func.count())
                .where(
                    CortexOrgEntity.tenant_id == TID,
                    CortexOrgEntity.tombstoned_at.is_(None),
                )
                .group_by(CortexOrgEntity.entity_kind)
                .order_by(func.count().desc())
                .limit(20)
            ).all()
        ]

    a1_ok, a1_detail = evaluate_a1_org_handles_v1(
        org_entities_active=int(out["org_entities_active_after"]),
        entities_upserted=int((out.get("backfill") or {}).get("entities_upserted") or 0),
        anchors_scanned=int((out.get("backfill") or {}).get("anchors_scanned") or 0),
    )
    out["A1_pass"] = a1_ok
    out["A1_detail"] = a1_detail
    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = _Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step05_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("A1_pass"):
        raise SystemExit(1)
