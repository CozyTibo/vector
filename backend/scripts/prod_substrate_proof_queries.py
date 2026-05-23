#!/usr/bin/env python3
"""Prod substrate baseline snapshot (unlock plan step 1) — JSON stdout or --out file."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

# repo root .env
_env = Path(__file__).resolve().parents[2] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

import psycopg

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vector.domains.cortex.canonical.transform_runtime import stub_routing_pairs  # noqa: E402
from vector.domains.cortex.unlock.baseline_snapshot import (  # noqa: E402
    extract_alive_baseline_metrics,
    validate_baseline_snapshot,
)


def conn():
    return psycopg.connect(
        host=os.environ["DB_PROD_HOST"],
        port=int(os.environ.get("DB_PROD_PORT", "5432")),
        user=os.environ["DB_PROD_USER"],
        password=os.environ["DB_PROD_PASSWORD"],
        dbname=os.environ.get("DB_PROD_DATABASE", "postgres"),
        connect_timeout=30,
    )


def q(cur, sql: str, params: tuple = ()) -> list:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def main(*, allow_deprecated: bool = False) -> dict[str, Any]:
    import sys

    from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
        CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1,
        deprecation_message_for_script_v1,
        warn_deprecated_continuity_proof_script_v1,
    )

    warn_deprecated_continuity_proof_script_v1(__file__)
    if not allow_deprecated:
        print(
            deprecation_message_for_script_v1(__file__)
            + f" Prefer backend/scripts/{CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1} and "
            "backend/scripts/graph_truth_audit_snapshot.py. "
            "Pass --allow-deprecated to run this script anyway.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    pairs = stub_routing_pairs()
    pair_count = len(pairs)
    # build temp table via VALUES for routable check
    pair_values = ",".join(
        f"('{p[0].replace(chr(39), chr(39)+chr(39))}','{p[1].replace(chr(39), chr(39)+chr(39))}')"
        for p in pairs[:500]
    )
    out: dict = {"tenant_id": TENANT, "routable_pair_count": pair_count}

    with conn() as c:
        cur = c.cursor()

        out["tenant"] = q(
            cur,
            "SELECT id, company_name, slug, status FROM tenants WHERE id = %s",
            (str(TID),),
        )

        out["lease"] = q(
            cur,
            """SELECT status, fsm_state, phase_cursor, obligation_epoch, target_epoch,
                      block_reason_code, detail_json->>'last_canonical_outcome' AS last_canonical_outcome,
                      detail_json->>'convergence_health' AS convergence_health
               FROM cortex_tenant_convergence_leases WHERE tenant_id = %s""",
            (str(TID),),
        )

        out["raw_total"] = q(
            cur,
            "SELECT COUNT(*)::bigint AS n FROM raw_ingestion_records WHERE tenant_id = %s",
            (str(TID),),
        )[0]["n"]

        out["mat_total"] = q(
            cur,
            "SELECT COUNT(*)::bigint AS n FROM cortex_canonical_transform_materializations WHERE tenant_id = %s",
            (str(TID),),
        )[0]["n"]

        out["raw_minus_mat_admin_gap"] = int(out["raw_total"]) - int(out["mat_total"])

        # default bundle
        out["bundles"] = q(
            cur,
            """SELECT bundle_id, COUNT(*)::bigint AS mat_count
               FROM cortex_canonical_transform_materializations
               WHERE tenant_id = %s GROUP BY 1 ORDER BY mat_count DESC LIMIT 5""",
            (str(TID),),
        )
        bundle_id = out["bundles"][0]["bundle_id"] if out["bundles"] else None
        out["primary_bundle_id"] = bundle_id

        if bundle_id:
            # routable untreated (mirror candidate_selection)
            cur.execute(
                f"""
                WITH routable(connector, resource_type) AS (
                  VALUES {",".join("(%s,%s)" for _ in pairs)}
                )
                SELECT COUNT(*)::bigint AS n
                FROM raw_ingestion_records r
                INNER JOIN routable rt ON r.connector = rt.connector AND r.resource_type = rt.resource_type
                LEFT JOIN cortex_canonical_transform_materializations m
                  ON m.raw_record_id = r.id AND m.tenant_id = r.tenant_id AND m.bundle_id = %s
                WHERE r.tenant_id = %s AND m.id IS NULL
                """,
                [x for p in pairs for x in p] + [bundle_id, str(TID)],
            )
            out["untreated_routable_estimate"] = cur.fetchone()[0]

            # any raw without mat (gate)
            out["untreated_raw_any_bundle"] = q(
                cur,
                """SELECT COUNT(*)::bigint AS n FROM raw_ingestion_records r
                   WHERE r.tenant_id = %s AND NOT EXISTS (
                     SELECT 1 FROM cortex_canonical_transform_materializations m
                     WHERE m.tenant_id = r.tenant_id AND m.raw_record_id = r.id
                   )""",
                (str(TID),),
            )[0]["n"]

            out["deferral_totals"] = q(
                cur,
                """SELECT
                     COUNT(*)::bigint AS total,
                     COUNT(*) FILTER (WHERE COALESCE(detail_json->>'permanent_orphan','') = 'true')::bigint AS permanent_orphan,
                     COUNT(*) FILTER (WHERE retry_ready_at > NOW())::bigint AS on_cooldown,
                     COUNT(*) FILTER (WHERE retry_ready_at <= NOW()
                       AND COALESCE(detail_json->>'permanent_orphan','') != 'true')::bigint AS retry_ready
                   FROM cortex_canonical_materialization_deferrals
                   WHERE tenant_id = %s AND bundle_id = %s""",
                (str(TID), bundle_id),
            )

            out["deferral_top"] = q(
                cur,
                """SELECT resource_type, deferral_reason, queue, COUNT(*)::bigint AS n
                   FROM cortex_canonical_materialization_deferrals
                   WHERE tenant_id = %s AND bundle_id = %s
                   GROUP BY 1,2,3 ORDER BY n DESC LIMIT 25""",
                (str(TID), bundle_id),
            )

            out["topology_parent_gaps"] = q(
                cur,
                """SELECT missing_parent_ref, resource_type, COUNT(*)::bigint AS n
                   FROM cortex_canonical_materialization_deferrals
                   WHERE tenant_id = %s AND bundle_id = %s
                     AND missing_parent_ref IS NOT NULL AND missing_parent_ref != ''
                   GROUP BY 1,2 ORDER BY n DESC LIMIT 20""",
                (str(TID), bundle_id),
            )

            out["failure_cases"] = q(
                cur,
                """SELECT failure_class, COUNT(*)::bigint AS n
                   FROM cortex_canonical_failure_cases
                   WHERE tenant_id = %s AND active = true
                   GROUP BY 1 ORDER BY n DESC""",
                (str(TID),),
            )

        out["anchors"] = q(
            cur,
            "SELECT COUNT(*)::bigint AS n FROM cortex_canonical_identity_anchors WHERE tenant_id = %s",
            (str(TID),),
        )[0]["n"]

        out["anchors_by_kind"] = q(
            cur,
            """SELECT canonical_object_kind, COUNT(*)::bigint AS n
               FROM cortex_canonical_identity_anchors WHERE tenant_id = %s
               GROUP BY 1 ORDER BY n DESC LIMIT 20""",
            (str(TID),),
        )

        out["org_entities_active"] = q(
            cur,
            """SELECT COUNT(*)::bigint AS n FROM cortex_org_entities
               WHERE tenant_id = %s AND tombstoned_at IS NULL AND lifecycle_state = 'active'""",
            (str(TID),),
        )[0]["n"]

        out["auth_links"] = q(
            cur,
            """SELECT COUNT(*)::bigint AS n FROM cortex_org_links
               WHERE tenant_id = %s AND link_authority = 'authoritative'""",
            (str(TID),),
        )[0]["n"]

        out["candidates"] = q(
            cur,
            "SELECT COUNT(*)::bigint AS n FROM cortex_org_link_candidates WHERE tenant_id = %s",
            (str(TID),),
        )[0]["n"]

        # raw by resource_type top
        out["raw_by_type"] = q(
            cur,
            """SELECT resource_type, COUNT(*)::bigint AS n
               FROM raw_ingestion_records WHERE tenant_id = %s
               GROUP BY 1 ORDER BY n DESC LIMIT 40""",
            (str(TID),),
        )

        # routable vs not per raw row
        if bundle_id and pairs:
            cur.execute(
                f"""
                WITH routable(connector, resource_type) AS (
                  VALUES {",".join("(%s,%s)" for _ in pairs)}
                )
                SELECT
                  COUNT(*)::bigint AS raw_total,
                  COUNT(*) FILTER (WHERE rt.connector IS NOT NULL)::bigint AS routable_raw,
                  COUNT(*) FILTER (WHERE rt.connector IS NULL)::bigint AS non_routable_raw,
                  COUNT(*) FILTER (WHERE rt.connector IS NOT NULL AND m.id IS NOT NULL)::bigint AS routable_mat,
                  COUNT(*) FILTER (WHERE rt.connector IS NOT NULL AND m.id IS NULL)::bigint AS routable_unmat
                FROM raw_ingestion_records r
                LEFT JOIN routable rt ON r.connector = rt.connector AND r.resource_type = rt.resource_type
                LEFT JOIN cortex_canonical_transform_materializations m
                  ON m.raw_record_id = r.id AND m.tenant_id = r.tenant_id AND m.bundle_id = %s
                WHERE r.tenant_id = %s
                """,
                [x for p in pairs for x in p] + [bundle_id, str(TID)],
            )
            cols = [d[0] for d in cur.description]
            out["routable_breakdown"] = dict(zip(cols, cur.fetchone()))

        # slack message actor
        out["slack_message_actor"] = q(
            cur,
            """SELECT
                 COUNT(*)::bigint AS total,
                 COUNT(*) FILTER (
                   WHERE payload_body->'message'->>'user' LIKE 'U%%'
                      OR payload_body->>'user' LIKE 'U%%'
                      OR payload_body->>'user_id' LIKE 'U%%'
                 )::bigint AS has_u_actor
               FROM raw_ingestion_records
               WHERE tenant_id = %s AND resource_type = 'slack.message'""",
            (str(TID),),
        )

        out["github_pr_users"] = q(
            cur,
            """SELECT
                 COUNT(*)::bigint AS total,
                 COUNT(*) FILTER (WHERE payload_body->'pull_request'->'user'->>'login' IS NOT NULL
                                    AND payload_body->'pull_request'->'user'->>'login' != '')::bigint AS has_user_login
               FROM raw_ingestion_records
               WHERE tenant_id = %s AND resource_type = 'github.pull_request'""",
            (str(TID),),
        )

        out["notion_page_users"] = q(
            cur,
            """SELECT
                 COUNT(*)::bigint AS total,
                 COUNT(*) FILTER (WHERE
                   payload_body->'page'->'created_by' IS NOT NULL
                   OR payload_body->'page'->'last_edited_by' IS NOT NULL
                 )::bigint AS has_user_ref
               FROM raw_ingestion_records
               WHERE tenant_id = %s AND resource_type = 'notion.page'""",
            (str(TID),),
        )

        # mat without anchor (should be ~0)
        out["mat_without_anchor"] = q(
            cur,
            """SELECT COUNT(*)::bigint AS n
               FROM cortex_canonical_transform_materializations m
               WHERE m.tenant_id = %s AND NOT EXISTS (
                 SELECT 1 FROM cortex_canonical_identity_anchors a
                 WHERE a.tenant_id = m.tenant_id AND a.raw_record_id = m.raw_record_id
               )""",
            (str(TID),),
        )[0]["n"]

        # sample IDs for trace
        out["phase_runs"] = q(
            cur,
            """SELECT pr.phase_id, pr.status, pr.error_detail, pr.output_json, pr.started_at, pr.completed_at
               FROM cortex_substrate_phase_runs pr
               JOIN cortex_substrate_pipeline_runs r ON r.id = pr.pipeline_run_id
               WHERE r.tenant_id = %s
               ORDER BY pr.started_at DESC NULLS LAST LIMIT 15""",
            (str(TID),),
        )

        out["primitives"] = q(
            cur,
            "SELECT COUNT(*)::bigint AS n FROM cortex_org_primitive_instances WHERE tenant_id = %s",
            (str(TID),),
        )[0]["n"]

        out["entity_by_kind"] = q(
            cur,
            """SELECT entity_kind, COUNT(*)::bigint AS n
               FROM cortex_org_entities WHERE tenant_id = %s AND tombstoned_at IS NULL
               GROUP BY 1 ORDER BY n DESC""",
            (str(TID),),
        )

        out["samples"] = {
            "slack_message": q(
                cur,
                """SELECT id, external_id, (payload_body->'message'->>'user') AS msg_user
                   FROM raw_ingestion_records WHERE tenant_id=%s AND resource_type='slack.message'
                   ORDER BY id DESC LIMIT 3""",
                (str(TID),),
            ),
            "github_pr": q(
                cur,
                """SELECT id, external_id,
                          (payload_body->'pull_request'->'user'->>'login') AS user_login
                   FROM raw_ingestion_records WHERE tenant_id=%s AND resource_type='github.pull_request'
                   ORDER BY id DESC LIMIT 3""",
                (str(TID),),
            ),
        }

    out["alive_baseline"] = extract_alive_baseline_metrics(out)
    validate_baseline_snapshot(out)

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from vector.domains.cortex.substrate_pipeline.continuity_substrate_sql_snapshot import (
            build_substrate_sql_snapshot_v1,
        )

        db_url = (
            f"postgresql+psycopg://{os.environ['DB_PROD_USER']}:{os.environ['DB_PROD_PASSWORD']}"
            f"@{os.environ['DB_PROD_HOST']}:{os.environ.get('DB_PROD_PORT', '5432')}"
            f"/{os.environ.get('DB_PROD_DATABASE', 'postgres')}"
        )
        SessionLocal = sessionmaker(bind=create_engine(db_url))
        with SessionLocal() as session:
            out["substrate_sql_core_v1"] = build_substrate_sql_snapshot_v1(
                session, tenant_id=TID
            )
        out["canonical_audit_entrypoint"] = "backend/scripts/continuity_audit_snapshot.py"
    except Exception as exc:  # noqa: BLE001
        out["substrate_sql_core_v1_error"] = str(exc)[:500]

    return out


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prod substrate baseline (unlock step 1)")
    parser.add_argument(
        "--out",
        type=Path,
        help="Write JSON snapshot to path (validated before write)",
    )
    parser.add_argument(
        "--allow-deprecated",
        action="store_true",
        help="Wave S5: allow running deprecated script (operators should use continuity/graph truth snapshots)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    payload = main(allow_deprecated=bool(args.allow_deprecated))
    text = json.dumps(payload, indent=2, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text)
