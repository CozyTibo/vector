"""Read-only continuity evidence propagation inspector (raw → canonical → anchor → rules).

No orchestration or replay side effects. Surfaces where identity-bearing fields drop between
raw payloads, canonical materialization snapshots, and the anchor continuity join-key engine.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter, defaultdict
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    _DEFAULT_MANIFEST,
    ANCHOR_CONTINUITY_RULE_SEMANTIC,
    CONTINUITY_JOIN_REASON_BY_RULE,
    RULE_CONTINUITY_FIXTURE_CLUSTER,
    RULE_EMAIL_EXACT,
    RULE_EMAIL_NORM_CONTINUITY_EVIDENCE,
    RULE_FIXTURE_LINK_SUBJECT,
    RULE_FIXTURE_STABLE_ACCOUNT_KEY,
    RULE_GITHUB_LOGIN,
    RULE_LINEAR_USER_ID,
    RULE_NOTION_USER_ID,
    RULE_SLACK_USER_ID,
    _continuity_fixture_dict,
    _display_name,
    _email_for_rule,
    _fixture_link_subject,
    _fixture_stable_account_key,
    _github_login,
    _payload_dict,
    _slack_user_id,
    build_anchor_continuity_candidate_rows,
    continuity_identity_signals_for_anchor,
)
from vector.domains.cortex.identity.anchor_projection import (
    legacy_org_handle_lane_eligible,
    org_entity_id_for_anchor_row,
    provider_login_for_kind_resolution,
)
from vector.domains.cortex.identity.continuity_candidate_evidence_accumulation import (
    accumulate_candidate_pair_evidence,
)
from vector.domains.cortex.identity.entity_kind_mapping import resolve_org_entity_kind_for_anchor
from vector.domains.cortex.identity.identity_primitive_projection import (
    aggregate_github_email_extraction_metrics,
    aggregate_identity_primitive_metrics,
    extract_identity_primitives,
    org_entity_id_for_identity_primitive,
    resolve_org_entity_kind_for_identity_primitive,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import (
    CortexCanonicalIdentityAnchor,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

CONTINUITY_EVIDENCE_INSPECT_SCHEMA_VERSION: Final[int] = 6

_LOGGER = logging.getLogger("vector.cortex.identity.continuity_evidence_inspector")


def _trunc_preview(obj: Any, *, max_chars: int = 6000) -> Any:
    try:
        s = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    except TypeError:
        s = repr(obj)
    if len(s) <= max_chars:
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return s
    return {"_truncated": True, "char_len": len(s), "preview": s[:max_chars]}


def _raw_identity_fields_public(payload: dict[str, Any]) -> dict[str, Any]:
    """Stable subset of raw payload paths continuity + UI care about (no full payload dump)."""
    out: dict[str, Any] = {
        "top_level_user_id": payload.get("user_id") if isinstance(payload.get("user_id"), str) else None,
        "top_level_user_email": payload.get("user_email") if isinstance(payload.get("user_email"), str) else None,
        "top_level_display_name": payload.get("display_name") if isinstance(payload.get("display_name"), str) else None,
        "message.user": None,
        "pull_request.user.login": None,
        "metadata.continuity_fixture": None,
        "message.metadata.continuity_fixture": None,
        "pull_request.metadata.continuity_fixture": None,
    }
    msg = payload.get("message")
    if isinstance(msg, dict):
        out["message.user"] = msg.get("user") if isinstance(msg.get("user"), str) else msg.get("user")
    pr = payload.get("pull_request")
    if isinstance(pr, dict):
        u = pr.get("user")
        if isinstance(u, dict) and isinstance(u.get("login"), str):
            out["pull_request.user.login"] = u.get("login")
    md = payload.get("metadata")
    if isinstance(md, dict) and md.get("continuity_fixture") is not None:
        out["metadata.continuity_fixture"] = _trunc_preview(md.get("continuity_fixture"), max_chars=1200)
    if isinstance(msg, dict):
        mm = msg.get("metadata")
        if isinstance(mm, dict) and mm.get("continuity_fixture") is not None:
            out["message.metadata.continuity_fixture"] = _trunc_preview(mm.get("continuity_fixture"), max_chars=1200)
    if isinstance(pr, dict):
        pmd = pr.get("metadata")
        if isinstance(pmd, dict) and pmd.get("continuity_fixture") is not None:
            out["pull_request.metadata.continuity_fixture"] = _trunc_preview(pmd.get("continuity_fixture"), max_chars=1200)
    return out


def _canonical_public_slice(mat: CortexCanonicalTransformMaterialization | None) -> dict[str, Any]:
    if mat is None:
        return {"materialization_joined": False}
    emitted = dict(mat.emitted_snapshot_json or {})
    lk = dict(mat.logical_key_json or {})
    return {
        "materialization_joined": True,
        "materialization_id": str(mat.id),
        "canonical_object_kind": mat.canonical_object_kind,
        "logical_key_preview": _trunc_preview(lk, max_chars=2500),
        "emitted_snapshot_preview": _trunc_preview(emitted, max_chars=4000),
        "emitted_top_level_keys": sorted(emitted.keys()),
        "continuity_fixture_in_canonical_emitted": _continuity_fixture_dict(emitted) is not None,
    }


def _build_join_buckets(
    *,
    tenant_id: uuid.UUID,
    anchors: list[CortexCanonicalIdentityAnchor],
    raw_by_id: dict[int, RawIngestionRecord],
) -> tuple[
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[tuple[str, str, str], list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
]:
    by_slack: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_github: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_linear: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_notion: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_email_norm: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_email_strict: dict[tuple[str, str, str], list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_fixture: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_link_subject: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_stable_account: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)

    for a in anchors:
        raw = raw_by_id.get(int(a.raw_record_id))
        rid = int(a.raw_record_id)
        prof = dict(a.provider_identity_json or {})
        payload = _payload_dict(raw)
        projections = extract_identity_primitives(anchor=a, raw=raw)

        for proj in projections:
            eid = org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=proj)
            mat = proj.identity_material
            pk = proj.projection_kind

            if pk == "slack_user":
                su = mat.get("slack_user_id")
                if isinstance(su, str) and su.strip():
                    by_slack[su.strip()].append((eid, rid, a))

            if pk == "github_user":
                gl = mat.get("github_login")
                if isinstance(gl, str) and gl.strip():
                    by_github[gl.strip().lower()].append((eid, rid, a))

            if pk == "linear_user":
                lu = mat.get("linear_user_id")
                if isinstance(lu, str) and lu.strip():
                    by_linear[lu.strip()].append((eid, rid, a))

            if pk == "notion_user":
                nid = mat.get("notion_user_id")
                if isinstance(nid, str) and nid.strip():
                    by_notion[nid.strip()].append((eid, rid, a))

            if pk == "email_display_identity":
                em = mat.get("email_norm")
                dom = mat.get("email_domain")
                dn = mat.get("display_name_norm")
                if isinstance(em, str) and isinstance(dom, str) and isinstance(dn, str) and em and dom and dn:
                    by_email_strict[(em, dom, dn)].append((eid, rid, a))

            if pk in ("email_identity", "email_display_identity"):
                emn = mat.get("email_norm")
                if isinstance(emn, str) and emn.strip():
                    by_email_norm[emn.strip().lower()].append((eid, rid, a))

            if pk == "cross_tool_cluster":
                ck = mat.get("cluster_key")
                if isinstance(ck, str) and ck.strip():
                    by_fixture[ck.strip()].append((eid, rid, a))

            if pk == "cross_tool_link_subject":
                ls = mat.get("link_subject")
                if isinstance(ls, str) and ls.strip():
                    by_link_subject[ls.strip()].append((eid, rid, a))

            if pk == "stable_account_identity":
                sk = mat.get("stable_account_key")
                if isinstance(sk, str) and sk.strip():
                    by_stable_account[sk.strip()].append((eid, rid, a))

        if not projections:
            if not legacy_org_handle_lane_eligible(
                canonical_object_kind=a.canonical_object_kind,
                raw=raw,
            ):
                continue
            eid = org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=a, raw=raw)
            su = _slack_user_id(payload, prof)
            if su:
                by_slack[su].append((eid, rid, a))
            gl = _github_login(payload, prof)
            if gl:
                by_github[gl].append((eid, rid, a))
            em, dom = _email_for_rule(payload, prof)
            dn = _display_name(payload)
            if em:
                by_email_norm[em].append((eid, rid, a))
            if em and dom and dn:
                by_email_strict[(em, dom, dn)].append((eid, rid, a))
            fc = _continuity_fixture_dict(payload)
            if fc:
                ck = fc.get("cluster_key")
                if isinstance(ck, str) and ck.strip():
                    by_fixture[ck.strip()].append((eid, rid, a))
            ls = _fixture_link_subject(payload)
            if ls:
                by_link_subject[ls].append((eid, rid, a))
            sak = _fixture_stable_account_key(payload)
            if sak:
                by_stable_account[sak].append((eid, rid, a))

    return (
        by_slack,
        by_github,
        by_linear,
        by_notion,
        by_email_norm,
        by_email_strict,
        by_fixture,
        by_link_subject,
        by_stable_account,
    )


def _eligible_rules_for_anchor(
    *,
    tenant_id: uuid.UUID,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
    by_slack: dict[str, list[Any]],
    by_github: dict[str, list[Any]],
    by_linear: dict[str, list[Any]],
    by_notion: dict[str, list[Any]],
    by_email_norm: dict[str, list[Any]],
    by_email_strict: dict[tuple[str, str, str], list[Any]],
    by_fixture: dict[str, list[Any]],
    by_link_subject: dict[str, list[Any]],
    by_stable_account: dict[str, list[Any]],
) -> tuple[list[str], dict[str, Any]]:
    """Rules where this anchor's extracted primitives sit in a bucket with ≥2 distinct org entities."""
    eligible: list[str] = []
    bucket_sizes: dict[str, Any] = {}
    projections = extract_identity_primitives(anchor=anchor, raw=raw)

    for proj in projections:
        mat = proj.identity_material
        pk = proj.projection_kind

        if pk == "slack_user":
            su = mat.get("slack_user_id")
            if isinstance(su, str) and su.strip():
                lst = by_slack.get(su.strip(), [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_SLACK_USER_ID] = {
                    "key": su.strip(),
                    "anchor_rows_in_bucket": len(lst),
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_SLACK_USER_ID)

        if pk == "github_user":
            gl = mat.get("github_login")
            if isinstance(gl, str) and gl.strip():
                g = gl.strip().lower()
                lst = by_github.get(g, [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_GITHUB_LOGIN] = {
                    "key": g,
                    "anchor_rows_in_bucket": len(lst),
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_GITHUB_LOGIN)

        if pk == "linear_user":
            lu = mat.get("linear_user_id")
            if isinstance(lu, str) and lu.strip():
                k = lu.strip()
                lst = by_linear.get(k, [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_LINEAR_USER_ID] = {
                    "key": k,
                    "anchor_rows_in_bucket": len(lst),
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_LINEAR_USER_ID)

        if pk == "notion_user":
            nid = mat.get("notion_user_id")
            if isinstance(nid, str) and nid.strip():
                k = nid.strip()
                lst = by_notion.get(k, [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_NOTION_USER_ID] = {
                    "key": k,
                    "anchor_rows_in_bucket": len(lst),
                    "distinct_org_entities": len(distinct_eids),
                    "continuity_join_reason": CONTINUITY_JOIN_REASON_BY_RULE[RULE_NOTION_USER_ID],
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_NOTION_USER_ID)

        if pk in ("email_identity", "email_display_identity"):
            emn = mat.get("email_norm")
            if isinstance(emn, str) and emn.strip():
                k = emn.strip().lower()
                lst = by_email_norm.get(k, [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_EMAIL_NORM_CONTINUITY_EVIDENCE] = {
                    "key": k,
                    "anchor_rows_in_bucket": len(lst),
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_EMAIL_NORM_CONTINUITY_EVIDENCE)

        if pk == "email_display_identity":
            em = mat.get("email_norm")
            dom = mat.get("email_domain")
            dn = mat.get("display_name_norm")
            if isinstance(em, str) and isinstance(dom, str) and isinstance(dn, str) and em and dom and dn:
                k = (em, dom, dn)
                lst = by_email_strict.get(k, [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_EMAIL_EXACT] = {
                    "key": {"email": em, "domain": dom, "display": dn},
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_EMAIL_EXACT)

        if pk == "cross_tool_cluster":
            ck = mat.get("cluster_key")
            if isinstance(ck, str) and ck.strip():
                cks = ck.strip()
                lst = by_fixture.get(cks, [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_CONTINUITY_FIXTURE_CLUSTER] = {
                    "key": cks,
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_CONTINUITY_FIXTURE_CLUSTER)

        if pk == "cross_tool_link_subject":
            ls = mat.get("link_subject")
            if isinstance(ls, str) and ls.strip():
                lst = by_link_subject.get(ls.strip(), [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_FIXTURE_LINK_SUBJECT] = {
                    "key": ls.strip(),
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_FIXTURE_LINK_SUBJECT)

        if pk == "stable_account_identity":
            sak = mat.get("stable_account_key")
            if isinstance(sak, str) and sak.strip():
                lst = by_stable_account.get(sak.strip(), [])
                distinct_eids = {t[0] for t in lst}
                bucket_sizes[RULE_FIXTURE_STABLE_ACCOUNT_KEY] = {
                    "key": sak.strip(),
                    "distinct_org_entities": len(distinct_eids),
                }
                if len(distinct_eids) >= 2:
                    eligible.append(RULE_FIXTURE_STABLE_ACCOUNT_KEY)

    return list(dict.fromkeys(eligible)), bucket_sizes


def _missing_identity_flags(
    *,
    raw: RawIngestionRecord | None,
    signals: dict[str, Any],
    canonical_unmapped: bool,
) -> list[str]:
    flags: list[str] = []
    if raw is None:
        flags.append("raw_join_missing")
    if canonical_unmapped:
        flags.append("unsupported_canonical_kind")
    if raw is not None and not signals.get("slack_user_id") and not signals.get("github_login"):
        flags.append("missing_slack_user_id_and_github_login")
    if not signals.get("email_rule_tuple_ready"):
        em = signals.get("email_normalized")
        dn = signals.get("display_name_normalized")
        if not em:
            flags.append("email_normalization_or_absent")
        elif not dn:
            flags.append("display_name_missing_for_email_rule")
    cf = signals.get("continuity_fixture")
    if cf is None:
        flags.append("continuity_fixture_absent_on_raw_payload")
    else:
        if not signals.get("fixture_cluster_key"):
            flags.append("cluster_key_missing_in_fixture")
        if not signals.get("fixture_stable_account_key"):
            flags.append("stable_account_key_missing_in_fixture")
        if not signals.get("fixture_link_subject"):
            flags.append("link_subject_missing_in_fixture")
    return flags


def _primary_skip_reason(
    *,
    raw: RawIngestionRecord | None,
    eligible_rules: list[str],
    canonical_unmapped: bool,
    signals: dict[str, Any],
) -> str:
    if eligible_rules:
        return "continuity_eligible"
    if raw is None:
        return "raw_join_missing"
    if canonical_unmapped:
        return "unsupported_canonical_kind_unknown_org_mapping"
    notion_ids = signals.get("notion_user_ids")
    linear_ids = signals.get("linear_user_ids")
    github_emails = signals.get("github_emails")
    has_any_key = bool(
        signals.get("slack_user_id")
        or signals.get("github_login")
        or (isinstance(github_emails, list) and len(github_emails) > 0)
        or signals.get("email_normalized")
        or signals.get("email_rule_tuple_ready")
        or (isinstance(notion_ids, list) and len(notion_ids) > 0)
        or (isinstance(linear_ids, list) and len(linear_ids) > 0)
        or signals.get("fixture_cluster_key")
        or signals.get("fixture_link_subject")
        or signals.get("fixture_stable_account_key")
    )
    if not has_any_key:
        return "missing_all_continuity_join_keys"
    return "join_keys_present_but_all_buckets_singleton_or_same_org_entity"


def build_continuity_evidence_inspection(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchor_scan_limit: int = 50_000,
    sample_limit: int = 30,
    fixture_survival_sample_limit: int = 40,
) -> dict[str, Any]:
    """Aggregate substrate introspection + sampled rows + hostile dry-run trace (read-only)."""
    lim = max(1, min(int(anchor_scan_limit), 100_000))
    samp = max(1, min(int(sample_limit), 200))
    surv = max(1, min(int(fixture_survival_sample_limit), 500))

    anchors = list(
        db.scalars(
            select(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
            .order_by(CortexCanonicalIdentityAnchor.canonical_entity_id.asc())
            .limit(lim)
        ).all()
    )
    raw_ids = {int(a.raw_record_id) for a in anchors}
    raw_by_id: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        for r in db.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))).all():
            raw_by_id[int(r.id)] = r

    mat_ids = {a.materialization_id for a in anchors if a.materialization_id is not None}
    mat_by_id: dict[uuid.UUID, CortexCanonicalTransformMaterialization] = {}
    if mat_ids:
        for m in db.scalars(
            select(CortexCanonicalTransformMaterialization).where(CortexCanonicalTransformMaterialization.id.in_(mat_ids))
        ).all():
            mat_by_id[m.id] = m

    (
        by_slack,
        by_github,
        by_linear,
        by_notion,
        by_email_norm,
        by_email_strict,
        by_fixture,
        by_link_subject,
        by_stable_account,
    ) = _build_join_buckets(tenant_id=tenant_id, anchors=anchors, raw_by_id=raw_by_id)

    canonical_kind_counts: Counter[str] = Counter()
    org_entity_kind_counts: Counter[str] = Counter()
    primary_skip_counts: Counter[str] = Counter()
    missing_flag_counts: Counter[str] = Counter()

    counters: dict[str, int] = {
        "anchors_scanned": len(anchors),
        "anchors_with_raw_join": 0,
        "anchors_missing_raw_join": 0,
        "anchors_with_slack_user_id": 0,
        "anchors_with_github_login": 0,
        "anchors_with_email_rule_tuple": 0,
        "anchors_with_continuity_fixture_dict": 0,
        "anchors_with_fixture_cluster_key": 0,
        "anchors_with_fixture_stable_account_key": 0,
        "anchors_with_fixture_link_subject": 0,
        "anchors_with_materialization_join": 0,
        "anchors_continuity_rule_eligible": 0,
        "anchors_skipped_missing_raw": 0,
        "anchors_skipped_unknown_canonical_org_kind": 0,
        "anchors_skipped_missing_all_join_keys": 0,
        "anchors_skipped_singleton_buckets": 0,
    }

    sampled_rows: list[dict[str, Any]] = []
    fixture_survival: list[dict[str, Any]] = []

    dry_anchor: CortexCanonicalIdentityAnchor | None = None
    dry_raw: RawIngestionRecord | None = None

    for idx, a in enumerate(anchors):
        raw = raw_by_id.get(int(a.raw_record_id))
        raw_pl = _payload_dict(raw)
        if raw is not None:
            counters["anchors_with_raw_join"] += 1
        else:
            counters["anchors_missing_raw_join"] += 1
            counters["anchors_skipped_missing_raw"] += 1

        if a.materialization_id and a.materialization_id in mat_by_id:
            counters["anchors_with_materialization_join"] += 1

        canonical_kind_counts[a.canonical_object_kind] += 1

        login = provider_login_for_kind_resolution(a, raw)
        org_kind_anchor, mapping_rule_id = resolve_org_entity_kind_for_anchor(
            connector=a.connector,
            canonical_object_kind=a.canonical_object_kind,
            resource_type=raw.resource_type if raw is not None else None,
            provider_login=login,
        )
        anchor_prims = extract_identity_primitives(anchor=a, raw=raw)
        if anchor_prims:
            for p in anchor_prims:
                ok, _ = resolve_org_entity_kind_for_identity_primitive(
                    projection_kind=p.projection_kind,
                    github_login=p.identity_material.get("github_login")
                    if p.projection_kind == "github_user"
                    else None,
                )
                org_entity_kind_counts[ok] += 1
        else:
            org_entity_kind_counts[org_kind_anchor] += 1
        canonical_unmapped = mapping_rule_id == "registry:fallback:unknown_placeholder"
        if canonical_unmapped:
            counters["anchors_skipped_unknown_canonical_org_kind"] += 1

        signals = continuity_identity_signals_for_anchor(anchor=a, raw=raw)
        if signals.get("slack_user_id"):
            counters["anchors_with_slack_user_id"] += 1
        if signals.get("github_login"):
            counters["anchors_with_github_login"] += 1
        if signals.get("email_rule_tuple_ready"):
            counters["anchors_with_email_rule_tuple"] += 1
        if signals.get("continuity_fixture") is not None:
            counters["anchors_with_continuity_fixture_dict"] += 1
        if signals.get("fixture_cluster_key"):
            counters["anchors_with_fixture_cluster_key"] += 1
        if signals.get("fixture_stable_account_key"):
            counters["anchors_with_fixture_stable_account_key"] += 1
        if signals.get("fixture_link_subject"):
            counters["anchors_with_fixture_link_subject"] += 1

        eligible, bucket_sizes = _eligible_rules_for_anchor(
            tenant_id=tenant_id,
            anchor=a,
            raw=raw,
            by_slack=by_slack,
            by_github=by_github,
            by_linear=by_linear,
            by_notion=by_notion,
            by_email_norm=by_email_norm,
            by_email_strict=by_email_strict,
            by_fixture=by_fixture,
            by_link_subject=by_link_subject,
            by_stable_account=by_stable_account,
        )
        if eligible:
            counters["anchors_continuity_rule_eligible"] += 1

        primary = _primary_skip_reason(
            raw=raw, eligible_rules=eligible, canonical_unmapped=canonical_unmapped, signals=signals
        )
        primary_skip_counts[primary] += 1
        if primary == "missing_all_continuity_join_keys":
            counters["anchors_skipped_missing_all_join_keys"] += 1
        elif primary == "join_keys_present_but_all_buckets_singleton_or_same_org_entity":
            counters["anchors_skipped_singleton_buckets"] += 1

        flags = _missing_identity_flags(raw=raw, signals=signals, canonical_unmapped=canonical_unmapped)
        for f in flags:
            missing_flag_counts[f] += 1

        if len(sampled_rows) < samp:
            mat = mat_by_id.get(a.materialization_id) if a.materialization_id else None
            emitted = dict(mat.emitted_snapshot_json) if mat is not None else {}
            sampled_rows.append(
                {
                    "anchor_canonical_entity_id": str(a.canonical_entity_id),
                    "anchor_raw_record_id": int(a.raw_record_id),
                    "anchor_connector": a.connector,
                    "anchor_canonical_object_kind": a.canonical_object_kind,
                    "raw": (
                        None
                        if raw is None
                        else {
                            "id": int(raw.id),
                            "connector": raw.connector,
                            "resource_type": raw.resource_type,
                            "external_id": raw.external_id,
                            "continuity_fixture": _continuity_fixture_dict(raw_pl),
                            "identity_fields": _raw_identity_fields_public(raw_pl),
                        }
                    ),
                    "canonical": _canonical_public_slice(mat),
                    "anchor_runtime_payload_source": "raw_ingestion_records.payload_body_via_anchor.raw_record_id",
                    "continuity_signals": signals,
                    "identity_primitive_projection_debug": [
                        {
                            "projection_kind": p.projection_kind,
                            "extraction_role": p.extraction_role,
                            "org_entity_id": str(
                                org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=p)
                            ),
                            "org_entity_kind": resolve_org_entity_kind_for_identity_primitive(
                                projection_kind=p.projection_kind,
                                github_login=p.identity_material.get("github_login")
                                if p.projection_kind == "github_user"
                                else None,
                            )[0],
                            "identity_material_preview": _trunc_preview(p.identity_material, max_chars=1200),
                        }
                        for p in extract_identity_primitives(anchor=a, raw=raw)
                    ],
                    "org_projection": {
                        "representative_org_entity_id": str(
                            org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=a, raw=raw)
                        ),
                        "work_object_would_map_to_org_kind": org_kind_anchor,
                        "work_object_mapping_rule_id": mapping_rule_id,
                    },
                    "continuity_rules": {
                        "rule_pack_semantic": ANCHOR_CONTINUITY_RULE_SEMANTIC,
                        "rules_in_pack": [e["rule_id"] for e in _DEFAULT_MANIFEST["entries"]],
                        "eligible_rules": eligible,
                        "bucket_sizes_for_this_anchor": bucket_sizes,
                        "primary_skip_or_eligible": primary,
                        "missing_identity_flags": flags,
                    },
                    "fixture_propagation": {
                        "raw_has_continuity_fixture": _continuity_fixture_dict(raw_pl) is not None,
                        "canonical_emitted_has_continuity_fixture": _continuity_fixture_dict(emitted) is not None,
                        "runtime_reads_fixture_from_raw": True,
                        "canonical_snapshot_likely_omits_actor_metadata": (
                            mat is not None
                            and _continuity_fixture_dict(raw_pl) is not None
                            and _continuity_fixture_dict(emitted) is None
                        ),
                    },
                }
            )

        if len(fixture_survival) < surv and raw is not None and _continuity_fixture_dict(raw_pl):
            mat = mat_by_id.get(a.materialization_id) if a.materialization_id else None
            emitted = dict(mat.emitted_snapshot_json) if mat is not None else {}
            fixture_survival.append(
                {
                    "raw_record_id": int(raw.id),
                    "canonical_entity_id": str(a.canonical_entity_id),
                    "raw_has_continuity_fixture": True,
                    "canonical_emitted_has_continuity_fixture": _continuity_fixture_dict(emitted) is not None,
                    "anchor_runtime_sees_fixture_via_raw_join": True,
                }
            )

    overflow_accounting: dict[str, Any] = {}
    candidate_rows = build_anchor_continuity_candidate_rows(
        db, tenant_id=tenant_id, accounting_out=overflow_accounting
    )
    cand_raw_ids: set[int] = set()
    for r in candidate_rows:
        for x in r.get("evidence_raw_record_ids") or []:
            if isinstance(x, int):
                cand_raw_ids.add(x)
    cand_raw_by_id: dict[int, RawIngestionRecord] = dict(raw_by_id)
    if cand_raw_ids:
        lim_cand = sorted(cand_raw_ids)[:8_000]
        for rr in db.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.id.in_(lim_cand),
            )
        ).all():
            cand_raw_by_id[int(rr.id)] = rr
    pair_evidence_accumulation = accumulate_candidate_pair_evidence(candidate_rows, raw_by_id=cand_raw_by_id)

    for a in anchors:
        raw = raw_by_id.get(int(a.raw_record_id))
        if raw is None:
            continue
        sig2 = continuity_identity_signals_for_anchor(anchor=a, raw=raw)
        if sig2.get("continuity_fixture") is None:
            continue
        if int(raw.id) in cand_raw_ids:
            dry_anchor, dry_raw = a, raw
            break

    sparse_honesty = {
        "schema_version": "p04.substrate_sparse_honesty.v1",
        "anchors_scanned": counters["anchors_scanned"],
        "anchors_continuity_rule_eligible": counters["anchors_continuity_rule_eligible"],
        "current_engine_candidate_row_count": len(candidate_rows),
        "hit_global_candidate_edge_cap": bool(overflow_accounting.get("hit_global_candidate_edge_cap")),
        "candidate_generation_overflow_accounting": overflow_accounting,
        "interpretation": (
            "Sparse or empty candidates can be **valid** when join buckets are singletons. "
            "If ``hit_global_candidate_edge_cap`` is true, later rules may be starved — see overflow accounting."
        ),
    }

    dry_run: dict[str, Any] | None = None
    if dry_anchor is not None and dry_raw is not None:
        mat = mat_by_id.get(dry_anchor.materialization_id) if dry_anchor.materialization_id else None
        dry_payload = _payload_dict(dry_raw)
        dry_signals = continuity_identity_signals_for_anchor(anchor=dry_anchor, raw=dry_raw)
        elig, buckets = _eligible_rules_for_anchor(
            tenant_id=tenant_id,
            anchor=dry_anchor,
            raw=dry_raw,
            by_slack=by_slack,
            by_github=by_github,
            by_linear=by_linear,
            by_notion=by_notion,
            by_email_norm=by_email_norm,
            by_email_strict=by_email_strict,
            by_fixture=by_fixture,
            by_link_subject=by_link_subject,
            by_stable_account=by_stable_account,
        )
        rid = int(dry_raw.id)
        pair_rows_touching = [
            r
            for r in candidate_rows
            if rid in (r.get("evidence_raw_record_ids") or [])
        ]
        dry_run = {
            "raw": {
                "id": rid,
                "connector": dry_raw.connector,
                "resource_type": dry_raw.resource_type,
                "identity_fields": _raw_identity_fields_public(dry_payload),
                "payload_preview": _trunc_preview(dry_payload, max_chars=8000),
            },
            "canonical": _canonical_public_slice(mat),
            "anchor": {
                "canonical_entity_id": str(dry_anchor.canonical_entity_id),
                "canonical_object_kind": dry_anchor.canonical_object_kind,
                "connector": dry_anchor.connector,
                "raw_record_id": int(dry_anchor.raw_record_id),
                "provider_identity_json_preview": _trunc_preview(dict(dry_anchor.provider_identity_json or {}), max_chars=2000),
            },
            "continuity_signals": dry_signals,
            "rules_evaluated_summary": {
                "eligible_rules": elig,
                "bucket_sizes": buckets,
                "candidate_rows_total": len(candidate_rows),
                "candidate_rows_referencing_this_raw_id": len(pair_rows_touching),
                "sample_candidate_rows": _trunc_preview(pair_rows_touching[:12], max_chars=4000),
            },
            "identity_primitive_projection_chain": [
                {
                    "projection_kind": p.projection_kind,
                    "org_entity_id": str(org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=p)),
                    "org_entity_kind": resolve_org_entity_kind_for_identity_primitive(
                        projection_kind=p.projection_kind,
                        github_login=p.identity_material.get("github_login")
                        if p.projection_kind == "github_user"
                        else None,
                    )[0],
                }
                for p in extract_identity_primitives(anchor=dry_anchor, raw=dry_raw)
            ],
        }
    else:
        dry_run = {
            "note": "no_anchor_with_continuity_fixture_found_in_scanned_anchor_set",
            "anchors_scanned": len(anchors),
        }

    notes: list[str] = [
        "Continuity join keys are extracted from **raw** payload_body (see anchor_continuity_candidates). "
        "Canonical MESSAGE emitted_snapshot_json typically copies only channel/ts columns — "
        "continuity_fixture may be raw-only by design.",
        "Org handles for identity continuity are derived from **identity primitives** "
        "(slack_user, github_user, fixture keys, …) — not from work-object canonical kinds.",
        "``candidate_pair_evidence_accumulation`` groups current candidate rows by org-entity pair "
        "and counts edges, rules, connectors, and raw evidence ids — bookkeeping only, not merge.",
    ]

    prim_metrics = aggregate_identity_primitive_metrics(anchors=anchors, raw_by_id=raw_by_id)
    github_email_metrics = aggregate_github_email_extraction_metrics(
        anchors=anchors,
        raw_by_id=raw_by_id,
    )
    from vector.domains.cortex.identity.identity_continuity_health import (
        build_identity_continuity_gap_reasons_v1,
    )

    gap_reasons = build_identity_continuity_gap_reasons_v1(
        db,
        tenant_id=tenant_id,
        anchors_scanned=len(anchors),
        primitive_metrics=prim_metrics,
        github_email_metrics=github_email_metrics,
        candidate_row_count=len(candidate_rows),
        anchors_rule_eligible=counters["anchors_continuity_rule_eligible"],
    )

    out: dict[str, Any] = {
        "continuity_evidence_inspect_schema_version": CONTINUITY_EVIDENCE_INSPECT_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "anchor_scan_limit_applied": lim,
        "substrate_counters": counters,
        "anchors_primary_skip_reason_counts": dict(primary_skip_counts),
        "anchors_missing_identity_flag_counts": dict(missing_flag_counts),
        "canonical_kind_counts": dict(canonical_kind_counts),
        "org_entity_kind_counts": dict(org_entity_kind_counts),
        "rule_pack_semantic": ANCHOR_CONTINUITY_RULE_SEMANTIC,
        "current_engine_candidate_row_count": len(candidate_rows),
        "candidate_pair_evidence_accumulation": pair_evidence_accumulation,
        "substrate_sparse_honesty": sparse_honesty,
        "sampled_rows": sampled_rows,
        "fixture_survival_sample": fixture_survival,
        "hostile_continuity_dry_run_trace": dry_run,
        "identity_primitive_projection_metrics": prim_metrics,
        "github_email_extraction_metrics": github_email_metrics,
        "continuity_gap_reasons": gap_reasons,
        "continuity_join_reason_catalog": dict(CONTINUITY_JOIN_REASON_BY_RULE),
        "notes": notes,
    }

    _LOGGER.info(
        "continuity_evidence_inspect tenant_id=%s anchors=%s raw_join=%s eligible=%s candidates=%s "
        "unknown_org_kind_anchors=%s top_skip_reasons=%s",
        tenant_id,
        counters["anchors_scanned"],
        counters["anchors_with_raw_join"],
        counters["anchors_continuity_rule_eligible"],
        len(candidate_rows),
        counters["anchors_skipped_unknown_canonical_org_kind"],
        dict(primary_skip_counts.most_common(8)),
    )
    return out


def build_continuity_evidence_inspection_for_tenant(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchor_scan_limit: int = 50_000,
    sample_limit: int = 30,
    fixture_survival_sample_limit: int = 40,
) -> dict[str, Any]:
    """Wrapper that attaches ``scenario_key`` for admin responses."""
    from mock_connectors.fixtures.phase04_continuity_fixtures import (
        resolve_phase04_continuity_scenario_key,
    )

    core = build_continuity_evidence_inspection(
        db,
        tenant_id=tenant_id,
        anchor_scan_limit=anchor_scan_limit,
        sample_limit=sample_limit,
        fixture_survival_sample_limit=fixture_survival_sample_limit,
    )
    core["scenario_key"] = resolve_phase04_continuity_scenario_key()
    return core


def _anchor_relates_to_entity_v1(
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
) -> bool:
    if org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=anchor, raw=raw) == entity_id:
        return True
    for projection in extract_identity_primitives(anchor=anchor, raw=raw):
        if org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=projection) == entity_id:
            return True
    return False


def build_entity_continuity_evidence_inspection_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    anchor_scan_limit: int = 50_000,
    receipt_limit: int = 48,
) -> dict[str, Any]:
    """Entity-scoped continuity evidence receipts and generation rejection reasons."""
    lim = max(1, min(int(anchor_scan_limit), 100_000))
    receipt_cap = max(1, min(int(receipt_limit), 200))

    anchors = list(
        db.scalars(
            select(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
            .order_by(CortexCanonicalIdentityAnchor.canonical_entity_id.asc())
            .limit(lim)
        ).all()
    )
    raw_ids = {int(a.raw_record_id) for a in anchors}
    raw_by_id: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        for r in db.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))).all():
            raw_by_id[int(r.id)] = r

    mat_ids = {a.materialization_id for a in anchors if a.materialization_id is not None}
    mat_by_id: dict[uuid.UUID, CortexCanonicalTransformMaterialization] = {}
    if mat_ids:
        for m in db.scalars(
            select(CortexCanonicalTransformMaterialization).where(
                CortexCanonicalTransformMaterialization.id.in_(mat_ids)
            )
        ).all():
            mat_by_id[m.id] = m

    buckets = _build_join_buckets(tenant_id=tenant_id, anchors=anchors, raw_by_id=raw_by_id)
    (
        by_slack,
        by_github,
        by_linear,
        by_notion,
        by_email_norm,
        by_email_strict,
        by_fixture,
        by_link_subject,
        by_stable_account,
    ) = buckets

    evidence_receipts: list[dict[str, Any]] = []
    generation_rejections: list[dict[str, Any]] = []
    rejection_counts: Counter[str] = Counter()

    for a in anchors:
        raw = raw_by_id.get(int(a.raw_record_id))
        if not _anchor_relates_to_entity_v1(
            tenant_id=tenant_id, entity_id=entity_id, anchor=a, raw=raw
        ):
            continue

        raw_pl = _payload_dict(raw)
        signals = continuity_identity_signals_for_anchor(anchor=a, raw=raw)
        org_kind_anchor, mapping_rule_id = resolve_org_entity_kind_for_anchor(
            canonical_object_kind=a.canonical_object_kind,
            provider_login=provider_login_for_kind_resolution(a, raw),
        )
        canonical_unmapped = org_kind_anchor == "unknown_placeholder"

        eligible, bucket_sizes = _eligible_rules_for_anchor(
            tenant_id=tenant_id,
            anchor=a,
            raw=raw,
            by_slack=by_slack,
            by_github=by_github,
            by_linear=by_linear,
            by_notion=by_notion,
            by_email_norm=by_email_norm,
            by_email_strict=by_email_strict,
            by_fixture=by_fixture,
            by_link_subject=by_link_subject,
            by_stable_account=by_stable_account,
        )
        primary = _primary_skip_reason(
            raw=raw,
            eligible_rules=eligible,
            canonical_unmapped=canonical_unmapped,
            signals=signals,
        )
        rejection_counts[primary] += 1
        if primary != "continuity_eligible":
            generation_rejections.append(
                {
                    "anchor_canonical_entity_id": str(a.canonical_entity_id),
                    "anchor_raw_record_id": int(a.raw_record_id),
                    "primary_skip_reason_code": primary,
                    "eligible_rules": eligible,
                    "continuity_signals": signals,
                    "bucket_sizes_for_anchor": bucket_sizes,
                }
            )

        if len(evidence_receipts) >= receipt_cap:
            continue

        mat = mat_by_id.get(a.materialization_id) if a.materialization_id else None
        evidence_receipts.append(
            {
                "anchor_canonical_entity_id": str(a.canonical_entity_id),
                "anchor_raw_record_id": int(a.raw_record_id),
                "anchor_connector": a.connector,
                "anchor_canonical_object_kind": a.canonical_object_kind,
                "representative_org_entity_id": str(
                    org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=a, raw=raw)
                ),
                "continuity_signals": signals,
                "continuity_rules": {
                    "eligible_rules": eligible,
                    "bucket_sizes_for_this_anchor": bucket_sizes,
                    "primary_skip_or_eligible": primary,
                    "join_reason_catalog": CONTINUITY_JOIN_REASON_BY_RULE,
                },
                "identity_primitive_projections": [
                    {
                        "projection_kind": p.projection_kind,
                        "org_entity_id": str(
                            org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=p)
                        ),
                        "identity_material_preview": _trunc_preview(p.identity_material, max_chars=800),
                    }
                    for p in extract_identity_primitives(anchor=a, raw=raw)
                ],
                "raw_identity_fields": _raw_identity_fields_public(raw_pl),
                "canonical": _canonical_public_slice(mat),
            }
        )

    return {
        "entity_id": str(entity_id),
        "anchors_scanned": len(anchors),
        "anchors_related_to_entity": sum(
            1
            for a in anchors
            if _anchor_relates_to_entity_v1(
                tenant_id=tenant_id,
                entity_id=entity_id,
                anchor=a,
                raw=raw_by_id.get(int(a.raw_record_id)),
            )
        ),
        "evidence_receipts": evidence_receipts,
        "generation_rejections": generation_rejections[:receipt_cap],
        "generation_rejection_counts": dict(rejection_counts),
        "continuity_join_reason_catalog": CONTINUITY_JOIN_REASON_BY_RULE,
    }
