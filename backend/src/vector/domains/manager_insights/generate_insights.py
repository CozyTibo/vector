"""Step 8 — LLM insights with strict schema + grounding validation."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, get_args

from openai import APIError, OpenAI
from pydantic import ValidationError

from vector.contracts.manager_insights import InsightConfidence, InsightPriority, InsightV0
from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    EvidenceItem,
    GapBundle,
    GapItem,
    InsightBundleDebug,
    InsightItemDebug,
    InsightPrimaryEntityItem,
    InterpretationBundleDebug,
    KeyAchievementsBundleDebug,
    RawHighlightsBundleDebug,
    RejectedInsightDebug,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
)
from vector.openai_chat_params import (
    max_completion_tokens_for_manager_insights_insights,
    temperature_for_chat_model,
)
from vector.settings import Settings

_SIGNAL_IDS = (
    "delivery_strength",
    "urgent_pressure",
    "expectation_coverage",
    "follow_through",
    "blocker_visibility",
    "repeated_discussion_present",
    "execution_momentum",
    "documentation_linkage",
    "focus",
    "collaboration_intensity",
    "support_pattern",
    "feedback_reception",
    "coordination_role",
    "interaction_friction",
)

_INSIGHT_CONFIDENCE: tuple[str, ...] = get_args(InsightConfidence)
_INSIGHT_PRIORITY: tuple[str, ...] = get_args(InsightPriority)
_LLM_DEBUG_MAX_ASSISTANT_CHARS = 48_000


@dataclass
class _LlmMeta:
    generated_via: str
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class _LlmResponse:
    raw_text: str
    raw_text_truncated: bool
    parsed_insight_rows: int
    items: list[dict[str, Any]]
    response_level_error: str | None


def _chat_message_text(message: Any) -> str:
    c = getattr(message, "content", None)
    if c is None:
        return ""
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for p in c:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text") or ""))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return str(c)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# Gap `description` strings from compute_gaps.py — LLMs often paste these instead of Step-3 quotes.
_GAP_DESCRIPTION_BOILERPLATES_NORM: frozenset[str] = frozenset(
    _normalize(x)
    for x in (
        "Blocker is mentioned but not linked to a tracked issue/PR.",
        "Action item has no linked closed issue or merged PR in tracked systems.",
        "Discussion evidence is not linked to any tracked issue or PR.",
        "Document has no medium/high-confidence link to tracked issue or PR.",
    )
)

_LINEAR_ISSUE_TICKET_RE = re.compile(r"^linear:issue:([A-Z][A-Z0-9]{1,6}-\d+)$")


def _resolve_bundle_work_item_id(ref: str, items: list[WorkItem]) -> str | None:
    allowed = {w.id for w in items}
    ref = ref.strip()
    if ref in allowed:
        return ref
    m = _LINEAR_ISSUE_TICKET_RE.match(ref)
    if not m:
        return None
    ident = m.group(1)
    for w in items:
        if w.source != "linear" or w.type != "issue":
            continue
        sr = w.source_ref.get("identifier") if isinstance(w.source_ref, dict) else None
        if sr == ident:
            return w.id
    return None


def _observation_covers_work_item(wid: str, observation: str, wi_by_id: dict[str, WorkItem]) -> bool:
    if wid in observation:
        return True
    w = wi_by_id.get(wid)
    if w is None:
        return False
    if w.source == "linear" and w.type == "issue":
        ident = w.source_ref.get("identifier") if isinstance(w.source_ref, dict) else None
        if isinstance(ident, str) and ident and ident in observation:
            return True
    return False


def _insight_evidence_is_gap_boilerplate(evidence_strings: list[str]) -> bool:
    return bool(evidence_strings) and all(
        _normalize(e) in _GAP_DESCRIPTION_BOILERPLATES_NORM for e in evidence_strings
    )


def _insight_narrative_text(c: InsightV0) -> str:
    """LLMs often put gap ids only in interpretation; anchor checks use the full narrative."""
    return f"{c.observation}\n{c.interpretation}\n{c.implication}"


def _merge_supporting_from_cited_evidence(
    primary_ids: list[str],
    supporting_ids: list[str],
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
    wi_list: list[WorkItem],
    allowed_work_item_ids: set[str],
) -> list[str]:
    """Ensure each cited evidence row's source work item is listed if it exists in Step-2."""
    primary_set = set(primary_ids)
    out: list[str] = []
    seen: set[str] = set()
    for w in supporting_ids:
        if w not in seen:
            seen.add(w)
            out.append(w)
    for eid in evidence_ids:
        row = evidence_by_id.get(eid)
        if row is None or not row.source_work_item_id:
            continue
        raw_src = row.source_work_item_id
        resolved = _resolve_bundle_work_item_id(raw_src, wi_list)
        wid = resolved if resolved is not None else raw_src
        if wid not in allowed_work_item_ids or wid in primary_set or wid in seen:
            continue
        seen.add(wid)
        out.append(wid)
    return out


def _extract_json_object(text: str) -> dict[str, Any] | None:
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _evidence_in_corpus(evidence_text: str, corpus: list[str]) -> bool:
    q = _normalize(evidence_text)
    if not q:
        return False
    for source in corpus:
        if q in _normalize(source):
            return True
    return False


def _evidence_in_corpus_insight(evidence_text: str, corpus: list[str]) -> bool:
    """Quote ⊆ corpus row, or a substantive corpus fragment ⊆ quote (LLM paraphrase)."""
    q = _normalize(evidence_text)
    if not q:
        return False
    for source in corpus:
        ns = _normalize(source)
        if not ns:
            continue
        if q in ns:
            return True
        if len(ns) >= 14 and ns in q:
            return True
    return False


def _insight_evidence_allowed_paraphrase(
    ev: str,
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
) -> bool:
    """Accept short gap-style summaries when evidence_ids ground to matching Step-3 kinds."""
    q = _normalize(ev)
    if not q:
        return False
    kinds = {evidence_by_id[e].kind for e in evidence_ids if evidence_by_id.get(e)}
    if "blocker" in kinds:
        needles = (
            "not linked to a tracked issue",
            "not linked to a tracked issue/pr",
            "blocker is mentioned but not linked",
            "no tracked issue",
            "no tracked owner",
            "not assigned owner",
        )
        if any(n in q for n in needles):
            return True
    if "action_item" in kinds:
        needles = (
            "no linked closed issue",
            "merged pr in tracked systems",
            "not linked to tracked",
            "discussion evidence is not linked",
            "deferring creating tracked",
        )
        if any(n in q for n in needles):
            return True
    return False


def _insight_quote_verifies(
    ev: str,
    corpus: list[str],
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
) -> bool:
    if _evidence_in_corpus_insight(ev, corpus):
        return True
    return _insight_evidence_allowed_paraphrase(ev, evidence_ids, evidence_by_id)


def _unverifiable_evidence_strings(
    evidence: list[str], corpus: list[str], *, max_examples: int = 3
) -> list[str]:
    bad: list[str] = []
    for ev in evidence:
        if not isinstance(ev, str):
            bad.append("<non-string evidence>")
            continue
        if _evidence_in_corpus(ev, corpus):
            continue
        t = (ev or "").replace("\n", " ").strip()
        if len(t) > 140:
            t = t[:140] + "..."
        bad.append(t or "<empty evidence>")
        if len(bad) >= max_examples:
            break
    return bad


def _unverifiable_insight_evidence_strings(
    evidence: list[str],
    corpus: list[str],
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
    *,
    max_examples: int = 3,
) -> list[str]:
    bad: list[str] = []
    for ev in evidence:
        if not isinstance(ev, str):
            bad.append("<non-string evidence>")
            continue
        if _insight_quote_verifies(ev, corpus, evidence_ids, evidence_by_id):
            continue
        t = (ev or "").replace("\n", " ").strip()
        if len(t) > 140:
            t = t[:140] + "..."
        bad.append(t or "<empty evidence>")
        if len(bad) >= max_examples:
            break
    return bad


def _iter_evidence_items(evidence: EvidenceBundle) -> list[EvidenceItem]:
    return [*evidence.action_items, *evidence.blockers, *evidence.decisions]


def _evidence_item_by_id(evidence: EvidenceBundle) -> dict[str, EvidenceItem]:
    return {e.id: e for e in _iter_evidence_items(evidence)}


def _cited_evidence_corpus(evidence: EvidenceBundle, evidence_ids: list[str]) -> list[str]:
    by_id = _evidence_item_by_id(evidence)
    rows: list[str] = []
    for eid in evidence_ids:
        item = by_id.get(eid)
        if item is None:
            continue
        rows.append(item.statement)
        rows.append(item.evidence)
    return [r for r in rows if isinstance(r, str) and r.strip()]


def _cited_evidence_corpus_for_insights(
    evidence: EvidenceBundle,
    evidence_ids: list[str],
    gaps: GapBundle,
) -> list[str]:
    """Step-3 row text plus deterministic gap descriptions that cite those evidence ids."""
    rows = list(_cited_evidence_corpus(evidence, evidence_ids))
    by_id = _evidence_item_by_id(evidence)
    linked_desc: set[str] = set()
    pointer_keys = ("blocker_item_ids", "action_item_ids", "evidence_item_ids")
    for eid in evidence_ids:
        if by_id.get(eid) is None:
            continue
        for g in gaps.gaps:
            matched = False
            for k in pointer_keys:
                vals = g.evidence_pointers.get(k)
                if isinstance(vals, list) and eid in vals:
                    matched = True
                    break
            if not matched:
                continue
            d = (g.description or "").strip()
            if d and d not in linked_desc:
                linked_desc.add(d)
                rows.append(d)
    return rows


def _resolve_insight_evidence_strings(
    evidence_strings: list[str],
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
) -> list[str]:
    """LLMs sometimes put evidence row ids in `evidence`[]; map those to quotable row text."""
    allowed = set(evidence_ids)
    out: list[str] = []
    for ev in evidence_strings:
        if isinstance(ev, str) and ev in allowed:
            row = evidence_by_id.get(ev)
            if row is None:
                out.append(ev)
                continue
            quote = (row.statement or "").strip() or (row.evidence or "").strip()
            out.append(quote[:1200] if quote else ev)
            continue
        out.append(ev)
    return out


_WORK_POINTER_KEYS = frozenset(
    {
        "source_work_item_ids",
        "linked_execution_item_ids",
        "document_work_item_ids",
    }
)
_EVID_POINTER_KEYS = frozenset({"action_item_ids", "blocker_item_ids", "evidence_item_ids"})


def _gap_pointer_ids(g: GapItem) -> tuple[list[str], list[str]]:
    work_ids: list[str] = []
    ev_ids: list[str] = []
    for k, vals in g.evidence_pointers.items():
        if not isinstance(vals, list):
            continue
        for x in vals:
            if not isinstance(x, str):
                continue
            if k in _EVID_POINTER_KEYS:
                ev_ids.append(x)
            elif k in _WORK_POINTER_KEYS or k not in _EVID_POINTER_KEYS:
                work_ids.append(x)
    return sorted(set(work_ids)), sorted(set(ev_ids))


def _gap_sort_band(g: GapItem) -> int:
    if g.type in ("expected_not_executed", "discussed_not_linked_to_work"):
        return 0
    if g.type == "blocker_not_tracked":
        return 1
    return 3


def _build_insight_candidates(
    gaps: GapBundle,
    evidence: EvidenceBundle,
    raw_highlights: RawHighlightsBundleDebug,
) -> list[dict[str, Any]]:
    """Phase 1 — deterministic execution-failure candidates (no LLM)."""
    out: list[dict[str, Any]] = []
    for g in gaps.gaps:
        wis, eids = _gap_pointer_ids(g)
        out.append(
            {
                "candidate_id": f"gap:{g.id}",
                "source_kind": "gap",
                "gap_id": g.id,
                "gap_type": g.type,
                "gap_description": g.description,
                "related_work_item_ids": wis,
                "source_evidence_item_ids": eids,
            }
        )
    for b in evidence.blockers:
        out.append(
            {
                "candidate_id": f"blocker:{b.id}",
                "source_kind": "blocker",
                "gap_ids": [],
                "blocker_evidence_id": b.id,
                "blocker_statement": b.statement,
                "related_work_item_ids": sorted({b.source_work_item_id, *b.linked_work_items}),
                "source_evidence_item_ids": [b.id],
            }
        )
    for h in raw_highlights.items:
        if len(h.sources) >= 2 or any(
            w in h.text.lower() for w in ("repeated", "multiple", "distinct", "several")
        ):
            out.append(
                {
                    "candidate_id": f"highlight:{h.id}",
                    "source_kind": "highlight",
                    "highlight_id": h.id,
                    "highlight_text": h.text,
                    "related_work_item_ids": list(h.sources),
                    "source_evidence_item_ids": [],
                }
            )

    def sort_key(c: dict[str, Any]) -> tuple[int, str]:
        sk = c.get("source_kind")
        if sk == "gap":
            gid = str(c.get("gap_id", ""))
            g = next((x for x in gaps.gaps if x.id == gid), None)
            band = _gap_sort_band(g) if g else 9
            return (band, gid)
        if sk == "blocker":
            return (2, str(c.get("candidate_id", "")))
        return (3, str(c.get("candidate_id", "")))

    out.sort(key=sort_key)
    return out[:28]


def _serialize_insight_llm_payload(
    candidates: list[dict[str, Any]],
    interpretations: InterpretationBundleDebug,
    evidence: EvidenceBundle,
    gaps: GapBundle,
    raw_highlights: RawHighlightsBundleDebug,
    work_items: WorkItemBundle,
) -> str:
    wi_rows = [
        {
            "id": w.id,
            "title": w.title,
            "project": w.project,
            "type": w.type,
            "source": w.source,
            "source_ref": w.source_ref,
        }
        for w in work_items.items[:48]
    ]
    payload = {
        "insight_candidates": candidates,
        "interpretations_for_optional_links": [
            {"id": x.id, "description": x.description} for x in interpretations.items[:12]
        ],
        "allowed_interpretation_ids_for_based_on_interpretations": [
            x.id for x in interpretations.items[:12]
        ],
        "allowed_signal_ids_for_based_on_signals": list(_SIGNAL_IDS),
        "allowed_work_item_ids": [w.id for w in work_items.items[:200]],
        "allowed_evidence_item_ids": [e.id for e in _iter_evidence_items(evidence)][:200],
        "allowed_gap_ids": [g.id for g in gaps.gaps[:80]],
        "allowed_blocker_evidence_ids": [b.id for b in evidence.blockers[:80]],
        "allowed_highlight_ids": [h.id for h in raw_highlights.items[:80]],
        "work_items_for_grounding": wi_rows,
    }
    return json.dumps(payload, ensure_ascii=False)


def _insight_observation_vague(observation: str) -> bool:
    o = observation.lower()
    if re.search(r"\b[A-Z][A-Z0-9]{1,6}-\d+\b", observation):
        return False
    if "gap:" in observation:
        return False
    if re.search(r"\b[a-z]+:[a-z0-9_:-]{4,}\b", observation):
        return False
    needles = (
        "the team ",
        "team is blocked",
        "external dependencies",
        "the process",
        "things are",
        "coordination is",
        "execution quality",
    )
    return any(n in o for n in needles)


def _validate_insights(
    items: list[dict[str, Any]],
    *,
    interpretation_ids: set[str],
    work_items: WorkItemBundle,
    evidence: EvidenceBundle,
    gaps: GapBundle,
    raw_highlights: RawHighlightsBundleDebug,
) -> tuple[list[InsightItemDebug], list[RejectedInsightDebug]]:
    out: list[InsightItemDebug] = []
    rejected: list[RejectedInsightDebug] = []
    seen_ids: set[str] = set()
    allowed_work_item_ids = {w.id for w in work_items.items}
    allowed_evidence_ids = {e.id for e in _iter_evidence_items(evidence)}
    evidence_by_id = _evidence_item_by_id(evidence)

    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            rejected.append(
                RejectedInsightDebug(index=i, reason="insight row is not a JSON object", raw={})
            )
            continue
        try:
            canonical = InsightV0.model_validate(raw)
        except ValidationError as e:
            rejected.append(RejectedInsightDebug(index=i, reason=f"schema: {e}", raw=raw))
            continue
        except Exception as e:  # pragma: no cover (defensive)
            rejected.append(RejectedInsightDebug(index=i, reason=f"schema: {e}", raw=raw))
            continue

        if canonical.id in seen_ids:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"duplicate id {canonical.id!r}",
                    raw=raw,
                )
            )
            continue
        invalid_interp_refs = [
            ref for ref in canonical.based_on_interpretations if ref not in interpretation_ids
        ]
        if invalid_interp_refs:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"invalid based_on_interpretations refs: {invalid_interp_refs!r}",
                    raw=raw,
                )
            )
            continue
        invalid_signals = [sig for sig in canonical.based_on_signals if sig not in _SIGNAL_IDS]
        if invalid_signals:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"invalid based_on_signals: {invalid_signals!r} (not in allowlist)",
                    raw=raw,
                )
            )
            continue

        wi_list = list(work_items.items)
        wi_by_id = {w.id: w for w in wi_list}

        primary_resolved: list[str] = []
        primary_unresolved: str | None = None
        for wid in canonical.primary_work_item_ids:
            r = _resolve_bundle_work_item_id(wid, wi_list)
            if r is None:
                primary_unresolved = wid
                break
            primary_resolved.append(r)
        if primary_unresolved is not None:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"primary_work_item_ids not in Step-2 bundle: {[primary_unresolved]!r}",
                    raw=raw,
                )
            )
            continue

        supporting_resolved: list[str] = []
        for wid in canonical.supporting_work_item_ids:
            r = _resolve_bundle_work_item_id(wid, wi_list)
            if r is not None:
                supporting_resolved.append(r)
        supporting_augmented = _merge_supporting_from_cited_evidence(
            primary_resolved,
            supporting_resolved,
            list(canonical.evidence_ids),
            evidence_by_id,
            wi_list,
            allowed_work_item_ids,
        )
        canonical = canonical.model_copy(
            update={
                "primary_work_item_ids": primary_resolved,
                "supporting_work_item_ids": supporting_augmented,
            }
        )

        gap_ids_allowed = {g.id for g in gaps.gaps}
        highlight_ids_allowed = {h.id for h in raw_highlights.items}
        blocker_ids_allowed = {b.id for b in evidence.blockers}
        bad_gap_refs = [g for g in canonical.based_on_gaps if g not in gap_ids_allowed]
        if bad_gap_refs:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"invalid based_on_gaps: {bad_gap_refs!r}",
                    raw=raw,
                )
            )
            continue
        bad_hl_refs = [h for h in canonical.based_on_highlights if h not in highlight_ids_allowed]
        if bad_hl_refs:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"invalid based_on_highlights: {bad_hl_refs!r}",
                    raw=raw,
                )
            )
            continue
        bad_bl_refs = [b for b in canonical.based_on_blockers if b not in blocker_ids_allowed]
        if bad_bl_refs:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"invalid based_on_blockers: {bad_bl_refs!r}",
                    raw=raw,
                )
            )
            continue
        blocker_row_invalid = False
        for bid in canonical.based_on_blockers:
            row = evidence_by_id.get(bid)
            if row is None or row.kind != "blocker":
                rejected.append(
                    RejectedInsightDebug(
                        index=i,
                        reason=f"based_on_blockers id {bid!r} is not a blocker evidence row",
                        raw=raw,
                    )
                )
                blocker_row_invalid = True
                break
        if blocker_row_invalid:
            continue

        narrative = _insight_narrative_text(canonical)
        effective_insight_highlights = [h for h in canonical.based_on_highlights if h in narrative]
        if canonical.based_on_highlights:
            if (
                not effective_insight_highlights
                and not canonical.based_on_gaps
                and not canonical.based_on_blockers
            ):
                rejected.append(
                    RejectedInsightDebug(
                        index=i,
                        reason="based_on_highlights ids must appear verbatim in insight narrative when "
                        "they are the only grounding (gaps/blockers empty)",
                        raw=raw,
                    )
                )
                continue
            if len(effective_insight_highlights) != len(canonical.based_on_highlights):
                canonical = canonical.model_copy(update={"based_on_highlights": effective_insight_highlights})

        obs_anchor_failed: str | None = None
        for gid in canonical.based_on_gaps:
            if gid not in narrative:
                obs_anchor_failed = (
                    "insight narrative (observation/interpretation/implication) must contain cited gap id "
                    f"substring {gid!r}"
                )
                break
        if obs_anchor_failed is None:
            for hid in canonical.based_on_highlights:
                if hid not in narrative:
                    obs_anchor_failed = (
                        "insight narrative (observation/interpretation/implication) must contain cited "
                        f"highlight id substring {hid!r}"
                    )
                    break
        if obs_anchor_failed is None:
            for bid in canonical.based_on_blockers:
                row = evidence_by_id.get(bid)
                if row is None:
                    continue
                if bid not in narrative and row.source_work_item_id not in narrative:
                    obs_anchor_failed = (
                        "insight narrative (observation/interpretation/implication) must contain each "
                        f"based_on_blockers id or that row's source_work_item_id; missing anchor for {bid!r}"
                    )
                    break
        if obs_anchor_failed is not None:
            rejected.append(RejectedInsightDebug(index=i, reason=obs_anchor_failed, raw=raw))
            continue

        if _insight_observation_vague(canonical.observation):
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason="observation reads as generic/vague without concrete anchors",
                    raw=raw,
                )
            )
            continue

        bad_wi = [wid for wid in canonical.primary_work_item_ids if wid not in allowed_work_item_ids]
        if bad_wi:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"primary_work_item_ids not in Step-2 bundle: {bad_wi!r}",
                    raw=raw,
                )
            )
            continue
        bad_sup = [
            wid for wid in canonical.supporting_work_item_ids if wid not in allowed_work_item_ids
        ]
        if bad_sup:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"supporting_work_item_ids not in Step-2 bundle: {bad_sup!r}",
                    raw=raw,
                )
            )
            continue

        missing_eids = [eid for eid in canonical.evidence_ids if eid not in allowed_evidence_ids]
        if missing_eids:
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason=f"evidence_ids not in Step-3 bundle: {missing_eids!r}",
                    raw=raw,
                )
            )
            continue

        cited_corpus = _cited_evidence_corpus_for_insights(
            evidence, list(canonical.evidence_ids), gaps
        )
        evidence_resolved = _resolve_insight_evidence_strings(
            list(canonical.evidence), list(canonical.evidence_ids), evidence_by_id
        )
        eid_list = list(canonical.evidence_ids)
        corpus_ok = all(
            _insight_quote_verifies(ev, cited_corpus, eid_list, evidence_by_id)
            for ev in evidence_resolved
        )
        if not corpus_ok and _insight_evidence_is_gap_boilerplate(evidence_resolved):
            fallback_quotes: list[str] = []
            for eid in canonical.evidence_ids:
                row = evidence_by_id.get(eid)
                if row is None:
                    continue
                q = (row.statement or row.evidence or "").strip()
                if q:
                    fallback_quotes.append(q)
            if fallback_quotes:
                evidence_resolved = fallback_quotes
                corpus_ok = all(
                    _insight_quote_verifies(ev, cited_corpus, eid_list, evidence_by_id)
                    for ev in evidence_resolved
                )
        if corpus_ok and _insight_evidence_is_gap_boilerplate(evidence_resolved):
            row_quotes: list[str] = []
            for eid in canonical.evidence_ids:
                row = evidence_by_id.get(eid)
                if row is None:
                    continue
                q = (row.statement or row.evidence or "").strip()
                if q:
                    row_quotes.append(q)
            if row_quotes:
                evidence_resolved = row_quotes
        if not corpus_ok:
            bad = _unverifiable_insight_evidence_strings(
                evidence_resolved, cited_corpus, eid_list, evidence_by_id
            )
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason="evidence quotes must be verifiable against cited evidence_ids rows only: "
                    + "; ".join(bad),
                    raw=raw,
                )
            )
            continue

        obs_grounding_failed: str | None = None
        for wid in canonical.primary_work_item_ids:
            if not _observation_covers_work_item(wid, narrative, wi_by_id):
                obs_grounding_failed = (
                    "insight narrative must contain primary work item id substring "
                    f"{wid!r} (or Linear identifier when id is canonical)"
                )
                break
        if obs_grounding_failed is None:
            for ent in canonical.primary_entities:
                if ent.name not in narrative:
                    obs_grounding_failed = (
                        "insight narrative must contain each primary_entities.name as substring; "
                        f"missing {ent.name!r}"
                    )
                    break
        if obs_grounding_failed is not None:
            rejected.append(
                RejectedInsightDebug(index=i, reason=obs_grounding_failed, raw=raw)
            )
            continue

        allowed_wi_refs = set(canonical.primary_work_item_ids) | set(
            canonical.supporting_work_item_ids
        )
        ev_link_failed: str | None = None
        for eid in canonical.evidence_ids:
            ev_row = evidence_by_id.get(eid)
            if ev_row is None:
                continue
            if ev_row.source_work_item_id not in allowed_wi_refs:
                ev_link_failed = (
                    f"evidence_id {eid!r} source_work_item_id {ev_row.source_work_item_id!r} "
                    "must appear in primary_work_item_ids or supporting_work_item_ids"
                )
                break
        if ev_link_failed is not None:
            rejected.append(RejectedInsightDebug(index=i, reason=ev_link_failed, raw=raw))
            continue

        seen_ids.add(canonical.id)
        out.append(
            InsightItemDebug(
                id=canonical.id,
                observation=canonical.observation,
                interpretation=canonical.interpretation,
                implication=canonical.implication,
                evidence=evidence_resolved,
                evidence_ids=list(canonical.evidence_ids),
                based_on_interpretations=list(canonical.based_on_interpretations),
                based_on_signals=list(canonical.based_on_signals),
                primary_work_item_ids=list(canonical.primary_work_item_ids),
                supporting_work_item_ids=list(canonical.supporting_work_item_ids),
                primary_entities=[
                    InsightPrimaryEntityItem(name=e.name, kind=e.kind) for e in canonical.primary_entities
                ],
                based_on_gaps=list(canonical.based_on_gaps),
                based_on_blockers=list(canonical.based_on_blockers),
                based_on_highlights=list(canonical.based_on_highlights),
                confidence=canonical.confidence,
                priority=canonical.priority,
            )
        )

    return out, rejected


def _primary_entities_for_work_item(wi: WorkItem) -> list[InsightPrimaryEntityItem]:
    if getattr(wi, "project", None) and str(wi.project).strip():
        return [InsightPrimaryEntityItem(name=str(wi.project).strip(), kind="project")]
    title = (getattr(wi, "title", None) or wi.id or "Work item").strip()
    return [InsightPrimaryEntityItem(name=title[:160], kind="feature")]


def _fallback_insights(
    candidates: list[dict[str, Any]],
    interpretations: InterpretationBundleDebug,
    work_items: WorkItemBundle,
    evidence: EvidenceBundle,
) -> list[InsightItemDebug]:
    """Phase 1 candidates → deterministic insight rows (no LLM)."""
    wi_by_id = {w.id: w for w in work_items.items}
    ev_by_id = _evidence_item_by_id(evidence)
    out: list[InsightItemDebug] = []
    interp0 = interpretations.items[0].id if interpretations.items else None

    def pick_primary_wid(c: dict[str, Any]) -> str | None:
        for wid in c.get("related_work_item_ids") or []:
            if isinstance(wid, str) and wid in wi_by_id:
                return wid
        return None

    def pick_evidence_id(c: dict[str, Any], primary_wid: str | None) -> str | None:
        for eid in c.get("source_evidence_item_ids") or []:
            if isinstance(eid, str) and eid in ev_by_id:
                return eid
        if primary_wid:
            for ev in _iter_evidence_items(evidence):
                if ev.source_work_item_id == primary_wid:
                    return ev.id
        return None

    idx = 0
    for c in candidates:
        primary_wid = pick_primary_wid(c)
        if primary_wid is None:
            continue
        wi = wi_by_id[primary_wid]
        entities = _primary_entities_for_work_item(wi)
        ev_id = pick_evidence_id(c, primary_wid)
        if ev_id is None:
            continue
        ev_row = ev_by_id[ev_id]
        based_on_gaps: list[str] = []
        based_on_blockers: list[str] = []
        based_on_highlights: list[str] = []
        sk = c.get("source_kind")
        if sk == "gap":
            gid = str(c.get("gap_id", ""))
            based_on_gaps = [gid] if gid else []
            summary = str(c.get("gap_description", ""))
            observation = f"{gid} — {primary_wid} — {summary}"
            prio: InsightPriority = (
                "high"
                if c.get("gap_type")
                in ("expected_not_executed", "discussed_not_linked_to_work", "blocker_not_tracked")
                else "medium"
            )
            sigs = ["follow_through", "expectation_coverage"]
        elif sk == "blocker":
            bid = str(c.get("blocker_evidence_id", ""))
            based_on_blockers = [bid] if bid else []
            summary = str(c.get("blocker_statement", ""))
            observation = f"{bid} — {primary_wid} — {summary}"
            prio = "high"
            sigs = ["blocker_visibility", "interaction_friction"]
        elif sk == "highlight":
            hid = str(c.get("highlight_id", ""))
            based_on_highlights = [hid] if hid else []
            summary = str(c.get("highlight_text", ""))
            observation = f"{hid} — {primary_wid} — {summary}"
            prio = "medium"
            sigs = ["repeated_discussion_present", "interaction_friction"]
        else:
            continue

        quotes = [s for s in (ev_row.statement, ev_row.evidence) if isinstance(s, str) and s.strip()][:3]
        supporting = [
            x
            for x in (c.get("related_work_item_ids") or [])
            if isinstance(x, str) and x in wi_by_id and x != primary_wid
        ][:5]
        idx += 1
        out.append(
            InsightItemDebug(
                id=f"insight_fallback_{idx}",
                observation=observation,
                interpretation=(
                    f"Execution risk from {sk} candidate {c.get('candidate_id')}: {summary[:200]}"
                ),
                implication="Assign an owner and link tracking artifacts so closure is visible.",
                evidence=quotes,
                evidence_ids=[ev_id],
                based_on_interpretations=[interp0] if interp0 else [],
                based_on_signals=sigs,
                primary_work_item_ids=[primary_wid],
                supporting_work_item_ids=supporting,
                primary_entities=entities,
                based_on_gaps=based_on_gaps,
                based_on_blockers=based_on_blockers,
                based_on_highlights=based_on_highlights,
                confidence="medium",
                priority=prio,
            )
        )
        if len(out) >= 5:
            break

    return out[:5]


def _call_llm(settings: Settings, prompt_json: str) -> tuple[_LlmResponse, _LlmMeta]:
    started = time.perf_counter()
    client = OpenAI(api_key=settings.openai_api_key)

    conf_list = ", ".join(_INSIGHT_CONFIDENCE)
    priority_list = ", ".join(_INSIGHT_PRIORITY)
    signal_ids_list = ", ".join(_SIGNAL_IDS)
    system = (
        "You explain PRE-SELECTED execution failures only. Output strict JSON, no markdown. "
        "Context contains insight_candidates (deterministic, no invention) plus work_items and allowlists. "
        "Do NOT summarize signals; use candidates as the primary facts. "
        f"Each item's \"confidence\" MUST be one of: {conf_list}. "
        f"Each item's \"priority\" MUST be one of: {priority_list}. "
        f"\"based_on_signals\" MUST be a subset of: {signal_ids_list} (supporting only; may be empty). "
        "\"based_on_interpretations\" ids MUST be from allowed_interpretation_ids (or []). "
        "MANDATORY: non-empty based_on_gaps (subset of allowed_gap_ids) OR based_on_blockers (blocker evidence "
        "ids from allowed_blocker_evidence_ids) OR based_on_highlights (subset of allowed_highlight_ids); "
        "observation MUST include every cited gap id, highlight id, and each blocker id OR that row's "
        "source_work_item_id as literal substrings. "
        "Also include primary_work_item_ids, evidence_ids, primary_entities as before. "
        "BAD: \"The team is blocked on external dependencies.\" "
        "GOOD: \"NEX-105 is blocked on InfoSec approval with no assigned owner, preventing release\" "
        "(use real ids from candidates/work_items). "
        "Each \"evidence\" string MUST be a verbatim excerpt from the Step-3 evidence row's `statement` "
        "or `evidence` field for one of the ids in evidence_ids (do not put raw ids like blocker:... "
        "into evidence[] — ids belong only in evidence_ids). "
        "Schema: {\"insights\":[{\"id\":str,\"observation\":str,\"interpretation\":str,\"implication\":str,"
        "\"evidence\":[str],\"evidence_ids\":[str],\"based_on_interpretations\":[str],"
        "\"based_on_signals\":[str],\"primary_work_item_ids\":[str],\"supporting_work_item_ids\":[str],"
        "\"primary_entities\":[{\"name\":str,\"kind\":\"project\"|\"feature\"|\"system\"}],"
        "\"based_on_gaps\":[str],\"based_on_blockers\":[str],\"based_on_highlights\":[str],"
        "\"confidence\":str,\"priority\":str}]}. "
        "Produce 3-5 insights prioritizing gap/blocker candidates first."
    )
    user = (
        "insight_candidates are authoritative execution failures. Explain them; do not invent new ids or facts.\n"
        f"{prompt_json}"
    )
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_completion_tokens_for_manager_insights_insights(
            settings.openai_model
        ),
    }
    temp = temperature_for_chat_model(settings.openai_model, 0.2)
    if temp is not None:
        kwargs["temperature"] = temp

    resp = client.chat.completions.create(**kwargs)
    choice0 = resp.choices[0] if getattr(resp, "choices", None) else None
    msg0 = choice0.message if choice0 is not None else None
    full_text = _chat_message_text(msg0)
    raw_text = full_text
    truncated = False
    if len(raw_text) > _LLM_DEBUG_MAX_ASSISTANT_CHARS:
        raw_text = raw_text[:_LLM_DEBUG_MAX_ASSISTANT_CHARS]
        truncated = True

    response_level_error: str | None = None
    parsed = _extract_json_object(full_text)
    items: list[dict[str, Any]] = []
    if not full_text.strip():
        bits: list[str] = ["empty_assistant_message"]
        if choice0 is not None and getattr(choice0, "finish_reason", None):
            bits.append(f"finish_reason={choice0.finish_reason!r}")
        if msg0 is not None and getattr(msg0, "refusal", None):
            bits.append(f"refusal={getattr(msg0, 'refusal')!r}")
        response_level_error = "; ".join(bits)
    elif parsed is None:
        response_level_error = "could_not_parse_json_object_from_assistant_text"
    elif "insights" not in parsed:
        response_level_error = 'top_level JSON object missing required key "insights"'
    elif not isinstance(parsed.get("insights"), list):
        response_level_error = 'top_level JSON "insights" is not a JSON array'
    else:
        insight_rows = parsed.get("insights")
        assert isinstance(insight_rows, list)
        items = [x for x in insight_rows if isinstance(x, dict)]
        if len(items) != len(insight_rows):
            response_level_error = (
                f"insights[] contains {len(insight_rows) - len(items)} non-object row(s) "
                f"({len(insight_rows)} total entries)"
            )

    usage = getattr(resp, "usage", None)
    latency_ms = int((time.perf_counter() - started) * 1000)
    return (
        _LlmResponse(
            raw_text=raw_text,
            raw_text_truncated=truncated,
            parsed_insight_rows=len(items),
            items=items,
            response_level_error=response_level_error,
        ),
        _LlmMeta(
            generated_via="llm",
            latency_ms=latency_ms,
            prompt_tokens=(usage.prompt_tokens if usage else None),
            completion_tokens=(usage.completion_tokens if usage else None),
            total_tokens=(usage.total_tokens if usage else None),
        ),
    )


def generate_insights(
    settings: Settings,
    *,
    signals: SignalsV0Debug,
    interpretations: InterpretationBundleDebug,
    evidence: EvidenceBundle,
    gaps: GapBundle,
    key_achievements: KeyAchievementsBundleDebug,
    raw_highlights: RawHighlightsBundleDebug,
    work_items: WorkItemBundle,
) -> InsightBundleDebug:
    """Generate Step 8 insights with strict validation and deterministic fallback."""
    candidates = _build_insight_candidates(gaps, evidence, raw_highlights)
    interpretation_ids = {x.id for x in interpretations.items}
    llm_items: list[InsightItemDebug] = []
    rejected: list[RejectedInsightDebug] = []
    llm_response_text: str | None = None
    llm_response_truncated = False
    llm_parsed_rows: int | None = None
    llm_error: str | None = None
    fallback_reason: str | None = None
    meta = _LlmMeta(
        generated_via="fallback",
        latency_ms=None,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
    )

    if settings.openai_api_key.strip():
        prompt_json = _serialize_insight_llm_payload(
            candidates,
            interpretations,
            evidence,
            gaps,
            raw_highlights,
            work_items,
        )
        try:
            llm, meta = _call_llm(settings, prompt_json)
            llm_response_text = llm.raw_text
            llm_response_truncated = llm.raw_text_truncated
            llm_parsed_rows = llm.parsed_insight_rows
            if llm.response_level_error:
                llm_error = llm.response_level_error
            llm_items, row_rejections = _validate_insights(
                llm.items,
                interpretation_ids=interpretation_ids,
                work_items=work_items,
                evidence=evidence,
                gaps=gaps,
                raw_highlights=raw_highlights,
            )
            rejected.extend(row_rejections)
            if not llm_items:
                fallback_reason = "llm_output_invalid"
        except (APIError, Exception) as e:
            llm_items = []
            fallback_reason = "llm_error"
            llm_error = f"{type(e).__name__}: {e}"
            meta = _LlmMeta(
                generated_via="fallback",
                latency_ms=None,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
            )
    else:
        fallback_reason = "missing_api_key"

    items = llm_items or _fallback_insights(candidates, interpretations, work_items, evidence)
    generated_via = "llm" if llm_items else "fallback"
    return InsightBundleDebug(
        run_id=interpretations.run_id,
        tenant_id=interpretations.tenant_id,
        window_days=interpretations.window_days,
        items=items,
        generated_via=generated_via,  # type: ignore[arg-type]
        fallback_reason=fallback_reason if generated_via == "fallback" else None,
        model=settings.openai_model if generated_via == "llm" else None,
        latency_ms=meta.latency_ms if generated_via == "llm" else None,
        prompt_tokens=meta.prompt_tokens if generated_via == "llm" else None,
        completion_tokens=meta.completion_tokens if generated_via == "llm" else None,
        total_tokens=meta.total_tokens if generated_via == "llm" else None,
        llm_response_text=llm_response_text,
        llm_response_truncated=llm_response_truncated,
        llm_parsed_insight_rows=llm_parsed_rows,
        rejected_insights=rejected,
        llm_error=llm_error,
    )
