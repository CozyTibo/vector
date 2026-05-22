#!/usr/bin/env python3
"""Step 6 — prod candidate regeneration from anchors (Fizzer A3)."""

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

from vector.domains.cortex.identity.anchor_continuity_candidates import (  # noqa: E402
    run_anchor_continuity_candidate_regeneration,
)
from vector.domains.cortex.unlock.step06_candidate_regen import evaluate_a3_candidate_links_v1  # noqa: E402
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate  # noqa: E402

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)


def _db_url() -> str:
    return (
        f"postgresql+psycopg://{os.environ['DB_PROD_USER']}:{os.environ['DB_PROD_PASSWORD']}"
        f"@{os.environ['DB_PROD_HOST']}:{os.environ.get('DB_PROD_PORT', '5432')}"
        f"/{os.environ.get('DB_PROD_DATABASE', 'postgres')}"
    )


def _count_candidates(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate)
            .where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        )
        or 0
    )


def main() -> dict:
    engine = create_engine(_db_url())
    out: dict = {
        "tenant_id": TENANT,
        "step": 6,
        "validated_at": datetime.now(UTC).isoformat(),
    }
    with Session(engine) as db:
        out["link_candidates_before"] = _count_candidates(db, TID)
        regen = run_anchor_continuity_candidate_regeneration(db, tenant_id=TID)
        db.commit()
        out["regen"] = dict(regen)
        overflow = regen.get("candidate_generation_overflow_accounting")
        if isinstance(overflow, dict):
            out["overflow_accounting"] = overflow
        out["link_candidates_after"] = _count_candidates(db, TID)
        out["link_types"] = [
            {"link_type": str(lt), "n": int(n or 0)}
            for lt, n in db.execute(
                select(CortexOrgLinkCandidate.link_type, func.count())
                .where(CortexOrgLinkCandidate.tenant_id == TID)
                .group_by(CortexOrgLinkCandidate.link_type)
                .order_by(func.count().desc())
                .limit(15)
            ).all()
        ]

    persisted = None
    if isinstance(regen, dict):
        persisted = regen.get("candidates_persisted") or regen.get("candidate_count")
    a3_ok, a3_detail = evaluate_a3_candidate_links_v1(
        candidate_count=int(out["link_candidates_after"]),
        candidates_persisted=int(persisted) if persisted is not None else None,
    )
    out["A3_pass"] = a3_ok
    out["A3_detail"] = a3_detail
    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = _Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step06_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("A3_pass"):
        raise SystemExit(1)
