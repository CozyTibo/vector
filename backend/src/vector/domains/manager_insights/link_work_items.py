"""Step 4 — Cross-work-item semantic / reference links (deterministic, no LLM)."""

from __future__ import annotations

import hashlib
import re

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    LinkBundle,
    LinkConfidence,
    LinkType,
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
    evidence: EvidenceBundle | None = None,
) -> LinkBundle:
    """Propose work-item links: token Jaccard, cross-source nudge, shared NEX-KEY detection."""
    ex_extra: dict[str, str] = {}
    if (
        evidence is not None
        and evidence.run_id == bundle.run_id
        and evidence.tenant_id == bundle.tenant_id
    ):
        ex_extra = _build_evidence_extra_by_work_item(evidence)

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
            rec = WorkItemLink(
                id=_link_id(a, b),
                from_work_item_id=a,
                to_work_item_id=b,
                link_type=ltype,
                confidence=conf,
                similarity=round(min(1.0, score), 4),
                method="token_jaccard+cross_source+ticket_keys+evidence_hits"
                if hit
                else "token_jaccard+cross_source+ticket_keys",
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
    )