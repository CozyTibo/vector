"""Step 4 — Cross-work-item semantic / reference links (deterministic, no LLM)."""

from __future__ import annotations

import hashlib
import re

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    LinkBundle,
    LinkConfidence,
    LinkType,
    PerceptionRow,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)

# Tunable; lock with tests (implementation plan Step 4 — high only when above threshold).
JACCARD_HIGH = 0.40
JACCARD_MEDIUM = 0.24
JACCARD_LOW = 0.14
CROSS_SOURCE_BONUS = 0.08
MAX_ITEMS_FOR_LINKING = 120

_TICKET_RE = re.compile(r"\b([A-Z]{2,20}-\d+)\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def _norm_tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b) or 1
    return inter / uni


def _evidence_cross_hit_boost(
    wi: WorkItem,
    wj: WorkItem,
    tki: set[str],
    tkj: set[str],
    ex_extra: dict[str, str] | None,
) -> float:
    """If Step-3 text for (i) mentions tokens that show up in the other work item, small boost."""
    if not ex_extra:
        return 0.0
    s = 0.0
    e_i, e_j = ex_extra.get(wi.id, ""), ex_extra.get(wj.id, "")
    for t in _norm_tokens(e_i):
        if len(t) > 3 and t in tkj:
            s += 0.02
    for t in _norm_tokens(e_j):
        if len(t) > 3 and t in tki:
            s += 0.02
    return min(0.1, s)


def _ticket_ids(*parts: str) -> set[str]:
    blob = " ".join(p for p in parts if p)
    return {m.group(1).upper() for m in _TICKET_RE.finditer(blob)}


def _build_evidence_extra_by_work_item(evidence: EvidenceBundle) -> dict[str, str]:
    by_id: dict[str, list[str]] = {}
    for group in (evidence.action_items, evidence.blockers, evidence.decisions):
        for e in group:
            by_id.setdefault(e.source_work_item_id, []).append(
                f"{e.statement} {e.evidence}"
            )
    return {k: " ".join(v) for k, v in by_id.items()}


def _build_perception_extra_by_work_item(rows: list[PerceptionRow]) -> dict[str, str]:
    """Fold validated perception text into the same cross-item token surface as Step-3 evidence."""
    by_id: dict[str, list[str]] = {}
    for row in rows:
        parts = [row.statement, row.quote]
        if row.ambiguity_quote and row.ambiguity_quote.strip():
            parts.append(row.ambiguity_quote)
        if row.state_transition is not None:
            parts.append(row.state_transition.quote)
        if row.waits_on:
            parts.extend(row.waits_on)
        if row.blocked_by:
            parts.extend(row.blocked_by)
        chunk = " ".join(p for p in parts if p)
        by_id.setdefault(row.work_item_id, []).append(chunk)
    return {k: " ".join(v) for k, v in by_id.items()}


def _merge_extra_by_work_item(a: dict[str, str], b: dict[str, str]) -> dict[str, str]:
    keys = set(a) | set(b)
    out: dict[str, str] = {}
    for k in keys:
        merged = " ".join(p.strip() for p in (a.get(k, ""), b.get(k, "")) if p and p.strip()).strip()
        if merged:
            out[k] = merged
    return out


def _text_for(
    w: WorkItem, extra: dict[str, str] | None
) -> str:
    parts = [w.title, w.summary or ""]
    if extra and w.id in extra:
        parts.append(extra[w.id])
    return " ".join(p for p in parts if p)


def _link_id(a: str, b: str) -> str:
    lo, hi = (a, b) if a < b else (b, a)
    d = hashlib.sha1(f"link|{lo}|{hi}".encode("utf-8")).hexdigest()[:12]
    return f"link:{d}"


def _classify(
    s: float,
) -> LinkConfidence | None:
    if s >= JACCARD_HIGH:
        return "high"
    if s >= JACCARD_MEDIUM:
        return "medium"
    if s >= JACCARD_LOW:
        return "low"
    return None


def _score_and_type(
    wi: WorkItem,
    wj: WorkItem,
    tki: set[str],
    tkj: set[str],
) -> tuple[float, LinkType, float]:
    jacc = _jaccard(tki, tkj)
    ltype: LinkType = "semantic_match"
    k_i = _ticket_ids(wi.title, wi.summary or "")
    k_j = _ticket_ids(wj.title, wj.summary or "")
    shared_keys = k_i & k_j
    score = jacc
    if shared_keys:
        ltype = "shared_reference"
        # Same ticket key in both => strong but still bounded (must clear LOW+ without fake high Jacc)
        score = max(jacc, 0.52, min(1.0, jacc + 0.18))
    if wi.source != wj.source:
        score = min(1.0, score + CROSS_SOURCE_BONUS)
    return (score, ltype, jacc)


def _evidence_prose(
    w_lo: WorkItem,
    w_hi: WorkItem,
    t_lo: set[str],
    t_hi: set[str],
    jacc: float,
    shared_label: str = "",
) -> str:
    inter = t_lo & t_hi
    top = ", ".join(sorted(x for x in inter if len(x) > 2)[:10])
    extra = f" {shared_label}" if shared_label else ""
    return (
        f"{extra}jaccard={jacc:.3f} overlap={{{top or '—'}}} | "
        f'{w_lo.id}: "{_short(w_lo.title)}" | '
        f'{w_hi.id}: "{_short(w_hi.title)}"'
    )


def _short(t: str, m: int = 100) -> str:
    t = t.strip()
    if len(t) <= m:
        return t
    return t[: m - 1] + "…"


def link_work_items(
    bundle: WorkItemBundle,
    *,
    link_input: CoordinationLinkInputBundle | None = None,
) -> LinkBundle:
    """Propose work-item links: token Jaccard, cross-source nudge, shared NEX-KEY detection.

    §6 Step 12: pass ``CoordinationLinkInputBundle(evidence=…, perception_rows=…)`` so validated
    ``PerceptionRow`` text is merged with Step-3 evidence for cross-item token hits (never raw LLM JSON).
    """
    ex_extra: dict[str, str] = {}
    perception_used_count = 0
    if link_input is not None:
        ev = link_input.evidence
        if ev.run_id == bundle.run_id and ev.tenant_id == bundle.tenant_id:
            evidence_extra = _build_evidence_extra_by_work_item(ev)
            perception_extra = _build_perception_extra_by_work_item(link_input.perception_rows)
            ex_extra = _merge_extra_by_work_item(evidence_extra, perception_extra)
            perception_used_count = len(link_input.perception_rows)

    items = sorted(bundle.items, key=lambda x: x.id)
    work_items_capped = 0
    if len(items) > MAX_ITEMS_FOR_LINKING:
        items = items[:MAX_ITEMS_FOR_LINKING]
        work_items_capped = MAX_ITEMS_FOR_LINKING

    texts = [_text_for(w, ex_extra) for w in items]
    toks = [_norm_tokens(t) for t in texts]

    best: dict[tuple[str, str], WorkItemLink] = {}
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            wi, wj = items[i], items[j]
            tki, tkj = toks[i], toks[j]
            score, ltype, jacc = _score_and_type(wi, wj, tki, tkj)
            hit = _evidence_cross_hit_boost(wi, wj, tki, tkj, ex_extra)
            score = min(1.0, score + hit)
            conf = _classify(score)
            if conf is None:
                continue
            a, b = (wi.id, wj.id) if wi.id < wj.id else (wj.id, wi.id)
            w_lo = wi if wi.id < wj.id else wj
            w_hi = wj if wi.id < wj.id else wi
            t_lo = tki if wi.id < wj.id else tkj
            t_hi = tkj if wi.id < wj.id else tki
            if ltype == "shared_reference":
                kx = _ticket_ids(wi.title, wi.summary or "") & _ticket_ids(
                    wj.title, wj.summary or ""
                )
                sh_lbl = f"shared_keys={sorted(kx)} " if kx else "shared_key "
            else:
                sh_lbl = ""
            ev = _evidence_prose(w_lo, w_hi, t_lo, t_hi, jacc, sh_lbl)
            method_parts = ["token_jaccard", "cross_source", "ticket_keys"]
            if hit:
                method_parts.append("cross_item_text_hits")
            if perception_used_count:
                method_parts.append("perception_rows")
            rec = WorkItemLink(
                id=_link_id(a, b),
                from_work_item_id=a,
                to_work_item_id=b,
                link_type=ltype,
                confidence=conf,
                similarity=round(min(1.0, score), 4),
                method="+".join(method_parts),
                evidence=ev,
            )
            k2 = (a, b)
            if k2 not in best or rec.similarity > best[k2].similarity:
                best[k2] = rec

    links = sorted(
        best.values(), key=lambda x: (-x.similarity, x.from_work_item_id, x.to_work_item_id)
    )
    return LinkBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        links=links,
        work_items_capped=work_items_capped,
        perception_rows_used_for_linking=perception_used_count,
    )