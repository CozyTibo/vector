"""Phase 08.5 P085-12 — orphan classification + continuity stitching (**G-P085-ORPHAN-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-graph-density-doctrine.md`` §Orphan law.
"""

from __future__ import annotations

import inspect
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.org_ambiguity import list_org_ambiguity_records
from vector.domains.cortex.operational_runtime.graph_density import (
    GP085_GRAPH01_GATE_ID_V1,
    count_active_org_entities_v1,
    count_entities_with_promoted_edges_v1,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    count_unpromoted_link_candidates_v1,
    schedule_graph_density_pass_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_GRAPH_DISCONNECTED_V1,
    RET_SKIP_IDENTITY_UNRESOLVED_V1,
)
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

PHASE085_ORPHAN_CONTINUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_ORPHAN_CONTINUITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-graph-density-doctrine.md"
)

GP085_ORPHAN01_GATE_ID_V1: Final[str] = "G-P085-ORPHAN-01"

ORPHAN_CLASS_AWAITING_PROMOTION_V1: Final[str] = "orphan_awaiting_promotion"
ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1: Final[str] = "orphan_identity_unresolved"
ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1: Final[str] = "orphan_disconnected_component"
ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1: Final[str] = "orphan_intentionally_excluded"

ORPHAN_CLASS_IDS_V1: Final[tuple[str, ...]] = (
    ORPHAN_CLASS_AWAITING_PROMOTION_V1,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1,
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
    ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1,
)

ORPHAN_ACTION_ENQUEUE_PROMOTION_V1: Final[str] = "enqueue_candidate_promotion"
ORPHAN_ACTION_BLOCK_IDENTITY_CONSOLE_V1: Final[str] = "block_surface_identity_console"
ORPHAN_ACTION_TRAVERSAL_RET_SKIP_V1: Final[str] = "traversal_blocked_ret_skip"
ORPHAN_ACTION_DOCUMENT_OMISSION_V1: Final[str] = "document_in_omission"

ORPHAN_CLASS_ACTIONS_V1: Final[dict[str, str]] = {
    ORPHAN_CLASS_AWAITING_PROMOTION_V1: ORPHAN_ACTION_ENQUEUE_PROMOTION_V1,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1: ORPHAN_ACTION_BLOCK_IDENTITY_CONSOLE_V1,
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1: ORPHAN_ACTION_TRAVERSAL_RET_SKIP_V1,
    ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1: ORPHAN_ACTION_DOCUMENT_OMISSION_V1,
}

ORPHAN_CLASS_RET_SKIP_V1: Final[dict[str, str | None]] = {
    ORPHAN_CLASS_AWAITING_PROMOTION_V1: None,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1: RET_SKIP_IDENTITY_UNRESOLVED_V1,
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1: RET_SKIP_GRAPH_DISCONNECTED_V1,
    ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1: None,
}

CELERY_ORPHAN_CONTINUITY_STITCH_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.orphan_continuity_stitch_pass"
)

STITCH_TRIGGER_MANUAL_V1: Final[str] = "manual"
STITCH_TRIGGER_AFTER_PROMOTION_V1: Final[str] = "after_promotion_pass"
STITCH_TRIGGER_SCHEDULED_V1: Final[str] = "scheduled"

_METADATA_EXCLUSION_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "cesp_orphan_class",
        "orphan_intentionally_excluded",
        "intentionally_excluded",
    }
)


class GraphOrphanContinuityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


@dataclass
class _OrphanStitchingContextV1:
    tenant_id: uuid.UUID
    entity_count: int
    linked_entity_count: int
    orphan_entity_ids: frozenset[uuid.UUID]
    awaiting_promotion_entity_ids: frozenset[uuid.UUID]
    identity_unresolved_entity_ids: frozenset[uuid.UUID]
    intentionally_excluded_entity_ids: frozenset[uuid.UUID]
    anchor_seed_entity_ids: frozenset[uuid.UUID]
    main_component_entity_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)


def get_orphan_stitching_sample_limit_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_orphan_stitching_sample_limit))
    except Exception:  # noqa: BLE001
        return 100


def get_orphan_stitching_run_anchor_regen_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_orphan_stitching_run_anchor_regen)
    except Exception:  # noqa: BLE001
        return True


def get_orphan_stitching_auto_schedule_promotion_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_orphan_stitching_auto_schedule_promotion)
    except Exception:  # noqa: BLE001
        return True


def _entity_intentionally_excluded_v1(meta: dict[str, Any]) -> bool:
    if str(meta.get("cesp_orphan_class") or "").strip() == ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1:
        return True
    if meta.get("orphan_intentionally_excluded") is True:
        return True
    if meta.get("intentionally_excluded") is True:
        return True
    omission = meta.get("omission")
    if isinstance(omission, dict) and omission.get("intentionally_excluded") is True:
        return True
    return False


def _entity_has_anchor_continuity_seed_v1(meta: dict[str, Any]) -> bool:
    if meta.get("anchor_backfill_lane"):
        return True
    if meta.get("continuity_seed_strategy"):
        return True
    if meta.get("source_anchor_ref"):
        return True
    if meta.get("source_anchor_type"):
        return True
    return False


def _load_entities_in_open_ambiguity_v1(session: Session, *, tenant_id: uuid.UUID) -> frozenset[uuid.UUID]:
    out: set[uuid.UUID] = set()
    for row in list_org_ambiguity_records(session, tenant_id=tenant_id, status="open", limit=5_000):
        raw = row.involved_org_entity_ids
        if not isinstance(raw, list):
            continue
        for item in raw:
            try:
                out.add(item if isinstance(item, uuid.UUID) else uuid.UUID(str(item)))
            except ValueError:
                continue
    return frozenset(out)


def _load_entities_touching_unpromoted_candidates_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> frozenset[uuid.UUID]:
    from vector.domains.cortex.operational_runtime.graph_density_promotion import (
        list_unpromoted_link_candidates_v1,
    )

    cap = max(500, get_orphan_stitching_sample_limit_v1() * 10)
    out: set[uuid.UUID] = set()
    for cand in list_unpromoted_link_candidates_v1(session, tenant_id=tenant_id, limit=cap):
        out.add(cand.source_entity_id)
        out.add(cand.target_entity_id)
    return frozenset(out)


def _load_orphan_entity_ids_v1(session: Session, *, tenant_id: uuid.UUID) -> frozenset[uuid.UUID]:
    linked_subq = (
        select(CortexOrgLink.source_entity_id.label("eid"))
        .where(
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.revoked_at.is_(None),
        )
        .union_all(
            select(CortexOrgLink.target_entity_id.label("eid")).where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.revoked_at.is_(None),
            )
        )
    ).subquery()
    rows = session.scalars(
        select(CortexOrgEntity.id).where(
            CortexOrgEntity.tenant_id == tenant_id,
            CortexOrgEntity.tombstoned_at.is_(None),
            CortexOrgEntity.lifecycle_state == "active",
            CortexOrgEntity.id.not_in(select(linked_subq.c.eid)),
        )
    ).all()
    return frozenset(rows)


def _build_linked_components_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[frozenset[uuid.UUID]]:
    """Union-find over active org links (endpoint columns only — no ORM row hydration)."""
    tid = str(tenant_id)
    rows = session.execute(
        text(
            """
            SELECT source_entity_id, target_entity_id
            FROM cortex_org_links
            WHERE tenant_id = :tenant AND revoked_at IS NULL
            """
        ),
        {"tenant": tid},
    ).all()
    parent: dict[uuid.UUID, uuid.UUID] = {}

    def find(x: uuid.UUID) -> uuid.UUID:
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: uuid.UUID, b: uuid.UUID) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for source_id, target_id in rows:
        union(source_id, target_id)

    buckets: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for node in parent:
        buckets[find(node)].add(node)
    return [frozenset(s) for s in buckets.values() if s]


def list_graph_connected_components_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[frozenset[uuid.UUID]]:
    """Connected components over authoritative org links (**G-P085-WALK-01** frontier ranking)."""
    return _build_linked_components_v1(session, tenant_id=tenant_id)


def build_orphan_stitching_context_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> _OrphanStitchingContextV1:
    entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    linked_entity_count = count_entities_with_promoted_edges_v1(session, tenant_id=tenant_id)
    orphan_ids = _load_orphan_entity_ids_v1(session, tenant_id=tenant_id)

    intentionally: set[uuid.UUID] = set()
    anchor_seed: set[uuid.UUID] = set()
    if orphan_ids:
        for ent in session.scalars(
            select(CortexOrgEntity).where(CortexOrgEntity.id.in_(orphan_ids))
        ).all():
            meta = dict(ent.metadata_json or {})
            if _entity_intentionally_excluded_v1(meta):
                intentionally.add(ent.id)
            if _entity_has_anchor_continuity_seed_v1(meta):
                anchor_seed.add(ent.id)

    components = _build_linked_components_v1(session, tenant_id=tenant_id)
    main: frozenset[uuid.UUID] = frozenset()
    if components:
        main = max(components, key=len)

    return _OrphanStitchingContextV1(
        tenant_id=tenant_id,
        entity_count=entity_count,
        linked_entity_count=linked_entity_count,
        orphan_entity_ids=orphan_ids,
        awaiting_promotion_entity_ids=_load_entities_touching_unpromoted_candidates_v1(
            session,
            tenant_id=tenant_id,
        ),
        identity_unresolved_entity_ids=_load_entities_in_open_ambiguity_v1(session, tenant_id=tenant_id),
        intentionally_excluded_entity_ids=frozenset(intentionally),
        anchor_seed_entity_ids=frozenset(anchor_seed),
        main_component_entity_ids=main,
    )


def classify_orphan_entity_v1(
    ctx: _OrphanStitchingContextV1,
    entity_id: uuid.UUID,
) -> str:
    """Deterministic orphan class for one unlinked org entity."""
    if entity_id not in ctx.orphan_entity_ids:
        msg = "entity_not_orphan"
        raise GraphOrphanContinuityError(msg)

    if entity_id in ctx.intentionally_excluded_entity_ids:
        return ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1
    if entity_id in ctx.identity_unresolved_entity_ids:
        return ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1
    if entity_id in ctx.awaiting_promotion_entity_ids:
        return ORPHAN_CLASS_AWAITING_PROMOTION_V1
    if ctx.linked_entity_count > 0:
        return ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1
    if entity_id in ctx.anchor_seed_entity_ids:
        return ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1
    return ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1


def classify_tenant_graph_orphans_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sample_limit: int | None = None,
) -> dict[str, Any]:
    """Tenant orphan inventory with doctrine class counts and recommended actions."""
    ctx = build_orphan_stitching_context_v1(session, tenant_id=tenant_id)
    lim = sample_limit if sample_limit is not None else get_orphan_stitching_sample_limit_v1()
    counts: dict[str, int] = {c: 0 for c in ORPHAN_CLASS_IDS_V1}
    samples: list[dict[str, Any]] = []

    for eid in sorted(ctx.orphan_entity_ids, key=str):
        cls = classify_orphan_entity_v1(ctx, eid)
        counts[cls] = counts.get(cls, 0) + 1
        if len(samples) < lim:
            samples.append(
                {
                    "org_entity_id": str(eid),
                    "orphan_class": cls,
                    "recommended_action": ORPHAN_CLASS_ACTIONS_V1[cls],
                    "ret_skip_code": ORPHAN_CLASS_RET_SKIP_V1[cls],
                }
            )

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_ORPHAN01_GATE_ID_V1,
        "related_gate_id": GP085_GRAPH01_GATE_ID_V1,
        "entity_count": ctx.entity_count,
        "linked_entity_count": ctx.linked_entity_count,
        "orphan_entity_count": len(ctx.orphan_entity_ids),
        "unpromoted_link_candidate_count": count_unpromoted_link_candidates_v1(
            session,
            tenant_id=tenant_id,
        ),
        "counts_by_class": counts,
        "samples": samples,
        "main_component_size": len(ctx.main_component_entity_ids),
    }


def document_intentionally_excluded_orphans_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_ids: frozenset[uuid.UUID] | None = None,
) -> int:
    """Persist omission documentation on intentionally excluded orphan handles."""
    ctx = build_orphan_stitching_context_v1(session, tenant_id=tenant_id)
    targets = entity_ids if entity_ids is not None else ctx.intentionally_excluded_entity_ids
    documented = 0
    for eid in targets:
        ent = session.get(CortexOrgEntity, eid)
        if ent is None or ent.tenant_id != tenant_id:
            continue
        meta = dict(ent.metadata_json or {})
        if not _entity_intentionally_excluded_v1(meta):
            continue
        omission = dict(meta.get("omission") or {}) if isinstance(meta.get("omission"), dict) else {}
        if omission.get("documented_by_cesp") is True:
            continue
        omission["documented_by_cesp"] = True
        omission["orphan_class"] = ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1
        meta["omission"] = omission
        meta["cesp_orphan_class"] = ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1
        ent.metadata_json = meta
        documented += 1
    if documented:
        session.flush()
    return documented


def run_continuity_stitching_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str = STITCH_TRIGGER_MANUAL_V1,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Classify orphans, stitch anchor continuity candidates, enqueue promotion when lawful."""
    classification = classify_tenant_graph_orphans_v1(session, tenant_id=tenant_id)
    counts = dict(classification["counts_by_class"])
    awaiting = int(counts.get(ORPHAN_CLASS_AWAITING_PROMOTION_V1, 0))
    disconnected = int(counts.get(ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1, 0))
    identity_blocked = int(counts.get(ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1, 0))
    excluded = int(counts.get(ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1, 0))

    anchor_regen_summary: dict[str, Any] | None = None
    promotion_schedule: dict[str, Any] | None = None
    documented = 0

    ctx = build_orphan_stitching_context_v1(session, tenant_id=tenant_id)
    stitch_anchor = (
        get_orphan_stitching_run_anchor_regen_v1()
        and disconnected > 0
        and len(ctx.anchor_seed_entity_ids & ctx.orphan_entity_ids) > 0
    )

    if not dry_run:
        if stitch_anchor:
            from vector.domains.cortex.identity.anchor_continuity_candidates import (
                run_anchor_continuity_candidate_regeneration,
            )

            anchor_regen_summary = run_anchor_continuity_candidate_regeneration(
                session,
                tenant_id=tenant_id,
            )
        if awaiting > 0 and get_orphan_stitching_auto_schedule_promotion_v1():
            promotion_schedule = schedule_graph_density_pass_v1(
                tenant_id=tenant_id,
                trigger=STITCH_TRIGGER_AFTER_PROMOTION_V1,
                force=True,
            )
        if excluded > 0:
            documented = document_intentionally_excluded_orphans_v1(session, tenant_id=tenant_id)

    ret_skip_hints = []
    if disconnected > 0:
        ret_skip_hints.append(
            {
                "ret_skip_code": RET_SKIP_GRAPH_DISCONNECTED_V1,
                "orphan_class": ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
                "count": disconnected,
            }
        )
    if identity_blocked > 0:
        ret_skip_hints.append(
            {
                "ret_skip_code": RET_SKIP_IDENTITY_UNRESOLVED_V1,
                "orphan_class": ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1,
                "count": identity_blocked,
            }
        )

    return {
        "gate_id": GP085_ORPHAN01_GATE_ID_V1,
        "trigger": trigger,
        "dry_run": dry_run,
        "classification": classification,
        "actions_taken": {
            "anchor_continuity_regeneration": anchor_regen_summary is not None,
            "promotion_scheduled": bool(promotion_schedule and promotion_schedule.get("scheduled")),
            "intentionally_excluded_documented": documented,
        },
        "anchor_continuity_regeneration": anchor_regen_summary,
        "promotion_schedule": promotion_schedule,
        "ret_skip_hints": ret_skip_hints,
    }


def build_graph_orphan_continuity_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_orphan_continuity_runtime_schema_version": int(
            PHASE085_ORPHAN_CONTINUITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_ORPHAN_CONTINUITY_SPEC_REF_V1,
        "primary_gate_id": GP085_ORPHAN01_GATE_ID_V1,
        "orphan_class_ids": list(ORPHAN_CLASS_IDS_V1),
        "orphan_class_actions": dict(ORPHAN_CLASS_ACTIONS_V1),
        "orphan_class_ret_skip_codes": {
            k: v for k, v in ORPHAN_CLASS_RET_SKIP_V1.items() if v is not None
        },
        "celery_task_name": CELERY_ORPHAN_CONTINUITY_STITCH_TASK_NAME_V1,
        "sample_limit": get_orphan_stitching_sample_limit_v1(),
        "run_anchor_regen_on_stitch": get_orphan_stitching_run_anchor_regen_v1(),
        "auto_schedule_promotion": get_orphan_stitching_auto_schedule_promotion_v1(),
        "runtime_package": "vector.domains.cortex.operational_runtime.graph_orphan_continuity",
        "stitch_entrypoint": "run_continuity_stitching_pass_v1",
    }


def verify_gp085_orphan01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_graph_orphan_continuity_catalog_v1()
    if set(cat["orphan_class_ids"]) != set(ORPHAN_CLASS_IDS_V1):
        errors.append("orphan_class_ids_mismatch")
    if cat["orphan_class_actions"][ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1] != ORPHAN_ACTION_TRAVERSAL_RET_SKIP_V1:
        errors.append("disconnected_action_mismatch")

    src = inspect.getsource(classify_orphan_entity_v1)
    if "random" in src.lower():
        errors.append("probabilistic_orphan_classification_forbidden")

    from vector.domains.cortex.operational_runtime import graph_completeness_propagation as gprop

    gprop_src = inspect.getsource(gprop.propagate_graph_completeness_stage_v1)
    if "classify_tenant_graph_orphans_v1" not in gprop_src:
        errors.append("graph_propagation_missing_orphan_classification")

    from vector.domains.cortex.retrieval import retrieval_skip_registry as rsr

    if RET_SKIP_GRAPH_DISCONNECTED_V1 not in rsr.RET_SKIP_CODES_V1:
        errors.append("ret_skip_graph_disconnected_missing")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_orphan_continuity_stitch") is not None:
        errors.append("celery_orphan_stitch_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_ORPHAN01_GATE_ID_V1,
        "name": "cesp_graph_orphan_continuity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
