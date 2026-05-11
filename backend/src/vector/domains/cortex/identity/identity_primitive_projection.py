"""Deterministic identity primitive projection (Phase 04).

Work-object anchors (``message``, ``pull_request``, …) are not identity objects. This module
extracts connector-native identity primitives (Slack user id, GitHub login, fixture keys, …) and
builds stable **identity material** for org handle derivation so many work objects can collapse
onto one org entity per primitive key.

Normative: deterministic only — no inference beyond explicit payload / logical-key fields.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Final

import re

from vector.domains.cortex.identity.org_entities import (
    OrgEntityKind,
    deterministic_org_entity_id,
    identity_key_fingerprint,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

IDENTITY_PRIMITIVE_LANE: Final[str] = "p04_identity_primitive_v1"
IDENTITY_PRIMITIVE_SCHEMA_VERSION: Final[int] = 2

_BOT_LOGIN: Final[re.Pattern[str]] = re.compile(r"(bot\]|\[bot|dependabot|renovate|nexora-ci)", re.I)

# Lower sorts earlier — human execution identities before cross-tool fixture keys.
_PROJECTION_PRIORITY: Final[tuple[str, ...]] = (
    "slack_user",
    "github_user",
    "linear_user",
    "email_display_identity",
    "email_identity",
    "stable_account_identity",
    "cross_tool_cluster",
    "cross_tool_link_subject",
)
_PROJECTION_RANK: Final[dict[str, int]] = {k: i for i, k in enumerate(_PROJECTION_PRIORITY)}


# --- Raw payload helpers (duplicated from ``anchor_continuity_candidates`` to avoid import cycles) ---


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


def raw_has_declared_continuity_fixture(raw: RawIngestionRecord | None) -> bool:
    """True when raw carries an explicit ``continuity_fixture`` block (operator / test harness only)."""
    return _continuity_fixture_dict(_payload_dict(raw)) is not None


def _continuity_fixture_dict(payload: dict[str, Any]) -> dict[str, Any] | None:
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
    logins = _github_login_strings_deterministic(payload, prof)
    return logins[0] if logins else None


def _user_login_from_github_dict(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    login = obj.get("login")
    if isinstance(login, str) and login.strip():
        return login.strip().lower()
    return None


def _github_login_strings_deterministic(payload: dict[str, Any], prof: dict[str, Any]) -> list[str]:
    """All GitHub ``login`` values explicitly present on the payload (sorted, de-duplicated)."""
    found: set[str] = set()

    def add_login(obj: Any) -> None:
        s = _user_login_from_github_dict(obj) if isinstance(obj, dict) else None
        if s:
            found.add(s)

    def add_from_user_list(key: str, container: dict[str, Any]) -> None:
        v = container.get(key)
        if isinstance(v, list):
            for item in v:
                add_login(item)

    pr = payload.get("pull_request")
    if isinstance(pr, dict):
        add_login(pr.get("user"))
        add_login(pr.get("assignee"))
        add_from_user_list("assignees", pr)
        add_from_user_list("requested_reviewers", pr)
        add_login(pr.get("merged_by"))

    issue = payload.get("issue")
    if isinstance(issue, dict):
        add_login(issue.get("user"))
        add_login(issue.get("assignee"))
        add_from_user_list("assignees", issue)

    review = payload.get("review")
    if isinstance(review, dict):
        add_login(review.get("user"))

    comment = payload.get("comment")
    if isinstance(comment, dict):
        add_login(comment.get("user"))

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
            found.add(cur.strip().lower())

    v = prof.get("login") or prof.get("github_login")
    if isinstance(v, str) and v.strip():
        found.add(v.strip().lower())

    commits = payload.get("commits")
    if isinstance(commits, list):
        for c in commits[:30]:
            if not isinstance(c, dict):
                continue
            add_login(c.get("author"))
            add_login(c.get("committer"))

    return sorted(found)


_LINEAR_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-fA-F-]{32,36}$")


def _linear_id_string(val: Any) -> str | None:
    if isinstance(val, str) and _LINEAR_ID_RE.match(val.strip()):
        return val.strip()
    return None


def _add_linear_id(acc: set[str], val: Any) -> None:
    s = _linear_id_string(val)
    if s:
        acc.add(s)


def _linear_user_ids_deterministic(payload: dict[str, Any], prof: dict[str, Any]) -> list[str]:
    """Linear GraphQL-style user ids explicitly present (sorted, de-duplicated)."""
    ids: set[str] = set()
    top = (
        "linear_user_id",
        "creator_id",
        "assignee_id",
        "delegate_id",
        "user_id",
        "actor_id",
        "author_id",
    )
    for k in top:
        _add_linear_id(ids, payload.get(k))

    for wrap in ("issue", "comment", "data"):
        blk = payload.get(wrap)
        if isinstance(blk, dict):
            for key in ("creator", "assignee", "delegate", "user", "actor", "author"):
                u = blk.get(key)
                if isinstance(u, dict):
                    _add_linear_id(ids, u.get("id"))
                else:
                    _add_linear_id(ids, u)

    md = payload.get("metadata")
    if isinstance(md, dict):
        for key in ("linear_user_id", "creator_id", "assignee_id"):
            _add_linear_id(ids, md.get(key))

    uprof = prof.get("linear_user_id") or prof.get("id")
    _add_linear_id(ids, uprof)

    return sorted(ids)


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
    uo = payload.get("user")
    if isinstance(uo, dict):
        pr = uo.get("profile")
        if isinstance(pr, dict):
            for k in ("display_name", "real_name", "first_name"):
                v = pr.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip().lower()
    return None


def _email_for_rule(payload: dict[str, Any], prof: dict[str, Any]) -> tuple[str | None, str | None]:
    pr = payload.get("pull_request")
    pr_email = None
    if isinstance(pr, dict):
        u = pr.get("user")
        if isinstance(u, dict):
            pr_email = _norm_email(u.get("email"))
    slack_nested = None
    uo = payload.get("user")
    if isinstance(uo, dict):
        pr = uo.get("profile")
        if isinstance(pr, dict):
            slack_nested = _norm_email(pr.get("email"))
    commit_email = None
    commits = payload.get("commits")
    if isinstance(commits, list):
        for c in commits[:25]:
            if not isinstance(c, dict):
                continue
            for key in ("author", "committer"):
                a = c.get(key)
                if isinstance(a, dict):
                    commit_email = commit_email or _norm_email(a.get("email"))
                if commit_email:
                    break
            if commit_email:
                break
    em = (
        _norm_email(payload.get("user_email"))
        or _norm_email(payload.get("email"))
        or _norm_email(prof.get("email"))
        or pr_email
        or slack_nested
        or commit_email
    )
    if not em or "@" not in em:
        return None, None
    local, _, domain = em.partition("@")
    if not local or not domain:
        return None, None
    return em, domain.lower()


@dataclass(frozen=True, slots=True)
class IdentityPrimitiveProjection:
    """One deterministic identity primitive instance observed on a work-object anchor."""

    projection_kind: str
    extraction_role: str
    identity_material: dict[str, Any]


def resolve_org_entity_kind_for_identity_primitive(
    *,
    projection_kind: str,
    github_login: str | None = None,
) -> tuple[str, str]:
    """Map a primitive projection to a closed org entity kind (audit rule id is stable)."""
    pk = (projection_kind or "").strip()
    gl = (github_login or "").strip().lower() if isinstance(github_login, str) else None
    if pk == "github_user" and gl and _BOT_LOGIN.search(gl):
        return OrgEntityKind.SERVICE_ACCOUNT.value, "registry:identity_primitive:github_bot_login"
    # Person-centric execution substrate: evidence keys live in the fingerprint material
    # (``evidence_canonical_entity_id``, cluster keys, …) so handles stay distinct without
    # minting coordination-thread / repository_asset org kinds for real identities.
    if pk in {
        "linear_user",
        "cross_tool_cluster",
        "cross_tool_link_subject",
        "stable_account_identity",
        "email_display_identity",
        "email_identity",
    }:
        return OrgEntityKind.HUMAN_ACTOR.value, f"registry:identity_primitive_human_evidence:{pk}"
    return OrgEntityKind.HUMAN_ACTOR.value, f"registry:identity_primitive:{pk}"


def _material(
    *,
    projection_kind: str,
    connector: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "lane": IDENTITY_PRIMITIVE_LANE,
        "identity_primitive_schema_version": IDENTITY_PRIMITIVE_SCHEMA_VERSION,
        "projection_kind": projection_kind,
        "source_connector": (connector or "").strip().lower(),
    }
    out = {**base, **extra}
    return dict(sorted(out.items()))


def extract_identity_primitives(
    *,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
) -> list[IdentityPrimitiveProjection]:
    """Return sorted, de-duplicated primitive projections for one anchor + raw row."""
    connector = (anchor.connector or "").strip().lower()
    prof = dict(anchor.provider_identity_json or {})
    payload = _payload_dict(raw)
    anchor_eid = str(anchor.canonical_entity_id)
    rt = (raw.resource_type or "").strip().lower() if raw is not None else ""

    out: list[IdentityPrimitiveProjection] = []

    su = _slack_user_id(payload, prof)
    if su:
        out.append(
            IdentityPrimitiveProjection(
                projection_kind="slack_user",
                extraction_role="actor",
                identity_material=_material(
                    projection_kind="slack_user",
                    connector=connector,
                    extra={"slack_user_id": su},
                ),
            )
        )

    for gh_login in _github_login_strings_deterministic(payload, prof):
        out.append(
            IdentityPrimitiveProjection(
                projection_kind="github_user",
                extraction_role="actor",
                identity_material=_material(
                    projection_kind="github_user",
                    connector=connector,
                    extra={"github_login": gh_login},
                ),
            )
        )

    if connector == "linear" or rt.startswith("linear."):
        for lid in _linear_user_ids_deterministic(payload, prof):
            out.append(
                IdentityPrimitiveProjection(
                    projection_kind="linear_user",
                    extraction_role="actor",
                    identity_material=_material(
                        projection_kind="linear_user",
                        connector=connector or "linear",
                        extra={"linear_user_id": lid, "evidence_canonical_entity_id": anchor_eid},
                    ),
                ),
            )

    em, dom = _email_for_rule(payload, prof)
    dn = _display_name(payload)
    if em and dom and dn:
        out.append(
            IdentityPrimitiveProjection(
                projection_kind="email_display_identity",
                extraction_role="actor",
                identity_material=_material(
                    projection_kind="email_display_identity",
                    connector=connector,
                    extra={
                        "email_norm": em,
                        "email_domain": dom,
                        "display_name_norm": dn,
                        "evidence_canonical_entity_id": anchor_eid,
                    },
                ),
            )
        )
    elif em and dom:
        out.append(
            IdentityPrimitiveProjection(
                projection_kind="email_identity",
                extraction_role="actor",
                identity_material=_material(
                    projection_kind="email_identity",
                    connector=connector,
                    extra={
                        "email_norm": em,
                        "email_domain": dom,
                        "evidence_canonical_entity_id": anchor_eid,
                    },
                ),
            )
        )

    sak = _fixture_stable_account_key(payload)
    if sak:
        out.append(
            IdentityPrimitiveProjection(
                projection_kind="stable_account_identity",
                extraction_role="fixture",
                identity_material=_material(
                    projection_kind="stable_account_identity",
                    connector=connector,
                    extra={"stable_account_key": sak, "evidence_canonical_entity_id": anchor_eid},
                ),
            )
        )

    cf = _continuity_fixture_dict(payload)
    if cf:
        ck = cf.get("cluster_key")
        if isinstance(ck, str) and ck.strip():
            out.append(
                IdentityPrimitiveProjection(
                    projection_kind="cross_tool_cluster",
                    extraction_role="fixture",
                    identity_material=_material(
                        projection_kind="cross_tool_cluster",
                        connector=connector,
                        extra={"cluster_key": ck.strip(), "evidence_canonical_entity_id": anchor_eid},
                    ),
                )
            )
        ls = _fixture_link_subject(payload)
        if ls:
            out.append(
                IdentityPrimitiveProjection(
                    projection_kind="cross_tool_link_subject",
                    extraction_role="fixture",
                    identity_material=_material(
                        projection_kind="cross_tool_link_subject",
                        connector=connector,
                        extra={"link_subject": ls, "evidence_canonical_entity_id": anchor_eid},
                    ),
                )
            )

    # Deterministic de-duplication + priority sort (stable across processes).
    seen: set[str] = set()
    uniq: list[IdentityPrimitiveProjection] = []
    for p in sorted(
        out,
        key=lambda x: (
            _PROJECTION_RANK.get(x.projection_kind, 99),
            x.projection_kind,
            json.dumps(x.identity_material, sort_keys=True, separators=(",", ":")),
        ),
    ):
        fp = identity_key_fingerprint(p.identity_material)
        if fp in seen:
            continue
        seen.add(fp)
        uniq.append(p)
    return uniq


def org_entity_id_for_identity_primitive(
    *,
    tenant_id: uuid.UUID,
    projection: IdentityPrimitiveProjection,
) -> uuid.UUID:
    """Stable org entity id for one primitive projection (G-P04-ORG-01 lane)."""
    fp = identity_key_fingerprint(projection.identity_material)
    kind, _rule = resolve_org_entity_kind_for_identity_primitive(
        projection_kind=projection.projection_kind,
        github_login=projection.identity_material.get("github_login")
        if projection.projection_kind == "github_user"
        else None,
    )
    return deterministic_org_entity_id(tenant_id=tenant_id, entity_kind=kind, fingerprint=fp)


def identity_primitive_backfill_metadata(
    *,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
    projection: IdentityPrimitiveProjection,
    backfill_job_id: str | None,
) -> dict[str, Any]:
    """Metadata merged into org entity rows for operator provenance."""
    meta = {
        "anchor_backfill_lane": IDENTITY_PRIMITIVE_LANE,
        "identity_primitive_schema_version": IDENTITY_PRIMITIVE_SCHEMA_VERSION,
        "projection_kind": projection.projection_kind,
        "extraction_role": projection.extraction_role,
        "canonical_entity_id": str(anchor.canonical_entity_id),
        "canonical_object_kind": anchor.canonical_object_kind,
        "source_anchor_raw_record_id": int(anchor.raw_record_id),
        "source_anchor_connector": anchor.connector,
        "source_anchor_bundle_id": anchor.bundle_id,
        "continuity_seed_strategy": IDENTITY_PRIMITIVE_LANE,
        "entity_kind_mapping_rule_id": resolve_org_entity_kind_for_identity_primitive(
            projection_kind=projection.projection_kind,
            github_login=projection.identity_material.get("github_login")
            if projection.projection_kind == "github_user"
            else None,
        )[1],
        "provenance_label": f"identity_primitive:{projection.projection_kind}:{anchor.canonical_entity_id}",
    }
    if raw is not None:
        meta["source_resource_type"] = raw.resource_type
    if backfill_job_id:
        meta["backfill_job_id"] = backfill_job_id
    return meta


def github_login_strings_for_continuity(payload: dict[str, Any], prof: dict[str, Any]) -> list[str]:
    """Public: sorted GitHub logins extracted for continuity join keys (operator / inspector)."""
    return _github_login_strings_deterministic(payload, prof)


def linear_user_ids_for_continuity(payload: dict[str, Any], prof: dict[str, Any]) -> list[str]:
    """Public: sorted Linear user ids extracted for continuity join keys."""
    return _linear_user_ids_deterministic(payload, prof)


def aggregate_identity_primitive_metrics(
    *,
    anchors: list[CortexCanonicalIdentityAnchor],
    raw_by_id: dict[int, RawIngestionRecord],
) -> dict[str, Any]:
    """Grouped counters for operator / inspector (no DB writes)."""
    kind_counts: dict[str, int] = {}
    failures = 0
    total_primitives = 0
    anchors_with_zero_primitives = 0

    for a in anchors:
        raw = raw_by_id.get(int(a.raw_record_id))
        try:
            projs = extract_identity_primitives(anchor=a, raw=raw)
        except Exception:
            failures += 1
            continue
        if not projs:
            anchors_with_zero_primitives += 1
        for p in projs:
            total_primitives += 1
            kind_counts[p.projection_kind] = kind_counts.get(p.projection_kind, 0) + 1

    return {
        "identity_projection_schema_version": IDENTITY_PRIMITIVE_SCHEMA_VERSION,
        "identity_projection_kind_counts": dict(sorted(kind_counts.items())),
        "identity_projection_failures": failures,
        "identity_projection_total_primitives": total_primitives,
        "anchors_with_zero_extracted_primitives": anchors_with_zero_primitives,
    }
