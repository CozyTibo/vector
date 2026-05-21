"""Deterministic candidate continuity edges derived from anchors + raw evidence (Phase 04).

Candidate-only: never writes authoritative ``CortexOrgLink`` rows.
Normative: ``phase-04-candidate-vs-authoritative-linkage-doctrine.md``,
``phase-04-linkage-rule-engine-doctrine.md``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_projection import (
    legacy_org_handle_lane_eligible,
    org_entity_id_for_anchor_row,
)
from vector.domains.cortex.identity.identity_primitive_projection import (
    extract_identity_primitives,
    github_emails_for_continuity,
    github_login_strings_for_continuity,
    linear_user_ids_for_continuity,
    notion_user_ids_for_continuity,
    org_entity_id_for_identity_primitive,
)
from vector.domains.cortex.identity.candidate_generation import regenerate_link_candidates
from vector.domains.cortex.identity.continuity_candidate_evidence_accumulation import (
    accumulate_candidate_pair_evidence,
    preview_top_pair_families,
)
from vector.domains.cortex.identity.linkage_rules import create_link_rule_version, get_active_link_rule_version_by_semantic
from vector.domains.cortex.identity.org_ambiguity import ORG_AMBIGUITY_CLASSES, OrgAmbiguityError, append_org_ambiguity_record
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

ANCHOR_CONTINUITY_RULE_SEMANTIC: Final[str] = "p04.anchor_continuity_rules.v1"
RULE_SLACK_USER_ID: Final[str] = "p04.candidate.exact_slack_user_id_v1"
RULE_GITHUB_LOGIN: Final[str] = "p04.candidate.exact_github_login_v1"
RULE_EMAIL_EXACT: Final[str] = "p04.candidate.exact_email_localpart_domain_v1"
RULE_EMAIL_NORM_CONTINUITY_EVIDENCE: Final[str] = "p04.candidate.email_norm_continuity_evidence_v1"
RULE_CONTINUITY_FIXTURE_CLUSTER: Final[str] = "p04.candidate.continuity_fixture_cluster_key_v1"
RULE_FIXTURE_LINK_SUBJECT: Final[str] = "p04.candidate.fixture_declared_link_subject_v1"
RULE_FIXTURE_STABLE_ACCOUNT_KEY: Final[str] = "p04.candidate.fixture_declared_stable_account_key_v1"
RULE_LINEAR_USER_ID: Final[str] = "p04.candidate.exact_linear_user_id_v1"
RULE_NOTION_USER_ID: Final[str] = "p04.candidate.exact_notion_user_id_v1"

CONTINUITY_JOIN_REASON_BY_RULE: Final[dict[str, str]] = {
    RULE_SLACK_USER_ID: "same_slack_user_id",
    RULE_GITHUB_LOGIN: "same_github_login",
    RULE_LINEAR_USER_ID: "same_linear_user_id",
    RULE_NOTION_USER_ID: "same_notion_user_id",
    RULE_EMAIL_EXACT: "same_email_localpart_domain_display",
    RULE_EMAIL_NORM_CONTINUITY_EVIDENCE: "same_email_norm",
    RULE_CONTINUITY_FIXTURE_CLUSTER: "same_continuity_fixture_cluster",
    RULE_FIXTURE_LINK_SUBJECT: "same_fixture_link_subject",
    RULE_FIXTURE_STABLE_ACCOUNT_KEY: "same_stable_account_key",
}

_DEFAULT_MANIFEST: Final[dict[str, Any]] = {
    "rule_pack_id": "p04.anchor_continuity.v1",
    "entries": [
        {"rule_id": RULE_SLACK_USER_ID, "kind": "exact_provider_key"},
        {"rule_id": RULE_GITHUB_LOGIN, "kind": "exact_provider_key"},
        {"rule_id": RULE_LINEAR_USER_ID, "kind": "exact_linear_user_id"},
        {"rule_id": RULE_NOTION_USER_ID, "kind": "exact_notion_user_id"},
        {"rule_id": RULE_EMAIL_EXACT, "kind": "exact_email"},
        {"rule_id": RULE_EMAIL_NORM_CONTINUITY_EVIDENCE, "kind": "email_norm_continuity_evidence"},
        {"rule_id": RULE_CONTINUITY_FIXTURE_CLUSTER, "kind": "fixture_declared_cluster"},
        {"rule_id": RULE_FIXTURE_LINK_SUBJECT, "kind": "fixture_declared_link_subject"},
        {"rule_id": RULE_FIXTURE_STABLE_ACCOUNT_KEY, "kind": "fixture_declared_stable_account_key"},
    ],
}

_MAX_CANDIDATE_ROWS: Final[int] = 2_000


def _dedupe_bucket_rows(
    items: list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]],
) -> list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]:
    deduped: dict[tuple[uuid.UUID, int], tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]] = {}
    for t in items:
        deduped[(t[0], t[1])] = t
    return sorted(deduped.values(), key=lambda x: (str(x[0]), x[1]))


def _cross_entity_pair_count(sorted_items: list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]) -> int:
    n = len(sorted_items)
    c = 0
    for i in range(n):
        for j in range(i + 1, n):
            if sorted_items[i][0] != sorted_items[j][0]:
                c += 1
    return c


def _eligible_pairs_total_for_buckets(
    bucket_map: dict[Any, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
) -> tuple[int, int]:
    """Return ``(eligible_cross_entity_pairs, buckets_with_ge2_rows)`` without emitting edges."""
    eligible = 0
    buckets_ge2 = 0
    for _k, items in sorted(bucket_map.items()):
        u = _dedupe_bucket_rows(items)
        if len(u) < 2:
            continue
        buckets_ge2 += 1
        eligible += _cross_entity_pair_count(u)
    return eligible, buckets_ge2


def _emit_cross_entity_pairs_from_bucket(
    sorted_items: list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]],
    rule_id: str,
    rows_out: list[dict[str, Any]],
    *,
    max_rows: int,
) -> tuple[int, bool]:
    """Emit cross-entity pairs; return ``(emitted_count, stopped_due_to_cap)``."""
    emitted = 0
    n = len(sorted_items)
    for i in range(n):
        for j in range(i + 1, n):
            e1, r1, _ = sorted_items[i]
            e2, r2, _ = sorted_items[j]
            if e1 == e2:
                continue
            if len(rows_out) >= max_rows:
                return emitted, True
            a_id, b_id = (e1, e2) if str(e1) < str(e2) else (e2, e1)
            ra, rb = (r1, r2) if str(e1) < str(e2) else (r2, r1)
            rows_out.append(
                {
                    "link_type": "org.persona_belongs_to_handle",
                    "source_entity_id": str(a_id),
                    "target_entity_id": str(b_id),
                    "evidence_raw_record_ids": sorted({ra, rb}),
                    "rule_id": rule_id,
                    "continuity_join_reason": CONTINUITY_JOIN_REASON_BY_RULE.get(
                        rule_id,
                        "deterministic_rule_match",
                    ),
                }
            )
            emitted += 1
    return emitted, False


def _process_single_rule_buckets(
    bucket_map: dict[Any, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]],
    rule_id: str,
    rows_out: list[dict[str, Any]],
    *,
    max_rows: int,
    rule_metrics: dict[str, Any],
) -> bool:
    """Process all buckets for one rule. Returns True if global edge cap was hit."""
    bucket_list = sorted(bucket_map.items(), key=lambda kv: str(kv[0]))
    for bi, (_k, items) in enumerate(bucket_list):
        sorted_items = _dedupe_bucket_rows(items)
        if len(sorted_items) < 2:
            continue
        elig_bucket = _cross_entity_pair_count(sorted_items)
        rule_metrics["eligible_cross_entity_pairs_across_buckets"] += elig_bucket
        rule_metrics["buckets_with_ge2_distinct_org_entity_rows"] += 1
        before = len(rows_out)
        emitted_here, cap_hit = _emit_cross_entity_pairs_from_bucket(
            sorted_items, rule_id, rows_out, max_rows=max_rows
        )
        rule_metrics["edges_emitted"] = rule_metrics.get("edges_emitted", 0) + emitted_here
        if cap_hit:
            emitted_in_bucket = len(rows_out) - before
            suppressed_this_bucket = max(0, elig_bucket - emitted_in_bucket)
            rule_metrics["edges_suppressed_due_to_global_cap"] = (
                rule_metrics.get("edges_suppressed_due_to_global_cap", 0) + suppressed_this_bucket
            )
            for _k2, items2 in bucket_list[bi + 1 :]:
                u2 = _dedupe_bucket_rows(items2)
                if len(u2) < 2:
                    continue
                si2 = sorted(u2, key=lambda t: (str(t[0]), t[1]))
                skipped_elig = _cross_entity_pair_count(si2)
                rule_metrics["edges_suppressed_due_to_global_cap"] += skipped_elig
                rule_metrics["eligible_cross_entity_pairs_in_buckets_skipped_after_cap"] = (
                    rule_metrics.get("eligible_cross_entity_pairs_in_buckets_skipped_after_cap", 0)
                    + skipped_elig
                )
            return True
    return False


def _norm_email(val: object) -> str | None:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    return s or None


def _payload_dict(raw: RawIngestionRecord | None) -> dict[str, Any]:
    if raw is None:
        return {}
    p = raw.payload_body
    return dict(p) if isinstance(p, dict) else {}


def continuity_identity_signals_for_anchor(
    *,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
) -> dict[str, Any]:
    """Normalized identity + fixture fields used by anchor continuity (operator / evidence inspector).

    Canonical materialization snapshots often omit ``metadata`` / actor fields; continuity rules still
    read **raw** ``payload_body`` joined via ``anchor.raw_record_id`` — this struct reflects that path.
    """
    payload = _payload_dict(raw)
    prof = dict(anchor.provider_identity_json or {})
    em, dom = _email_for_rule(payload, prof)
    dn = _display_name(payload)
    cf = _continuity_fixture_dict(payload)
    return {
        "raw_record_joined": raw is not None,
        "slack_user_id": _slack_user_id(payload, prof),
        "github_login": _github_login(payload, prof),
        "github_logins": github_login_strings_for_continuity(payload, prof),
        "github_emails": github_emails_for_continuity(payload, prof),
        "notion_user_ids": notion_user_ids_for_continuity(payload),
        "linear_user_ids": linear_user_ids_for_continuity(payload, prof),
        "email_normalized": em,
        "email_domain": dom,
        "display_name_normalized": dn,
        "email_rule_tuple_ready": bool(em and dom and dn),
        "continuity_fixture": cf,
        "fixture_cluster_key": _continuity_fixture_cluster(payload),
        "fixture_link_subject": _fixture_link_subject(payload),
        "fixture_stable_account_key": _fixture_stable_account_key(payload),
    }


def _continuity_fixture_dict(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve ``continuity_fixture`` from Slack-style root metadata or GitHub ``pull_request.metadata``."""
    md = payload.get("metadata")
    if isinstance(md, dict):
        cf = md.get("continuity_fixture")
        if isinstance(cf, dict):
            return cf
    msg = payload.get("message")
    if isinstance(msg, dict):
        mm = msg.get("metadata")
        if isinstance(mm, dict):
            cf = mm.get("continuity_fixture")
            if isinstance(cf, dict):
                return cf
    pr = payload.get("pull_request")
    if isinstance(pr, dict):
        pmd = pr.get("metadata")
        if isinstance(pmd, dict):
            cf = pmd.get("continuity_fixture")
            if isinstance(cf, dict):
                return cf
    return None


def _continuity_fixture_cluster(payload: dict[str, Any]) -> str | None:
    cf = _continuity_fixture_dict(payload)
    if not cf:
        return None
    ck = cf.get("cluster_key")
    return str(ck).strip() if isinstance(ck, str) and ck.strip() else None


def _fixture_link_subject(payload: dict[str, Any]) -> str | None:
    cf = _continuity_fixture_dict(payload)
    if not cf:
        return None
    ls = cf.get("link_subject")
    return str(ls).strip() if isinstance(ls, str) and ls.strip() else None


def _fixture_stable_account_key(payload: dict[str, Any]) -> str | None:
    cf = _continuity_fixture_dict(payload)
    if not cf:
        return None
    sk = cf.get("stable_account_key")
    return str(sk).strip() if isinstance(sk, str) and sk.strip() else None


def _slack_user_id(payload: dict[str, Any], prof: dict[str, Any]) -> str | None:
    for k in ("slack_user_id", "user_id"):
        v = payload.get(k) or prof.get(k)
        if isinstance(v, str) and v.strip().startswith("U") and len(v.strip()) >= 4:
            return v.strip()
    msg = payload.get("message")
    if isinstance(msg, dict):
        u = msg.get("user")
        if isinstance(u, str) and u.strip().startswith("U"):
            return u.strip()
    return None


def _github_login(payload: dict[str, Any], prof: dict[str, Any]) -> str | None:
    pr = payload.get("pull_request")
    if isinstance(pr, dict):
        u = pr.get("user")
        if isinstance(u, dict):
            login = u.get("login")
            if isinstance(login, str) and login.strip():
                return login.strip().lower()
    for path in (
        ("sender", "login"),
        ("user", "login"),
        ("author", "login"),
    ):
        cur: Any = payload
        ok = True
        for p in path:
            if not isinstance(cur, dict):
                ok = False
                break
            cur = cur.get(p)
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip().lower()
    v = prof.get("login") or prof.get("github_login")
    if isinstance(v, str) and v.strip():
        return v.strip().lower()
    return None


def _display_name(payload: dict[str, Any]) -> str | None:
    for k in ("display_name", "name", "full_name", "real_name"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    pr = payload.get("pull_request")
    if isinstance(pr, dict):
        u = pr.get("user")
        if isinstance(u, dict):
            for k in ("name", "login"):
                v = u.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip().lower()
    prof = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    if isinstance(prof, dict):
        dn = prof.get("display_name") or prof.get("real_name")
        if isinstance(dn, str) and dn.strip():
            return dn.strip().lower()
    return None


def _email_for_rule(payload: dict[str, Any], prof: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(email_norm, domain)`` for strict same-domain+same-display rule."""
    pr = payload.get("pull_request")
    pr_email = None
    if isinstance(pr, dict):
        u = pr.get("user")
        if isinstance(u, dict):
            pr_email = _norm_email(u.get("email"))
    em = (
        _norm_email(payload.get("user_email"))
        or _norm_email(payload.get("email"))
        or _norm_email(prof.get("email"))
        or pr_email
    )
    if not em or "@" not in em:
        return None, None
    local, _, domain = em.partition("@")
    if not local or not domain:
        return None, None
    return em, domain.lower()


def ensure_anchor_continuity_rule_pack(db: Session, *, tenant_id: uuid.UUID) -> uuid.UUID:
    """Idempotently ensure the semantic rule pack exists; return its row id."""
    existing = get_active_link_rule_version_by_semantic(db, tenant_id=tenant_id, semantic_version=ANCHOR_CONTINUITY_RULE_SEMANTIC)
    if existing is not None:
        return existing.id
    row = create_link_rule_version(
        db,
        tenant_id=tenant_id,
        semantic_version=ANCHOR_CONTINUITY_RULE_SEMANTIC,
        rules_manifest_json=_DEFAULT_MANIFEST,
        notes="Auto-seeded anchor continuity candidate rules (deterministic, fixture-safe).",
    )
    return row.id


def build_anchor_continuity_candidate_rows(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    accounting_out: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build ``org.persona_belongs_to_handle`` candidate rows from strict join keys only.

    When ``accounting_out`` is provided, it is **replaced** with deterministic overflow / per-rule
    bookkeeping (does **not** affect ``candidate_set_sha256`` — row projection unchanged).
    """
    anchors = list(
        db.scalars(
            select(CortexCanonicalIdentityAnchor).where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id),
        ).all()
    )
    raw_ids = {int(a.raw_record_id) for a in anchors}
    raw_by_id: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        for r in db.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))).all():
            raw_by_id[int(r.id)] = r

    by_slack: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_github: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_email_strict: dict[tuple[str, str, str], list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_fixture: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_link_subject: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_stable_account: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_linear: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_notion: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)
    by_email_norm: dict[str, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]] = defaultdict(list)

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

        # Back-compat: if extractor missed connector-native keys still present on raw, bucket once per anchor.
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
            fc = _continuity_fixture_cluster(payload)
            if fc:
                by_fixture[fc].append((eid, rid, a))
            ls = _fixture_link_subject(payload)
            if ls:
                by_link_subject[ls].append((eid, rid, a))
            sak = _fixture_stable_account_key(payload)
            if sak:
                by_stable_account[sak].append((eid, rid, a))

    rows_out: list[dict[str, Any]] = []

    rule_kind_by_id = {str(e["rule_id"]): str(e.get("kind") or "") for e in _DEFAULT_MANIFEST.get("entries", [])}
    rule_phases: tuple[tuple[str, dict[Any, list[tuple[uuid.UUID, int, CortexCanonicalIdentityAnchor]]]], ...] = (
        (RULE_SLACK_USER_ID, by_slack),
        (RULE_GITHUB_LOGIN, by_github),
        (RULE_LINEAR_USER_ID, by_linear),
        (RULE_NOTION_USER_ID, by_notion),
        (RULE_EMAIL_EXACT, by_email_strict),
        (RULE_EMAIL_NORM_CONTINUITY_EVIDENCE, by_email_norm),
        (RULE_CONTINUITY_FIXTURE_CLUSTER, by_fixture),
        (RULE_FIXTURE_LINK_SUBJECT, by_link_subject),
        (RULE_FIXTURE_STABLE_ACCOUNT_KEY, by_stable_account),
    )

    acc: dict[str, Any] = {
        "schema_version": "p04.anchor_candidate_generation_accounting.v1",
        "global_max_candidate_edges": _MAX_CANDIDATE_ROWS,
        "rule_evaluation_order": [rid for rid, _ in rule_phases],
        "anchor_count": len(anchors),
        "per_rule": {},
        "rules_never_started_after_global_cap": [],
        "hit_global_candidate_edge_cap": False,
        "first_rule_truncated_after_emission": None,
        "eligible_cross_entity_pairs_in_rules_never_started_after_cap": 0,
        "deterministic_notes": [],
    }

    for rid, bmap in rule_phases:
        acc["per_rule"][rid] = {
            "rule_id": rid,
            "manifest_kind": rule_kind_by_id.get(rid),
            "eligible_cross_entity_pairs_across_buckets": 0,
            "buckets_with_ge2_distinct_org_entity_rows": 0,
            "edges_emitted": 0,
            "edges_suppressed_due_to_global_cap": 0,
            "eligible_cross_entity_pairs_in_buckets_skipped_after_cap": 0,
        }
        if len(rows_out) >= _MAX_CANDIDATE_ROWS:
            acc["rules_never_started_after_global_cap"].append(rid)
            continue
        trunc = _process_single_rule_buckets(
            bmap,
            rid,
            rows_out,
            max_rows=_MAX_CANDIDATE_ROWS,
            rule_metrics=acc["per_rule"][rid],
        )
        if trunc:
            acc["hit_global_candidate_edge_cap"] = True
            if acc["first_rule_truncated_after_emission"] is None:
                acc["first_rule_truncated_after_emission"] = rid

    for rid, bmap in rule_phases:
        if rid in acc["rules_never_started_after_global_cap"]:
            e_skip, _ = _eligible_pairs_total_for_buckets(bmap)
            acc["eligible_cross_entity_pairs_in_rules_never_started_after_cap"] += e_skip

    acc["edges_emitted_total"] = len(rows_out)
    acc["hit_global_candidate_edge_cap"] = len(rows_out) >= _MAX_CANDIDATE_ROWS
    if acc["hit_global_candidate_edge_cap"]:
        acc["deterministic_notes"].append(
            "Candidate edge global cap reached: later rules in evaluation order may emit zero edges "
            "even when buckets exist — compare per_rule.edges_suppressed_due_to_global_cap and "
            "rules_never_started_after_global_cap."
        )
    if anchors and not rows_out:
        acc["deterministic_notes"].append(
            "Zero candidate edges with anchors present: usually insufficient multi-entity join buckets "
            "or identity primitives missing on raw payloads (not necessarily a replay failure)."
        )

    if accounting_out is not None:
        accounting_out.clear()
        accounting_out.update(acc)

    return rows_out


def maybe_record_email_slack_ambiguity(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchors_with_raw: list[tuple[CortexCanonicalIdentityAnchor, RawIngestionRecord | None]],
) -> int:
    """When two human handles share email+display but different Slack user ids, open one ambiguity row."""
    by_key: dict[tuple[str, str, str], list[tuple[uuid.UUID, str | None]]] = defaultdict(list)
    for a, raw in anchors_with_raw:
        payload = _payload_dict(raw)
        prof = dict(a.provider_identity_json or {})
        projs = extract_identity_primitives(anchor=a, raw=raw)
        slack_proj = next((p for p in projs if p.projection_kind == "slack_user"), None)
        email_proj = next((p for p in projs if p.projection_kind == "email_display_identity"), None)
        if slack_proj is None or email_proj is None:
            continue
        su = slack_proj.identity_material.get("slack_user_id")
        em = email_proj.identity_material.get("email_norm")
        dom = email_proj.identity_material.get("email_domain")
        dn = email_proj.identity_material.get("display_name_norm")
        if not (isinstance(su, str) and su.strip() and isinstance(em, str) and isinstance(dom, str) and isinstance(dn, str)):
            continue
        eid = org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=slack_proj)
        by_key[(em, dom, dn)].append((eid, su.strip()))

    created = 0
    for _k, lst in by_key.items():
        slack_ids = {s for _, s in lst if s}
        eids = {e for e, _ in lst}
        if len(slack_ids) <= 1 or len(eids) < 2:
            continue
        subject = f"email_slack_multiplicity:{_k[0]}"
        try:
            append_org_ambiguity_record(
                db,
                tenant_id=tenant_id,
                org_ambiguity_class="multiple_persona_unresolved",
                subject_key=subject[:512],
                involved_org_entity_ids=sorted(eids),
                status="open",
                evidence_json={
                    "slack_user_ids": sorted(slack_ids),
                    "deterministic_classifier": "anchor_continuity_email_slack_split_v1",
                },
            )
            created += 1
        except OrgAmbiguityError:
            continue
    return created


def maybe_record_email_norm_slack_multiplicity(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchors_with_raw: list[tuple[CortexCanonicalIdentityAnchor, RawIngestionRecord | None]],
) -> int:
    """When the same normalized email appears with multiple Slack user ids, open one ambiguity row.

    Evidence-only: does **not** assert same person — only records connector-local multiplicity on a
    shared email_norm key (organizational uncertainty surface).
    """
    by_email: dict[str, list[tuple[uuid.UUID, str]]] = defaultdict(list)
    for a, raw in anchors_with_raw:
        projs = extract_identity_primitives(anchor=a, raw=raw)
        slack_proj = next((p for p in projs if p.projection_kind == "slack_user"), None)
        if slack_proj is None:
            continue
        em: str | None = None
        for p in projs:
            if p.projection_kind not in ("email_display_identity", "email_identity"):
                continue
            n = p.identity_material.get("email_norm")
            if isinstance(n, str) and n.strip():
                em = n.strip().lower()
                break
        if not em:
            continue
        su = slack_proj.identity_material.get("slack_user_id")
        if not isinstance(su, str) or not su.strip():
            continue
        eid = org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=slack_proj)
        by_email[em].append((eid, su.strip()))

    created = 0
    for em_key, lst in sorted(by_email.items()):
        slack_ids = {s for _, s in lst if s}
        eids = {e for e, _ in lst}
        if len(slack_ids) <= 1 or len(eids) < 2:
            continue
        subject = f"email_norm_slack_multiplicity:{em_key}"[:512]
        try:
            append_org_ambiguity_record(
                db,
                tenant_id=tenant_id,
                org_ambiguity_class="multiple_persona_unresolved",
                subject_key=subject,
                involved_org_entity_ids=sorted(eids),
                status="open",
                evidence_json={
                    "email_norm": em_key,
                    "slack_user_ids": sorted(slack_ids),
                    "deterministic_classifier": "anchor_continuity_email_norm_slack_multiplicity_v1",
                },
            )
            created += 1
        except OrgAmbiguityError:
            continue
    return created


def maybe_record_fixture_ambiguity_cohorts(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchors_with_raw: list[tuple[CortexCanonicalIdentityAnchor, RawIngestionRecord | None]],
) -> int:
    """Open one ambiguity per ``(ambiguity_cohort_key, org_ambiguity_class)`` when fixtures declare ≥2 handles."""
    cohort_entities: dict[tuple[str, str], list[uuid.UUID]] = defaultdict(list)
    for a, raw in anchors_with_raw:
        payload = _payload_dict(raw)
        cf = _continuity_fixture_dict(payload)
        if not cf:
            continue
        cohort = cf.get("ambiguity_cohort_key")
        oclass = cf.get("org_ambiguity_class")
        if not isinstance(cohort, str) or not cohort.strip():
            continue
        if not isinstance(oclass, str) or not oclass.strip():
            continue
        cls = oclass.strip()
        if cls not in ORG_AMBIGUITY_CLASSES:
            continue
        projs = extract_identity_primitives(anchor=a, raw=raw)
        eid = None
        for pref in (
            "slack_user",
            "github_user",
            "linear_user",
            "cross_tool_cluster",
            "stable_account_identity",
            "email_display_identity",
            "cross_tool_link_subject",
        ):
            hit = next((p for p in projs if p.projection_kind == pref), None)
            if hit is not None:
                eid = org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=hit)
                break
        if eid is None:
            if not legacy_org_handle_lane_eligible(
                canonical_object_kind=a.canonical_object_kind,
                raw=raw,
            ):
                continue
            eid = org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=a, raw=raw)
        cohort_entities[(cohort.strip(), cls)].append(eid)

    created = 0
    for (cohort, cls), eids in sorted(cohort_entities.items()):
        uniq = sorted(set(eids))
        if len(uniq) < 2:
            continue
        subject_key = f"fixture_cohort:{cohort}:{cls}"[:512]
        try:
            append_org_ambiguity_record(
                db,
                tenant_id=tenant_id,
                org_ambiguity_class=cls,
                subject_key=subject_key,
                involved_org_entity_ids=uniq,
                status="open",
                evidence_json={
                    "ambiguity_cohort_key": cohort,
                    "deterministic_classifier": "anchor_continuity_fixture_cohort_v1",
                },
            )
            created += 1
        except OrgAmbiguityError:
            continue
    return created


def compute_anchor_evidence_input_sha256(anchors: list[CortexCanonicalIdentityAnchor]) -> str:
    """Deterministic fingerprint of anchor evidence rows driving candidate regen (replay lineage)."""
    parts = [
        f"{a.canonical_entity_id}|{int(a.raw_record_id)}|{a.connector}|{a.canonical_object_kind}"
        for a in anchors
    ]
    parts.sort()
    blob = json.dumps(parts, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def run_anchor_continuity_candidate_regeneration(
    db: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Ensure rule pack, optionally record ambiguities, persist one candidate batch (may be empty)."""
    ver_id = ensure_anchor_continuity_rule_pack(db, tenant_id=tenant_id)
    anchors = list(
        db.scalars(select(CortexCanonicalIdentityAnchor).where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)).all()
    )
    anchor_fp = compute_anchor_evidence_input_sha256(anchors)
    raw_ids = {int(a.raw_record_id) for a in anchors}
    raw_by_id: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        for r in db.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))).all():
            raw_by_id[int(r.id)] = r
    pairs = [(a, raw_by_id.get(int(a.raw_record_id))) for a in anchors]
    n_email_amb = maybe_record_email_slack_ambiguity(db, tenant_id=tenant_id, anchors_with_raw=pairs)
    n_email_norm_slack = maybe_record_email_norm_slack_multiplicity(db, tenant_id=tenant_id, anchors_with_raw=pairs)
    n_fixture_amb = maybe_record_fixture_ambiguity_cohorts(db, tenant_id=tenant_id, anchors_with_raw=pairs)

    overflow_acc: dict[str, Any] = {}
    rows = build_anchor_continuity_candidate_rows(db, tenant_id=tenant_id, accounting_out=overflow_acc)
    if not rows:
        # Still emit an empty batch for replay visibility (deterministic hash of empty set).
        rows = []

    out = regenerate_link_candidates(
        db,
        tenant_id=tenant_id,
        rule_version=ANCHOR_CONTINUITY_RULE_SEMANTIC,
        rows=rows,
        link_rule_version_id=ver_id,
    )
    out["anchor_evidence_input_sha256"] = anchor_fp
    out["ambiguity_opened_email_slack_multiplicity"] = n_email_amb
    out["ambiguity_opened_email_norm_slack_multiplicity"] = n_email_norm_slack
    out["ambiguity_opened_fixture_cohort"] = n_fixture_amb
    out["candidate_generation_overflow_accounting"] = overflow_acc
    acc_full = accumulate_candidate_pair_evidence(rows, raw_by_id=raw_by_id)
    out["continuity_pair_evidence_preview"] = preview_top_pair_families(acc_full, limit=12)
    return out


def candidate_touch_counts(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20_000,
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    """Return ``(persona_candidate_touch_count, any_candidate_touch_count)`` per org entity id."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexOrgLinkCandidate)
            .where(CortexOrgLinkCandidate.tenant_id == tenant_id)
            .order_by(CortexOrgLinkCandidate.created_at.desc())
            .limit(lim)
        ).all()
    )
    persona: dict[uuid.UUID, int] = defaultdict(int)
    total: dict[uuid.UUID, int] = defaultdict(int)
    for r in rows:
        for eid in (r.source_entity_id, r.target_entity_id):
            total[eid] += 1
            if r.link_type == "org.persona_belongs_to_handle":
                persona[eid] += 1
    return dict(persona), dict(total)


def open_ambiguity_touch_counts(db: Session, *, tenant_id: uuid.UUID, limit: int = 2_000) -> dict[uuid.UUID, int]:
    from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord

    lim = max(1, min(limit, 10_000))
    rows = list(
        db.scalars(
            select(CortexOrgAmbiguityRecord).where(
                CortexOrgAmbiguityRecord.tenant_id == tenant_id,
                CortexOrgAmbiguityRecord.status == "open",
            ).limit(lim)
        ).all()
    )
    touch: dict[uuid.UUID, int] = defaultdict(int)
    for r in rows:
        raw_ids = r.involved_org_entity_ids or []
        if not isinstance(raw_ids, list):
            continue
        for x in raw_ids:
            try:
                u = uuid.UUID(str(x).strip())
            except ValueError:
                continue
            touch[u] += 1
    return dict(touch)
