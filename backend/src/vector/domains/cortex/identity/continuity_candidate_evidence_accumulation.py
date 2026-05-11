"""Deterministic evidence accumulation for org link candidate families (Phase 04).

Aggregates **explainable counts** per undirected org-entity pair (candidate family) from the
current candidate row set. This is continuity substrate bookkeeping — not scoring, not merge.

Derived only from ``(rows, raw_by_id)`` so replays that reproduce the same candidate rows yield
the same accumulation JSON.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Final

ACCUMULATION_SCHEMA_VERSION: Final[str] = "p04.candidate_evidence_accumulation.v1"

# Mirrors ``_DEFAULT_MANIFEST`` rule_id → kind (avoid import cycle with anchor_continuity_candidates).
ACCUMULATION_MANIFEST_KIND_BY_RULE_ID: Final[dict[str, str]] = {
    "p04.candidate.exact_slack_user_id_v1": "exact_provider_key",
    "p04.candidate.exact_github_login_v1": "exact_provider_key",
    "p04.candidate.exact_linear_user_id_v1": "exact_linear_user_id",
    "p04.candidate.exact_email_localpart_domain_v1": "exact_email",
    "p04.candidate.email_norm_continuity_evidence_v1": "email_norm_continuity_evidence",
    "p04.candidate.continuity_fixture_cluster_key_v1": "fixture_declared_cluster",
    "p04.candidate.fixture_declared_link_subject_v1": "fixture_declared_link_subject",
    "p04.candidate.fixture_declared_stable_account_key_v1": "fixture_declared_stable_account_key",
}

_EXPLAIN_LINE_BY_MANIFEST_KIND: Final[dict[str, str]] = {
    "exact_provider_key": "Same deterministic provider-native key appears on multiple org-entity fingerprints.",
    "exact_linear_user_id": "Same Linear user id bucket ties multiple identity primitive fingerprints.",
    "exact_email": "Exact same normalized email + domain + display-name tuple across anchors.",
    "email_norm_continuity_evidence": "Same normalized email across anchors (continuity evidence only — not same-person).",
    "fixture_declared_cluster": "Same declared continuity_fixture cluster_key across anchors.",
    "fixture_declared_link_subject": "Same declared fixture link_subject across anchors.",
    "fixture_declared_stable_account_key": "Same declared stable_account_key across anchors.",
}


def _pair_key(source: uuid.UUID, target: uuid.UUID) -> tuple[str, str, str]:
    s, t = str(source), str(target)
    if s <= t:
        return s, t, f"{s}|{t}"
    return t, s, f"{t}|{s}"


def accumulate_candidate_pair_evidence(
    rows: list[dict[str, Any]],
    *,
    raw_by_id: dict[int, Any],
) -> dict[str, Any]:
    """Return sorted, JSON-serializable accumulation for operator / inspector (no DB writes)."""
    families: dict[str, dict[str, Any]] = {}

    def _fetched_bounds(rids: list[int]) -> dict[str, Any]:
        ts: list[datetime] = []
        for rid in rids:
            raw = raw_by_id.get(rid)
            if raw is None:
                continue
            fa = getattr(raw, "fetched_at", None)
            if isinstance(fa, datetime):
                ts.append(fa)
        if not ts:
            return {"evidence_raw_count": len(rids), "fetched_at_min_iso": None, "fetched_at_max_iso": None}
        lo, hi = min(ts), max(ts)

        def _iso(dt: datetime) -> str:
            d = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
            return d.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        return {
            "evidence_raw_count": len(rids),
            "fetched_at_min_iso": _iso(lo),
            "fetched_at_max_iso": _iso(hi),
        }

    for row in rows:
        lt = row.get("link_type")
        if lt != "org.persona_belongs_to_handle":
            continue
        try:
            src = uuid.UUID(str(row.get("source_entity_id")))
            tgt = uuid.UUID(str(row.get("target_entity_id")))
        except (TypeError, ValueError):
            continue
        lo, hi, pk = _pair_key(src, tgt)
        fam = families.setdefault(
            pk,
            {
                "pair_key": pk,
                "source_entity_id": lo,
                "target_entity_id": hi,
                "by_rule_id": {},
                "distinct_evidence_raw_record_ids": set(),
                "by_connector": defaultdict(int),
                "rule_ids": set(),
            },
        )
        rid = str(row.get("rule_id") or "").strip() or "(none)"
        fam["rule_ids"].add(rid)
        br = fam["by_rule_id"].setdefault(
            rid,
            {
                "edge_count": 0,
                "evidence_raw_record_ids": set(),
                "by_connector": defaultdict(int),
            },
        )
        br["edge_count"] += 1
        evs = [int(x) for x in (row.get("evidence_raw_record_ids") or []) if isinstance(x, int)]
        for e in evs:
            br["evidence_raw_record_ids"].add(e)
            fam["distinct_evidence_raw_record_ids"].add(e)
            raw = raw_by_id.get(e)
            conn = (getattr(raw, "connector", None) or "unknown") if raw is not None else "raw_missing"
            ckey = str(conn).strip().lower() or "unknown"
            br["by_connector"][ckey] += 1
            fam["by_connector"][ckey] += 1

    out_families: list[dict[str, Any]] = []
    for pk in sorted(families.keys()):
        fam = families[pk]
        by_rule: dict[str, Any] = {}
        for rule_id in sorted(fam["by_rule_id"].keys()):
            block = fam["by_rule_id"][rule_id]
            rids_sorted = sorted(block["evidence_raw_record_ids"])
            bc = {k: block["by_connector"][k] for k in sorted(block["by_connector"].keys())}
            by_rule[rule_id] = {
                "edge_count": int(block["edge_count"]),
                "evidence_raw_record_ids": rids_sorted,
                "by_connector": bc,
                "temporal": _fetched_bounds(rids_sorted),
            }
        all_rids = sorted(fam["distinct_evidence_raw_record_ids"])
        top_bc = {k: fam["by_connector"][k] for k in sorted(fam["by_connector"].keys())}
        out_families.append(
            {
                "pair_key": pk,
                "source_entity_id": fam["source_entity_id"],
                "target_entity_id": fam["target_entity_id"],
                "distinct_rule_ids": sorted(fam["rule_ids"]),
                "rule_count": len(fam["rule_ids"]),
                "by_rule_id": by_rule,
                "distinct_evidence_raw_record_ids": all_rids,
                "by_connector": top_bc,
                "temporal": _fetched_bounds(all_rids),
            }
        )

    for fam in out_families:
        _attach_family_explainability(fam, raw_by_id=raw_by_id)

    multi_rule = sum(1 for f in out_families if f["rule_count"] >= 2)
    return {
        "accumulation_schema_version": ACCUMULATION_SCHEMA_VERSION,
        "candidate_row_input_count": len(rows),
        "pair_family_count": len(out_families),
        "pair_families_with_multiple_rules_count": multi_rule,
        "pair_families": out_families,
    }


def _attach_family_explainability(fam: dict[str, Any], *, raw_by_id: dict[int, Any]) -> None:
    """Mutates ``fam`` with deterministic explain fields (no scoring)."""
    lines: list[str] = []
    kinds_seen: set[str] = set()
    rtypes: set[str] = set()
    days: set[str] = set()
    for rid in fam.get("distinct_rule_ids") or []:
        mk = ACCUMULATION_MANIFEST_KIND_BY_RULE_ID.get(str(rid), "")
        if mk:
            kinds_seen.add(mk)
        expl = _EXPLAIN_LINE_BY_MANIFEST_KIND.get(mk)
        if expl and expl not in lines:
            lines.append(expl)
    for rid in sorted(fam.get("distinct_rule_ids") or []):
        blk = (fam.get("by_rule_id") or {}).get(rid) or {}
        n = int(blk.get("edge_count") or 0)
        if n > 0:
            mk = ACCUMULATION_MANIFEST_KIND_BY_RULE_ID.get(str(rid), "unknown")
            lines.append(f"Rule {rid} ({mk}): {n} candidate edge(s).")
    for raw_id in fam.get("distinct_evidence_raw_record_ids") or []:
        raw = raw_by_id.get(int(raw_id)) if isinstance(raw_id, int) else raw_by_id.get(raw_id)
        if raw is None:
            continue
        rt = getattr(raw, "resource_type", None)
        if isinstance(rt, str) and rt.strip():
            rtypes.add(rt.strip())
        fa = getattr(raw, "fetched_at", None)
        if isinstance(fa, datetime):
            d = fa if fa.tzinfo is not None else fa.replace(tzinfo=UTC)
            days.add(d.astimezone(UTC).date().isoformat())
    fam["manifest_kinds_distinct"] = sorted(kinds_seen)
    fam["distinct_resource_types"] = sorted(rtypes)
    fam["recurrence_calendar_day_count"] = len(days)
    fam["deterministic_explain_lines"] = sorted(set(lines))


def preview_top_pair_families(acc: dict[str, Any], *, limit: int = 12) -> dict[str, Any]:
    """Bounded, deterministic slice for replay summaries / control plane (stable sort)."""
    lim = max(1, min(int(limit), 50))
    fams: list[dict[str, Any]] = list(acc.get("pair_families") or [])

    def _total_edges(f: dict[str, Any]) -> int:
        br = f.get("by_rule_id") or {}
        return sum(int((br.get(rid) or {}).get("edge_count") or 0) for rid in br)

    fams.sort(key=lambda f: (-_total_edges(f), str(f.get("pair_key") or "")))
    return {
        "schema_version": "p04.continuity_pair_evidence_preview.v1",
        "limit": lim,
        "pair_families": fams[:lim],
        "pair_family_count_total": len(fams),
    }
