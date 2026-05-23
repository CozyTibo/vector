#!/usr/bin/env python3
"""Step 7 — prod graph density promotion pass (Fizzer A2)."""

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

from vector.domains.cortex.operational_runtime.graph_density_promotion import (  # noqa: E402
    PROMOTION_TRIGGER_MANUAL_V1,
    count_unpromoted_link_candidates_v1,
    schedule_graph_density_pass_v1,
)
from vector.domains.cortex.unlock.step07_graph_density_promotion import (  # noqa: E402
    evaluate_a2_authoritative_links_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink  # noqa: E402

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)
FORCE = os.environ.get("UNLOCK_STEP07_FORCE", "1").lower() not in ("0", "false", "no")
TRIGGER = os.environ.get("UNLOCK_STEP07_TRIGGER", PROMOTION_TRIGGER_MANUAL_V1)


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


def main() -> dict:
    engine = create_engine(_db_url())
    out: dict = {
        "tenant_id": TENANT,
        "step": 7,
        "validated_at": datetime.now(UTC).isoformat(),
        "force": FORCE,
        "trigger": TRIGGER,
    }
    with Session(engine) as db:
        out["authoritative_links_before"] = _count_authoritative_links(db, TID)
        out["unpromoted_candidates_before"] = count_unpromoted_link_candidates_v1(db, tenant_id=TID)
        schedule_out = schedule_graph_density_pass_v1(
            tenant_id=TID,
            trigger=TRIGGER,
            force=FORCE,
            session=db,
        )
        db.commit()
        out["schedule"] = schedule_out
        pass_out = schedule_out.get("pass") if isinstance(schedule_out, dict) else None
        if isinstance(pass_out, dict):
            out["promotion_pass"] = pass_out
        out["authoritative_links_after"] = _count_authoritative_links(db, TID)
        out["unpromoted_candidates_after"] = count_unpromoted_link_candidates_v1(db, tenant_id=TID)
        out["link_types"] = [
            {"link_type": str(lt), "n": int(n or 0)}
            for lt, n in db.execute(
                select(CortexOrgLink.link_type, func.count())
                .where(
                    CortexOrgLink.tenant_id == TID,
                    CortexOrgLink.link_authority == "authoritative",
                    CortexOrgLink.revoked_at.is_(None),
                )
                .group_by(CortexOrgLink.link_type)
                .order_by(func.count().desc())
                .limit(15)
            ).all()
        ]

    promoted_count = None
    if isinstance(out.get("promotion_pass"), dict):
        promoted_count = out["promotion_pass"].get("promoted_count")
    a2_ok, a2_detail = evaluate_a2_authoritative_links_v1(
        authoritative_links_active=int(out["authoritative_links_after"]),
        promoted_count=int(promoted_count) if promoted_count is not None else None,
    )
    out["A2_pass"] = a2_ok
    out["A2_detail"] = a2_detail
    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = (
        _Path(__file__).resolve().parents[2]
        / "DOCS/audits/baselines/fizzer_step07_2026-05-22.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("A2_pass"):
        raise SystemExit(1)
