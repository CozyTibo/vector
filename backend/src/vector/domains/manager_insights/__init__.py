"""Manager insights domain: fetch through gaps (Steps 1–5) and future pipeline stages."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from vector.contracts.manager_insights_activity import ManagerInsightFetchDebugResponse
from vector.domains.manager_insights.build_work_items import build_work_items
from vector.domains.manager_insights.compute_gaps import compute_gaps
from vector.domains.manager_insights.data_reliability import compute_data_reliability
from vector.domains.manager_insights.extract_evidence import extract_evidence
from vector.domains.manager_insights.fetch_activity import run_fetch_activity_bundle
from vector.domains.manager_insights.link_work_items import link_work_items
from vector.settings import Settings


def run_manager_insights_fetch_debug(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_days: int = 30,
    as_of: datetime | None = None,
) -> ManagerInsightFetchDebugResponse:
    """Run Step 1 -> 0.5 -> 2 -> 3 -> 4 -> 5 (same entrypoint used by admin debug API)."""

    bundle = run_fetch_activity_bundle(
        session,
        settings,
        tenant_id=tenant_id,
        window_days=window_days,
        as_of=as_of,
    )
    reliability = compute_data_reliability(bundle)
    work_items = build_work_items(bundle)
    evidence = extract_evidence(work_items)
    links = link_work_items(work_items, evidence=evidence)
    gaps = compute_gaps(work_items, evidence, links)
    return ManagerInsightFetchDebugResponse(
        fetch=bundle,
        data_reliability=reliability,
        work_items=work_items,
        evidence=evidence,
        links=links,
        gaps=gaps,
    )


__all__ = [
    "compute_data_reliability",
    "build_work_items",
    "compute_gaps",
    "extract_evidence",
    "link_work_items",
    "run_fetch_activity_bundle",
    "run_manager_insights_fetch_debug",
]
