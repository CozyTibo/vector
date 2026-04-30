"""Step 7 — LLM interpretations with strict schema + evidence validation."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, get_args

from openai import APIError, OpenAI
from pydantic import ValidationError

from vector.contracts.manager_insights import (
    InterpretationConfidence,
    InterpretationType,
    InterpretationV0,
)
from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    EvidenceItem,
    GapBundle,
    GapItem,
    InterpretationBundleDebug,
    InterpretationItemDebug,
    KeyAchievementsBundleDebug,
    LinkBundle,
    RawHighlightsBundleDebug,
    RejectedInterpretationDebug,
    SignalsV0Debug,
    WorkItemBundle,
)
from vector.openai_chat_params import (
    max_completion_tokens_for_manager_insights_interpretations,
    temperature_for_chat_model,
)
from vector.settings import Settings

_INTERPRETATION_TYPES: tuple[str, ...] = get_args(InterpretationType)
_INTERPRETATION_CONFIDENCE: tuple[str, ...] = get_args(InterpretationConfidence)

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
    parsed_interpretation_rows: int
    items: list[dict[str, Any]]
    response_level_error: str | None


_LLM_DEBUG_MAX_ASSISTANT_CHARS = 48_000


def _chat_message_text(message: Any) -> str:
    """Best-effort assistant string from a Chat Completions message (str or part list)."""
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


def _execution_artifact_corpus(
    evidence: EvidenceBundle,
    gaps: GapBundle,
    raw_highlights: RawHighlightsBundleDebug,
    key_achievements: KeyAchievementsBundleDebug,
    work_items: WorkItemBundle,
) -> list[str]:
    """Quotes must come from Step 2–5.6 execution artifacts (not signal explain strings)."""
    rows: list[str] = []
    rows.extend(g.id for g in gaps.gaps)
    rows.extend(g.description for g in gaps.gaps)
    rows.extend(h.id for h in raw_highlights.items)
    rows.extend(h.text for h in raw_highlights.items)
    for s in raw_highlights.items:
        rows.extend(s.sources)
    rows.extend(k.title for k in key_achievements.items)
    for wi in work_items.items:
        rows.append(wi.id)
        rows.append(wi.title)
        if wi.summary:
            rows.append(wi.summary)
        for v in wi.source_ref.values():
            if isinstance(v, str) and v.strip():
                rows.append(v)
    for item in [*evidence.action_items, *evidence.blockers, *evidence.decisions]:
        rows.append(item.id)
        rows.append(item.statement)
        rows.append(item.evidence)
        rows.append(item.source_work_item_id)
        rows.extend(item.linked_work_items)
    return [r for r in rows if isinstance(r, str) and r.strip()]


def _gap_work_item_ids(g: GapItem, wi_ids: set[str]) -> list[str]:
    out: list[str] = []
    for vals in g.evidence_pointers.values():
        if isinstance(vals, list):
            for x in vals:
                if isinstance(x, str) and x in wi_ids:
                    out.append(x)
        elif isinstance(vals, str) and vals in wi_ids:
            out.append(vals)
    return sorted(set(out))


def _looks_vague_generic_interpretation(description: str) -> bool:
    d = description.lower()
    if re.search(r"\b[A-Z][A-Z0-9]{1,6}-\d+\b", description):
        return False
    if "gap:" in description:
        return False
    if re.search(r"\b[a-z]+:[a-z0-9_:-]{4,}\b", description):
        return False
    needles = (
        "coordination is inconsistent",
        "the team is",
        "execution quality",
        "things are blocked",
        "collaboration is inconsistent",
        "team is blocked",
        "process is",
    )
    return any(n in d for n in needles)


def _description_cites_grounding_ids(
    description: str,
    *,
    based_on_gaps: list[str],
    based_on_highlights: list[str],
    based_on_blockers: list[str],
    evidence_by_id: dict[str, EvidenceItem],
) -> bool:
    for gid in based_on_gaps:
        if gid not in description:
            return False
    for hid in based_on_highlights:
        if hid not in description:
            return False
    for bid in based_on_blockers:
        row = evidence_by_id.get(bid)
        if row is None:
            return False
        if bid not in description and row.source_work_item_id not in description:
            return False
    return True


def _evidence_in_corpus(evidence_text: str, corpus: list[str]) -> bool:
    q = _normalize(evidence_text)
    if not q:
        return False
    for source in corpus:
        s = _normalize(source)
        if q in s:
            return True
    return False


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
            t = t[:140] + "…"
        bad.append(t or "<empty evidence>")
        if len(bad) >= max_examples:
            break
    return bad


def _serialize_prompt_context(
    signals: SignalsV0Debug,
    evidence: EvidenceBundle,
    links: LinkBundle,
    gaps: GapBundle,
    raw_highlights: RawHighlightsBundleDebug,
    work_items: WorkItemBundle,
) -> str:
    payload = {
        "execution_artifacts": {
            "gaps": [x.model_dump(mode="json") for x in gaps.gaps[:40]],
            "blockers": [x.model_dump(mode="json") for x in evidence.blockers[:24]],
            "action_items": [x.model_dump(mode="json") for x in evidence.action_items[:24]],
            "decisions": [x.model_dump(mode="json") for x in evidence.decisions[:24]],
            "raw_highlights": [x.model_dump(mode="json") for x in raw_highlights.items[:30]],
        },
        "work_items": [
            {
                "id": w.id,
                "title": w.title,
                "summary": w.summary,
                "project": w.project,
                "type": w.type,
                "source": w.source,
                "source_ref": w.source_ref,
            }
            for w in work_items.items[:60]
        ],
        "allowed_gap_ids": [g.id for g in gaps.gaps[:80]],
        "allowed_blocker_evidence_ids": [b.id for b in evidence.blockers[:80]],
        "allowed_highlight_ids": [h.id for h in raw_highlights.items[:80]],
        "high_confidence_links": [
            x.model_dump(mode="json") for x in links.links if x.confidence == "high"
        ][:60],
        "supporting_signals_only": signals.model_dump(mode="json"),
        "allowed_signal_ids_for_based_on_signals": list(_SIGNAL_IDS),
    }
    return json.dumps(payload, ensure_ascii=False)


def _validate_interpretations(
    items: list[dict[str, Any]],
    *,
    corpus: list[str],
    gaps: GapBundle,
    evidence: EvidenceBundle,
    raw_highlights: RawHighlightsBundleDebug,
    work_items: WorkItemBundle,
) -> tuple[list[InterpretationItemDebug], list[RejectedInterpretationDebug]]:
    out: list[InterpretationItemDebug] = []
    rejected: list[RejectedInterpretationDebug] = []
    seen_ids: set[str] = set()
    gap_ids = {g.id for g in gaps.gaps}
    highlight_ids = {h.id for h in raw_highlights.items}
    blocker_ids = {b.id for b in evidence.blockers}
    evidence_by_id = {e.id: e for e in [*evidence.action_items, *evidence.blockers, *evidence.decisions]}
    wi_ids = {w.id for w in work_items.items}

    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason="interpretation row is not a JSON object",
                    raw={},
                )
            )
            continue
        try:
            canonical = InterpretationV0.model_validate(raw)
        except ValidationError as e:
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"schema: {e}",
                    raw=raw,
                )
            )
            continue
        except Exception as e:  # pragma: no cover (defensive)
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"schema: {e}",
                    raw=raw,
                )
            )
            continue
        if canonical.id in seen_ids:
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"duplicate id {canonical.id!r}",
                    raw=raw,
                )
            )
            continue
        invalid_sigs = [s for s in canonical.based_on_signals if s not in _SIGNAL_IDS]
        if invalid_sigs:
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"invalid based_on_signals: {invalid_sigs!r} (not in allowlist)",
                    raw=raw,
                )
            )
            continue
        bad_gaps = [g for g in canonical.based_on_gaps if g not in gap_ids]
        if bad_gaps:
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"invalid based_on_gaps: {bad_gaps!r}",
                    raw=raw,
                )
            )
            continue
        bad_h = [h for h in canonical.based_on_highlights if h not in highlight_ids]
        if bad_h:
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"invalid based_on_highlights: {bad_h!r}",
                    raw=raw,
                )
            )
            continue
        bad_b = [b for b in canonical.based_on_blockers if b not in blocker_ids]
        if bad_b:
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason=f"invalid based_on_blockers (not Step-3 blocker ids): {bad_b!r}",
                    raw=raw,
                )
            )
            continue
        blocker_row_invalid = False
        for bid in canonical.based_on_blockers:
            row = evidence_by_id.get(bid)
            if row is None or row.kind != "blocker":
                rejected.append(
                    RejectedInterpretationDebug(
                        index=i,
                        reason=f"based_on_blockers id {bid!r} is not a blocker evidence row",
                        raw=raw,
                    )
                )
                blocker_row_invalid = True
                break
        if blocker_row_invalid:
            continue

        # Models often list extra raw_highlight ids but only paste a subset into `description`.
        # Drop uncited highlight ids so strict grounding matches what the model actually anchored.
        effective_highlights = [h for h in canonical.based_on_highlights if h in canonical.description]
        if canonical.based_on_highlights:
            if (
                not effective_highlights
                and not canonical.based_on_gaps
                and not canonical.based_on_blockers
            ):
                rejected.append(
                    RejectedInterpretationDebug(
                        index=i,
                        reason="based_on_highlights ids must appear verbatim in description when they are "
                        "the only grounding (gaps/blockers empty)",
                        raw=raw,
                    )
                )
                continue
            if len(effective_highlights) != len(canonical.based_on_highlights):
                canonical = canonical.model_copy(update={"based_on_highlights": effective_highlights})

        if not _description_cites_grounding_ids(
            canonical.description,
            based_on_gaps=list(canonical.based_on_gaps),
            based_on_highlights=list(canonical.based_on_highlights),
            based_on_blockers=list(canonical.based_on_blockers),
            evidence_by_id=evidence_by_id,
        ):
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason="description must literally include each cited gap_id, highlight_id, or "
                    "each blocker evidence id / its source_work_item_id",
                    raw=raw,
                )
            )
            continue

        anchored_wi = False
        for gid in canonical.based_on_gaps:
            g = next((x for x in gaps.gaps if x.id == gid), None)
            if g is None:
                continue
            for wid in _gap_work_item_ids(g, wi_ids):
                if wid in canonical.description:
                    anchored_wi = True
                    break
            if anchored_wi:
                break
        for bid in canonical.based_on_blockers:
            row = evidence_by_id.get(bid)
            if row and row.source_work_item_id in canonical.description:
                anchored_wi = True
                break
        for hid in canonical.based_on_highlights:
            h = next((x for x in raw_highlights.items if x.id == hid), None)
            if h is None:
                continue
            if any(s in canonical.description for s in h.sources if s in wi_ids):
                anchored_wi = True
                break
        # Shadow-work / discussion rows often anchor only to slack:calls ids with no NEX-* in text;
        # accept any Step-2 work_item id substring that appears in the description.
        if not anchored_wi:
            for wid in wi_ids:
                if wid and str(wid) in canonical.description:
                    anchored_wi = True
                    break
        # If the model cites an action_item id, require its source_work_item_id in the same line of
        # reasoning (Step-3 row → Step-2 anchor), not the action_item id alone.
        if not anchored_wi:
            for m in re.finditer(r"\baction_item:[a-f0-9]+\b", canonical.description):
                row = evidence_by_id.get(m.group(0))
                if (
                    row is not None
                    and row.kind == "action_item"
                    and row.source_work_item_id
                    and str(row.source_work_item_id) in canonical.description
                ):
                    anchored_wi = True
                    break
        if not anchored_wi and not re.search(r"\b[A-Z][A-Z0-9]{1,6}-\d+\b", canonical.description):
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason="description must name at least one Step-2 work item id from cited artifacts "
                    "or a ticket-like identifier (e.g. NEX-105)",
                    raw=raw,
                )
            )
            continue

        if _looks_vague_generic_interpretation(canonical.description):
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason="description reads as generic management summary without concrete anchors",
                    raw=raw,
                )
            )
            continue

        if not all(_evidence_in_corpus(ev, corpus) for ev in canonical.evidence):
            bad = _unverifiable_evidence_strings(list(canonical.evidence), corpus)
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason="evidence not verifiable as a substring of allowed execution context: "
                    + "; ".join(bad),
                    raw=raw,
                )
            )
            continue
        seen_ids.add(canonical.id)
        out.append(
            InterpretationItemDebug(
                id=canonical.id,
                type=canonical.type,
                description=canonical.description,
                based_on_signals=list(canonical.based_on_signals),
                evidence=list(canonical.evidence),
                confidence=canonical.confidence,
                based_on_gaps=list(canonical.based_on_gaps),
                based_on_blockers=list(canonical.based_on_blockers),
                based_on_highlights=list(canonical.based_on_highlights),
            )
        )
    return out, rejected


def _fallback_interpretations(
    signals: SignalsV0Debug,
    gaps: GapBundle,
    evidence: EvidenceBundle,
    raw_highlights: RawHighlightsBundleDebug,
    work_items: WorkItemBundle,
) -> list[InterpretationItemDebug]:
    """Deterministic interpretations from gaps → blockers → highlights (no signal-only summaries)."""
    out: list[InterpretationItemDebug] = []
    wi_ids = {w.id for w in work_items.items}
    evidence_by_id = {e.id: e for e in [*evidence.action_items, *evidence.blockers, *evidence.decisions]}
    idx = 1

    def push_row(
        *,
        itype: str,
        description: str,
        quotes: list[str],
        gap_ids: list[str],
        blocker_ids: list[str],
        highlight_ids: list[str],
        sigs: list[str],
        conf: str,
    ) -> None:
        nonlocal idx
        out.append(
            InterpretationItemDebug(
                id=f"interp_fallback_{idx}",
                type=itype,  # type: ignore[arg-type]
                description=description,
                based_on_signals=sigs,
                evidence=quotes[:3],
                confidence=conf,  # type: ignore[arg-type]
                based_on_gaps=gap_ids,
                based_on_blockers=blocker_ids,
                based_on_highlights=highlight_ids,
            )
        )
        idx += 1

    def gap_priority(g: GapItem) -> tuple[int, str]:
        if g.type in ("expected_not_executed", "discussed_not_linked_to_work"):
            return (0, g.id)
        if g.type == "blocker_not_tracked":
            return (1, g.id)
        return (3, g.id)

    sorted_gaps = sorted(gaps.gaps, key=gap_priority)
    for g in sorted_gaps[:4]:
        parts: list[str] = [g.id, g.description]
        for wid in _gap_work_item_ids(g, wi_ids)[:3]:
            parts.append(wid)
        desc = " — ".join(parts)
        quotes: list[str] = [g.description]
        for k, vals in g.evidence_pointers.items():
            if not isinstance(vals, list):
                continue
            for eid in vals:
                if not isinstance(eid, str):
                    continue
                row = evidence_by_id.get(eid)
                if row:
                    quotes.append(row.statement)
        raw_blockers = g.evidence_pointers.get("blocker_item_ids", [])
        blocker_ids = [b for b in raw_blockers if isinstance(b, str)] if isinstance(raw_blockers, list) else []
        if g.type in ("expected_not_executed", "discussed_not_linked_to_work"):
            sigs = ["follow_through", "expectation_coverage"]
            itype_val = "follow_through"
        elif g.type == "blocker_not_tracked":
            sigs = ["blocker_visibility", "follow_through"]
            itype_val = "execution_friction"
        else:
            sigs = ["documentation_linkage", "focus"]
            itype_val = "execution_friction"
        push_row(
            itype=itype_val,
            description=desc,
            quotes=quotes or [g.description],
            gap_ids=[g.id],
            blocker_ids=blocker_ids,
            highlight_ids=[],
            sigs=sigs,
            conf="medium",
        )

    for b in evidence.blockers[:2]:
        desc = f"{b.id} on {b.source_work_item_id}: {b.statement}"
        push_row(
            itype="execution_friction",
            description=desc,
            quotes=[b.statement, b.evidence],
            gap_ids=[],
            blocker_ids=[b.id],
            highlight_ids=[],
            sigs=["blocker_visibility", "interaction_friction"],
            conf="medium",
        )

    for h in raw_highlights.items[:2]:
        if len(h.sources) < 2 and not any(
            w in h.text.lower() for w in ("repeated", "multiple", "distinct", "several")
        ):
            continue
        src = next((s for s in h.sources if s in wi_ids), h.sources[0] if h.sources else "unknown")
        desc = f"{h.id} — {src} — {h.text}"
        push_row(
            itype="execution_friction",
            description=desc,
            quotes=[h.text],
            gap_ids=[],
            blocker_ids=[],
            highlight_ids=[h.id],
            sigs=["repeated_discussion_present", "interaction_friction"],
            conf="medium",
        )

    return out[:6]


def _call_llm(
    settings: Settings,
    prompt_json: str,
) -> tuple[_LlmResponse, _LlmMeta]:
    started = time.perf_counter()
    client = OpenAI(api_key=settings.openai_api_key)
    types_list = ", ".join(_INTERPRETATION_TYPES)
    conf_list = ", ".join(_INTERPRETATION_CONFIDENCE)
    signal_ids_list = ", ".join(_SIGNAL_IDS)
    system = (
        "You detect execution patterns from STRUCTURED artifacts only. Output strict JSON, no markdown. "
        f"Each item's \"type\" MUST be one of: {types_list}. "
        f"Each item's \"confidence\" MUST be one of: {conf_list}. "
        "MANDATORY GROUNDING: each interpretation MUST cite at least one of based_on_gaps, "
        "based_on_blockers (Step-3 blocker evidence row ids), or based_on_highlights using ONLY ids "
        "from allowed_gap_ids / allowed_blocker_evidence_ids / allowed_highlight_ids in the context. "
        "\"based_on_signals\" is OPTIONAL supporting context only (subset of "
        "allowed_signal_ids_for_based_on_signals); you MAY use an empty list. "
        "\"description\" MUST be a concrete pattern statement: include EVERY cited gap_id and "
        "highlight_id as literal substrings; for each cited blocker id include that id OR the row's "
        "source_work_item_id in the description; include at least one Step-2 work_item id from "
        "work_items (exact id string, e.g. slack:message:..., calls:event:...) OR a ticket key like "
        "NEX-105 from titles/source_ref. Do not use action_item:... as the only anchor — cite the "
        "underlying work item id or ticket key. "
        "BAD: \"coordination is inconsistent\". "
        "GOOD: \"g1 — calls:c1 — Repeated discussions about NEX-1 are not linked to any tracked issue "
        "or PR\". "
        "Do not invent ids. "
        "\"evidence\" strings MUST be exact substrings of execution_artifacts or work_items text "
        "(after whitespace normalize). "
        "Schema: {\"interpretations\":[{\"id\":str,\"type\":str,\"description\":str,"
        "\"based_on_signals\":[str],\"evidence\":[str],\"confidence\":str,"
        "\"based_on_gaps\":[str],\"based_on_blockers\":[str],\"based_on_highlights\":[str]}]}. "
        "Generate 3-6 interpretations; skip categories with no cited artifacts."
    )
    user = (
        "Context JSON follows. execution_artifacts + work_items are PRIMARY; supporting_signals_only "
        "is secondary. Build interpretations only from real gaps/blockers/highlights.\n"
        f"{prompt_json}"
    )
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_completion_tokens_for_manager_insights_interpretations(
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
    elif "interpretations" not in parsed:
        response_level_error = 'top_level JSON object missing required key "interpretations"'
    elif not isinstance(parsed.get("interpretations"), list):
        response_level_error = 'top_level JSON "interpretations" is not a JSON array'
    else:
        interps = parsed.get("interpretations")
        assert isinstance(interps, list)
        items = [x for x in interps if isinstance(x, dict)]
        if len(items) != len(interps):
            # Non-object rows can't be attached as dict-shaped rejections; surface at response level.
            response_level_error = (
                f"interpretations[] contains {len(interps) - len(items)} non-object row(s) "
                f"({len(interps)} total entries)"
            )

    usage = getattr(resp, "usage", None)
    latency_ms = int((time.perf_counter() - started) * 1000)
    return (
        _LlmResponse(
            raw_text=raw_text,
            raw_text_truncated=truncated,
            parsed_interpretation_rows=len(items),
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


def generate_interpretations(
    settings: Settings,
    *,
    signals: SignalsV0Debug,
    evidence: EvidenceBundle,
    links: LinkBundle,
    gaps: GapBundle,
    key_achievements: KeyAchievementsBundleDebug,
    raw_highlights: RawHighlightsBundleDebug,
    work_items: WorkItemBundle,
) -> InterpretationBundleDebug:
    """Generate Step 7 interpretations with strict validation and deterministic fallback."""
    corpus = _execution_artifact_corpus(evidence, gaps, raw_highlights, key_achievements, work_items)
    llm_items: list[InterpretationItemDebug] = []
    rejected: list[RejectedInterpretationDebug] = []
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
        prompt_json = _serialize_prompt_context(
            signals, evidence, links, gaps, raw_highlights, work_items
        )
        try:
            llm, meta = _call_llm(settings, prompt_json)
            llm_response_text = llm.raw_text
            llm_response_truncated = llm.raw_text_truncated
            llm_parsed_rows = llm.parsed_interpretation_rows
            if llm.response_level_error:
                llm_error = llm.response_level_error
            raw_items = llm.items
            llm_items, row_rejections = _validate_interpretations(
                raw_items,
                corpus=corpus,
                gaps=gaps,
                evidence=evidence,
                raw_highlights=raw_highlights,
                work_items=work_items,
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

    items = llm_items or _fallback_interpretations(
        signals, gaps, evidence, raw_highlights, work_items
    )
    generated_via = "llm" if llm_items else "fallback"
    return InterpretationBundleDebug(
        run_id=evidence.run_id,
        tenant_id=evidence.tenant_id,
        window_days=evidence.window_days,
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
        llm_parsed_interpretation_rows=llm_parsed_rows,
        rejected_interpretations=rejected,
        llm_error=llm_error,
    )
