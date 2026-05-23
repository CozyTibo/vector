"""Phase B step B2 — island scope alignment when retrieval index epoch changes (R-REC-1 extension)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    P1_C_ISLAND_SCOPE_KEY_V1,
    _island_omission_summary_v1,
    select_largest_eligible_island_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch

RETRIEVAL_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION: Final[int] = 1
P0_B2_STEP: Final[str] = "step_b2_retrieval_epoch_scope_alignment"
FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1: Final[str] = "d7e41b3c763d38e9"


def is_retrieval_epoch_scope_realign_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_retrieval_epoch_scope_realign_enabled)
    except Exception:  # noqa: BLE001
        return True


def count_retrieval_entries_in_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str,
) -> int:
    """Count rows on ``published_index_epoch`` tagged with ``island_scope_id``."""
    epoch = published_index_epoch.strip()
    scope = island_scope_id.strip()
    if not epoch or not scope:
        return 0
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry.omission_summary).where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == epoch,
            )
        ).all()
    )
    return sum(
        1
        for summary in rows
        if isinstance(summary, dict)
        and str(summary.get(P1_C_ISLAND_SCOPE_KEY_V1) or "") == scope
    )


def find_prior_published_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    exclude_epoch: str | None = None,
) -> str | None:
    """Second-most-recent ``PUBLISHED`` epoch name (for tag realign after epoch bump)."""
    exclude = (exclude_epoch or "").strip()
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEpoch.index_epoch)
            .where(
                CortexRetrievalIndexEpoch.tenant_id == tenant_id,
                CortexRetrievalIndexEpoch.build_state == "PUBLISHED",
            )
            .order_by(CortexRetrievalIndexEpoch.published_at.desc().nullslast())
        ).all()
    )
    for name in rows:
        epoch = str(name).strip()
        if epoch and epoch != exclude:
            return epoch
    return None


def resolve_primary_island_scope_id_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> tuple[str, dict[str, Any]]:
    """Largest eligible island scope id (P1-C primary island for synthesis)."""
    _, meta = select_largest_eligible_island_v1(session, tenant_id=tenant_id)
    return str(meta.get("island_scope_id") or ""), meta


def realign_island_scope_tags_from_prior_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    prior_published_epoch: str,
    target_epoch: str,
    island_scope_id: str,
    outside_island_scope_entity_count: int = 0,
) -> dict[str, Any]:
    """Bump ``island_scope_id`` on ``target_epoch`` rows via lookup_id map from prior published epoch."""
    prior = prior_published_epoch.strip()
    target = target_epoch.strip()
    scope = island_scope_id.strip()
    if not prior or not target or not scope or prior == target:
        return {
            "realign_skipped": True,
            "reason": "no_prior_epoch_or_same_epoch",
            "tags_bumped": 0,
        }

    prior_tagged = {
        str(row.retrieval_lookup_id): dict(row.omission_summary or {})
        for row in session.scalars(
            select(CortexRetrievalIndexEntry).where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == prior,
            )
        ).all()
        if str((row.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "") == scope
    }
    if not prior_tagged:
        return {
            "realign_skipped": True,
            "reason": "no_prior_tagged_entries",
            "tags_bumped": 0,
            "prior_published_epoch": prior,
        }

    template = _island_omission_summary_v1(
        island_scope_id=scope,
        outside_island_scope_entity_count=outside_island_scope_entity_count,
    )
    tags_bumped = 0
    for row in session.scalars(
        select(CortexRetrievalIndexEntry).where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.index_epoch == target,
        )
    ).all():
        lookup = str(row.retrieval_lookup_id)
        if lookup not in prior_tagged:
            continue
        current = str((row.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "")
        if current == scope:
            continue
        merged = dict(row.omission_summary or {})
        merged.update(template)
        merged.update(
            {
                k: v
                for k, v in prior_tagged[lookup].items()
                if k in (P1_C_ISLAND_SCOPE_KEY_V1, "retrieval_scope_law", "outside_island_scope_entity_count")
            }
        )
        merged[P1_C_ISLAND_SCOPE_KEY_V1] = scope
        row.omission_summary = merged
        flag_modified(row, "omission_summary")
        tags_bumped += 1
    if tags_bumped:
        session.flush()
    return {
        "realign_skipped": False,
        "prior_published_epoch": prior,
        "target_epoch": target,
        "island_scope_id": scope,
        "prior_tagged_lookup_ids": len(prior_tagged),
        "tags_bumped": tags_bumped,
    }


def reconcile_primary_island_scope_on_epoch_change_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    prior_published_epoch: str | None,
    new_published_epoch: str | None,
    island_scope_id: str,
    outside_island_scope_entity_count: int = 0,
    force_realign: bool = False,
) -> dict[str, Any]:
    """After publish: ensure primary island has in-scope rows on the new published epoch."""
    scope = island_scope_id.strip()
    new_epoch = (new_published_epoch or "").strip()
    prior = (prior_published_epoch or "").strip() or None
    out: dict[str, Any] = {
        "epoch_scope_alignment_schema_version": RETRIEVAL_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION,
        "island_scope_id": scope,
        "prior_published_index_epoch": prior,
        "new_published_index_epoch": new_epoch,
        "epoch_changed": bool(prior and new_epoch and prior != new_epoch),
    }
    if not scope or not new_epoch:
        out["reconcile_skipped"] = True
        out["reason"] = "missing_scope_or_epoch"
        out["retrieval_entries_in_scope"] = 0
        return out

    in_scope_before = 0
    if prior:
        in_scope_before = count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=prior,
            island_scope_id=scope,
        )
    in_scope_after = count_retrieval_entries_in_scope_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=new_epoch,
        island_scope_id=scope,
    )
    out["retrieval_entries_in_scope_before"] = in_scope_before
    out["retrieval_entries_in_scope"] = in_scope_after

    if not is_retrieval_epoch_scope_realign_enabled_v1():
        out["realign"] = {"realign_skipped": True, "reason": "feature_disabled"}
        return out

    needs_realign = force_realign or (
        out["epoch_changed"] and in_scope_after == 0 and in_scope_before > 0
    )
    if in_scope_after == 0 and prior and (needs_realign or in_scope_before > 0):
        realign = realign_island_scope_tags_from_prior_epoch_v1(
            session,
            tenant_id=tenant_id,
            prior_published_epoch=prior,
            target_epoch=new_epoch,
            island_scope_id=scope,
            outside_island_scope_entity_count=outside_island_scope_entity_count,
        )
        out["realign"] = realign
        in_scope_after = count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=new_epoch,
            island_scope_id=scope,
        )
        out["retrieval_entries_in_scope"] = in_scope_after
    else:
        out["realign"] = {
            "realign_skipped": True,
            "reason": "in_scope_satisfied",
            "tags_bumped": 0,
        }
    out["primary_island_in_scope_ok"] = in_scope_after > 0
    return out


def snapshot_retrieval_epoch_scope_alignment_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str | None = None,
) -> dict[str, Any]:
    """Prod snapshot for B2 proof — in-scope counts on published epoch."""
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    scope, meta = (
        (island_scope_id, {})
        if island_scope_id
        else resolve_primary_island_scope_id_v1(session, tenant_id=tenant_id)
    )
    in_scope = (
        count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=published,
            island_scope_id=scope,
        )
        if published and scope
        else 0
    )
    tagged_any = 0
    if published:
        summaries = list(
            session.scalars(
                select(CortexRetrievalIndexEntry.omission_summary).where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.index_epoch == published,
                )
            ).all()
        )
        tagged_any = sum(
            1
            for summary in summaries
            if isinstance(summary, dict) and bool(summary.get(P1_C_ISLAND_SCOPE_KEY_V1))
        )
    return {
        "tenant_id": str(tenant_id),
        "published_index_epoch": published,
        "primary_island_scope_id": scope,
        "island_meta": meta,
        "retrieval_entries_in_scope": in_scope,
        "tagged_entries_on_published_epoch": tagged_any,
        "fizzer_primary_island_scope_id": FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
        "fizzer_primary_in_scope": (
            count_retrieval_entries_in_scope_v1(
                session,
                tenant_id=tenant_id,
                published_index_epoch=published or "",
                island_scope_id=FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
            )
            if published
            else 0
        ),
        "epoch_scope_alignment_schema_version": RETRIEVAL_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION,
    }


def drive_primary_island_scope_realign_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Operator/proof drive: bump island tags on current published epoch from prior published epoch."""
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    scope = (island_scope_id or "").strip() or resolve_primary_island_scope_id_v1(
        session, tenant_id=tenant_id
    )[0]
    prior = find_prior_published_epoch_v1(
        session, tenant_id=tenant_id, exclude_epoch=published
    )
    if not published or not scope or not prior:
        return {
            "driven": False,
            "reason": "missing_published_prior_or_scope",
            "published_index_epoch": published,
            "prior_published_epoch": prior,
            "island_scope_id": scope,
        }
    if dry_run:
        return {
            "driven": False,
            "dry_run": True,
            "published_index_epoch": published,
            "prior_published_epoch": prior,
            "island_scope_id": scope,
        }
    realign = realign_island_scope_tags_from_prior_epoch_v1(
        session,
        tenant_id=tenant_id,
        prior_published_epoch=prior,
        target_epoch=published,
        island_scope_id=scope,
    )
    in_scope = count_retrieval_entries_in_scope_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published,
        island_scope_id=scope,
    )
    return {
        "driven": True,
        "published_index_epoch": published,
        "prior_published_epoch": prior,
        "island_scope_id": scope,
        "realign": realign,
        "retrieval_entries_in_scope": in_scope,
    }
