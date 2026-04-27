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
    GapBundle,
    InterpretationBundleDebug,
    InterpretationItemDebug,
    KeyAchievementsBundleDebug,
    LinkBundle,
    RawHighlightsBundleDebug,
    RejectedInterpretationDebug,
    SignalsV0Debug,
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


def _allowed_evidence_corpus(
    signals: SignalsV0Debug,
    evidence: EvidenceBundle,
    gaps: GapBundle,
    raw_highlights: RawHighlightsBundleDebug,
    key_achievements: KeyAchievementsBundleDebug,
) -> list[str]:
    rows: list[str] = []
    rows.extend(v for v in signals.explain.values() if isinstance(v, str))
    rows.extend(r.text for r in raw_highlights.items)
    rows.extend(k.title for k in key_achievements.items)
    rows.extend(g.description for g in gaps.gaps)
    for item in [*evidence.action_items, *evidence.blockers, *evidence.decisions]:
        rows.append(item.statement)
        rows.append(item.evidence)
    return [r for r in rows if isinstance(r, str) and r.strip()]


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
) -> str:
    payload = {
        "signals": signals.model_dump(mode="json"),
        "allowed_signal_ids_for_based_on_signals": list(_SIGNAL_IDS),
        "evidence": {
            "action_items": [x.model_dump(mode="json") for x in evidence.action_items[:24]],
            "blockers": [x.model_dump(mode="json") for x in evidence.blockers[:24]],
            "decisions": [x.model_dump(mode="json") for x in evidence.decisions[:24]],
        },
        "links": [x.model_dump(mode="json") for x in links.links if x.confidence == "high"][:60],
        "gaps": [x.model_dump(mode="json") for x in gaps.gaps[:40]],
        "raw_highlights": [x.model_dump(mode="json") for x in raw_highlights.items[:30]],
    }
    return json.dumps(payload, ensure_ascii=False)


def _validate_interpretations(
    items: list[dict[str, Any]],
    *,
    corpus: list[str],
) -> tuple[list[InterpretationItemDebug], list[RejectedInterpretationDebug]]:
    out: list[InterpretationItemDebug] = []
    rejected: list[RejectedInterpretationDebug] = []
    seen_ids: set[str] = set()
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
        if not all(_evidence_in_corpus(ev, corpus) for ev in canonical.evidence):
            bad = _unverifiable_evidence_strings(list(canonical.evidence), corpus)
            rejected.append(
                RejectedInterpretationDebug(
                    index=i,
                    reason="evidence not verifiable as a substring of allowed context (after whitespace normalize): "
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
            )
        )
    return out, rejected


def _fallback_interpretations(
    signals: SignalsV0Debug,
) -> list[InterpretationItemDebug]:
    out: list[InterpretationItemDebug] = []
    idx = 1

    def push(itype: str, desc: str, signal_ids: list[str], conf: str) -> None:
        nonlocal idx
        out.append(
            InterpretationItemDebug(
                id=f"interp_fallback_{idx}",
                type=itype,  # type: ignore[arg-type]
                description=desc,
                based_on_signals=signal_ids,
                evidence=[signals.explain[sig] for sig in signal_ids if sig in signals.explain][:2]
                or ["Deterministic fallback based on signal vector."],
                confidence=conf,  # type: ignore[arg-type]
            )
        )
        idx += 1

    if signals.follow_through in ("weak", "partial"):
        push(
            "follow_through",
            "Follow-through from discussion to tracked execution is incomplete.",
            ["follow_through", "expectation_coverage"],
            "medium",
        )
    if signals.blocker_visibility in ("partial", "not_visible"):
        push(
            "coordination_quality",
            "Blocker visibility in tracked systems is limited.",
            ["blocker_visibility", "interaction_friction"],
            "medium",
        )
    if signals.repeated_discussion_present or signals.interaction_friction == "present":
        push(
            "execution_friction",
            "Recurring discussion patterns suggest execution friction.",
            ["repeated_discussion_present", "interaction_friction"],
            "medium",
        )
    if signals.focus == "fragmented" or signals.urgent_pressure == "high":
        push(
            "prioritization",
            "Competing priorities may be reducing execution predictability.",
            ["focus", "urgent_pressure"],
            "low",
        )
    if signals.support_pattern == "asks_for_help":
        push(
            "support_dependency",
            "Work appears to rely on external unblock/support cycles.",
            ["support_pattern", "collaboration_intensity"],
            "low",
        )
    if not out:
        push(
            "collaboration_pattern",
            "Current signals are mixed; collaboration pattern remains neutral in this window.",
            ["collaboration_intensity", "feedback_reception"],
            "low",
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
        "You generate grounded engineering execution interpretations. "
        "Output strict JSON only, no markdown. "
        f"Each item's \"type\" MUST be exactly one of these strings (no synonyms): {types_list}. "
        f"Each item's \"confidence\" MUST be exactly one of: {conf_list}. "
        f"Each string in \"based_on_signals\" MUST be a signal id from this fixed set only "
        f"(snake_case keys like follow_through, not human sentences): {signal_ids_list}. "
        "The context JSON includes the same list under allowed_signal_ids_for_based_on_signals. "
        "Use \"based_on_signals\" to cite which signal *dimensions* you are interpreting. "
        "Use \"evidence\" for exact quoted lines/metrics; never put signal explain lines, JSON "
        "snippets, or ad-hoc metric strings in \"based_on_signals\". "
        "Schema: {\"interpretations\":[{\"id\":str,\"type\":str,\"description\":str,"
        "\"based_on_signals\":[str],\"evidence\":[str],\"confidence\":str}]}. "
        "Map narrative roles (e.g. an observation, a risk, a suggested action) onto the allowed "
        "\"type\" values — do not output type labels like observation, risk, or action. "
        "Use only evidence strings that are exact substrings of the provided context "
        "(after normalizing runs of whitespace). "
        "Do not invent facts. Keep descriptions concise."
    )
    user = (
        "Context JSON follows. Build interpretations from the signal vector, explain strings, and "
        "the evidence/gaps. Generate 3-6 interpretations.\n"
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
) -> InterpretationBundleDebug:
    """Generate Step 7 interpretations with strict validation and deterministic fallback."""
    corpus = _allowed_evidence_corpus(signals, evidence, gaps, raw_highlights, key_achievements)
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
        prompt_json = _serialize_prompt_context(signals, evidence, links, gaps, raw_highlights)
        try:
            llm, meta = _call_llm(settings, prompt_json)
            llm_response_text = llm.raw_text
            llm_response_truncated = llm.raw_text_truncated
            llm_parsed_rows = llm.parsed_interpretation_rows
            if llm.response_level_error:
                llm_error = llm.response_level_error
            raw_items = llm.items
            llm_items, row_rejections = _validate_interpretations(raw_items, corpus=corpus)
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

    items = llm_items or _fallback_interpretations(signals)
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
