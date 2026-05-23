#!/usr/bin/env python3
"""Wave S3 — rebuild one retrieval epoch with execution-shaped mix for a target island.

Default island: Fizzer primary execution island ``d7e41b3c763d38e9``.

  cd backend
  python scripts/retrieval_island_semantic_backfill.py --tenant <uuid>
  python scripts/retrieval_island_semantic_backfill.py --tenant <uuid> --apply
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import uuid
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

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
)
from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    select_largest_eligible_island_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    derive_substrate_pipeline_replay_identity_v1,
    get_published_index_epoch_v1,
)
from vector.domains.cortex.retrieval.retrieval_publish_contract import (
    begin_pipeline_retrieval_index_build_v1,
    finalize_pipeline_retrieval_index_build_v1,
)
from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import (
    snapshot_retrieval_index_mix_v1,
    validate_retrieval_semantic_mix_v1,
)
from vector.domains.cortex.retrieval.retrieval_semantic_orchestration_v1 import (
    run_wave_s3_retrieval_materialization_pass_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import DEFAULT_TENANT_ID
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1

TENANT_DEFAULT = str(DEFAULT_TENANT_ID)


def _db_url() -> str:
    if os.environ.get("DATABASE_URL", "").strip():
        return os.environ["DATABASE_URL"].strip()
    host = os.environ["DB_PROD_HOST"]
    port = os.environ.get("DB_PROD_PORT", "5432")
    user = os.environ["DB_PROD_USER"]
    password = os.environ["DB_PROD_PASSWORD"]
    dbname = os.environ.get("DB_PROD_DATABASE", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _resolve_island(
    session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str,
) -> tuple[frozenset[uuid.UUID], dict]:
    from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
        list_eligible_traversal_components_v1,
        stable_component_scope_id_v1,
    )
    from vector.infrastructure.db.models.cortex_execution_island_registry import (
        CortexExecutionIslandRegistry,
    )

    row = session.scalar(
        select(CortexExecutionIslandRegistry).where(
            CortexExecutionIslandRegistry.tenant_id == tenant_id,
            CortexExecutionIslandRegistry.island_scope_id == island_scope_id,
        ).limit(1)
    )
    if row is not None and row.entity_ids:
        ids = frozenset(uuid.UUID(str(x)) for x in row.entity_ids if x)
        return ids, {"source": "registry", "entity_count": len(ids)}
    for comp in list_eligible_traversal_components_v1(session, tenant_id=tenant_id, min_entities=2):
        if stable_component_scope_id_v1(comp) == island_scope_id:
            return comp, {"source": "eligible_component", "entity_count": len(comp)}
    island, meta = select_largest_eligible_island_v1(session, tenant_id=tenant_id)
    return island, {"source": "largest_fallback", **meta}


def main() -> int:
    parser = argparse.ArgumentParser(description="Island-scoped retrieval semantic backfill (S3.3)")
    parser.add_argument("--tenant", "--tenant-id", dest="tenant", default=os.environ.get("PROOF_TENANT_ID", TENANT_DEFAULT))
    parser.add_argument(
        "--island-scope-id",
        default=os.environ.get("CORTEX_ISLAND_SCOPE_ID", FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1),
    )
    parser.add_argument("--pipeline-run", default="", help="Optional pipeline run id (else latest running)")
    parser.add_argument("--apply", action="store_true", help="Commit BUILDING epoch and publish")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--database-url", default="")
    args = parser.parse_args()

    tenant_id = uuid.UUID(args.tenant)
    db_url = args.database_url.strip() or _db_url()
    SessionLocal = sessionmaker(bind=create_engine(db_url))

    with SessionLocal() as session:
        prid: uuid.UUID | None = None
        if args.pipeline_run.strip():
            prid = uuid.UUID(args.pipeline_run.strip())
        else:
            run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
            if run is not None:
                prid = run.id
        if prid is None:
            prid = uuid.uuid4()

        island, island_meta = _resolve_island(
            session,
            tenant_id=tenant_id,
            island_scope_id=args.island_scope_id.strip(),
        )
        prior_epoch = get_published_index_epoch_v1(session, tenant_id=tenant_id)
        replay = derive_substrate_pipeline_replay_identity_v1(
            tenant_id=tenant_id,
            pipeline_run_id=prid,
        )
        _, epoch_name = begin_pipeline_retrieval_index_build_v1(session, tenant_id=tenant_id)
        omission = {
            "island_scope_id": args.island_scope_id.strip(),
            "retrieval_scope_law": "island_semantic_backfill_v1",
            "outside_island_scope_entity_count": 0,
        }
        pass_stats = run_wave_s3_retrieval_materialization_pass_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            index_epoch=epoch_name,
            replay_identity=replay,
            island=island,
            omission_summary=omission,
        )
        mix = snapshot_retrieval_index_mix_v1(session, tenant_id=tenant_id, index_epoch=epoch_name)
        ok, violations = validate_retrieval_semantic_mix_v1(mix)
        receipt: dict = {
            "tenant_id": str(tenant_id),
            "island_scope_id": args.island_scope_id.strip(),
            "island_meta": island_meta,
            "pipeline_run_id": str(prid),
            "prior_published_epoch": prior_epoch,
            "new_index_epoch": epoch_name,
            "materialization_pass": pass_stats,
            "mix_preview": mix,
            "mix_ok": ok,
            "mix_violations": violations,
            "apply": bool(args.apply),
        }
        if args.apply:
            finalized = finalize_pipeline_retrieval_index_build_v1(
                session,
                tenant_id=tenant_id,
                index_epoch=epoch_name,
                pipeline_run_id=prid,
            )
            receipt["finalize"] = finalized
            session.commit()
        else:
            session.rollback()

    payload = json.dumps(receipt, indent=2, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n")
        print(f"wrote {args.out}")
    print(payload)
    return 0 if receipt.get("mix_ok") or not args.apply else 1


if __name__ == "__main__":
    raise SystemExit(main())
