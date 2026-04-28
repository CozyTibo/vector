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
    GapBundle,
    InsightBundleDebug,
    InsightItemDebug,
    InterpretationBundleDebug,
    KeyAchievementsBundleDebug,
    RawHighlightsBundleDebug,
    RejectedInsightDebug,
    SignalsV0Debug,
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
    interpretations: InterpretationBundleDebug,
    evidence: EvidenceBundle,
    gaps: GapBundle,
    raw_highlights: RawHighlightsBundleDebug,
    key_achievements: KeyAchievementsBundleDebug,
) -> list[str]:
    rows: list[str] = []
    rows.extend(v for v in signals.explain.values() if isinstance(v, str))
    rows.extend(i.description for i in interpretations.items)
    for i in interpretations.items:
        rows.extend(i.evidence)
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
        if q in _normalize(source):
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
            t = t[:140] + "..."
        bad.append(t or "<empty evidence>")
        if len(bad) >= max_examples:
            break
    return bad


def _serialize_prompt_context(
    signals: SignalsV0Debug,
    interpretations: InterpretationBundleDebug,
    evidence: EvidenceBundle,
    gaps: GapBundle,
    key_achievements: KeyAchievementsBundleDebug,
    raw_highlights: RawHighlightsBundleDebug,
) -> str:
    payload = {
        "signals": signals.model_dump(mode="json"),
        "interpretations": [x.model_dump(mode="json") for x in interpretations.items[:12]],
        "allowed_signal_ids_for_based_on_signals": list(_SIGNAL_IDS),
        "allowed_interpretation_ids_for_based_on_interpretations": [
            x.id for x in interpretations.items[:12]
        ],
        "evidence": {
            "action_items": [x.model_dump(mode="json") for x in evidence.action_items[:24]],
            "blockers": [x.model_dump(mode="json") for x in evidence.blockers[:24]],
            "decisions": [x.model_dump(mode="json") for x in evidence.decisions[:24]],
        },
        "gaps": [x.model_dump(mode="json") for x in gaps.gaps[:40]],
        "key_achievements": [x.model_dump(mode="json") for x in key_achievements.items[:30]],
        "raw_highlights": [x.model_dump(mode="json") for x in raw_highlights.items[:30]],
    }
    return json.dumps(payload, ensure_ascii=False)


def _validate_insights(
    items: list[dict[str, Any]],
    *,
    corpus: list[str],
    interpretation_ids: set[str],
) -> tuple[list[InsightItemDebug], list[RejectedInsightDebug]]:
    out: list[InsightItemDebug] = []
    rejected: list[RejectedInsightDebug] = []
    seen_ids: set[str] = set()

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
        if not all(_evidence_in_corpus(ev, corpus) for ev in canonical.evidence):
            bad = _unverifiable_evidence_strings(list(canonical.evidence), corpus)
            rejected.append(
                RejectedInsightDebug(
                    index=i,
                    reason="evidence not verifiable as a substring of allowed context: "
                    + "; ".join(bad),
                    raw=raw,
                )
            )
            continue

        seen_ids.add(canonical.id)
        out.append(
            InsightItemDebug(
                id=canonical.id,
                observation=canonical.observation,
                interpretation=canonical.interpretation,
                implication=canonical.implication,
                evidence=list(canonical.evidence),
                based_on_interpretations=list(canonical.based_on_interpretations),
                based_on_signals=list(canonical.based_on_signals),
                confidence=canonical.confidence,
                priority=canonical.priority,
            )
        )

    return out, rejected


def _fallback_insights(interpretations: InterpretationBundleDebug) -> list[InsightItemDebug]:
    def priority_for_confidence(conf: str) -> str:
        if conf == "high":
            return "high"
        if conf == "medium":
            return "medium"
        return "low"

    out: list[InsightItemDebug] = []
    for i, interp in enumerate(interpretations.items[:5], start=1):
        out.append(
            InsightItemDebug(
                id=f"insight_fallback_{i}",
                observation=interp.description,
                interpretation=(
                    f"Signal pattern indicates {interp.type.replace('_', ' ')} with {interp.confidence}"
                    " confidence."
                ),
                implication="Manager attention is recommended to prevent delivery drift.",
                evidence=list(interp.evidence[:3]) or ["Deterministic fallback from Step 7 interpretation."],
                based_on_interpretations=[interp.id],
                based_on_signals=list(interp.based_on_signals[:3]),
                confidence=interp.confidence,  # type: ignore[arg-type]
                priority=priority_for_confidence(interp.confidence),  # type: ignore[arg-type]
            )
        )
    if not out:
        out.append(
            InsightItemDebug(
                id="insight_fallback_1",
                observation="No validated interpretations were available for this run.",
                interpretation="Insight generation used deterministic fallback due to missing validated inputs.",
                implication="Run quality checks on upstream connector coverage and interpretation validation.",
                evidence=["Deterministic fallback generated without validated Step 7 interpretations."],
                based_on_interpretations=["none"],
                based_on_signals=["execution_momentum"],
                confidence="low",
                priority="low",
            )
        )
    return out[:5]


def _call_llm(settings: Settings, prompt_json: str) -> tuple[_LlmResponse, _LlmMeta]:
    started = time.perf_counter()
    client = OpenAI(api_key=settings.openai_api_key)

    conf_list = ", ".join(_INSIGHT_CONFIDENCE)
    priority_list = ", ".join(_INSIGHT_PRIORITY)
    signal_ids_list = ", ".join(_SIGNAL_IDS)
    system = (
        "You generate grounded engineering-management insights. Output strict JSON only, no markdown. "
        f"Each item's \"confidence\" MUST be one of: {conf_list}. "
        f"Each item's \"priority\" MUST be one of: {priority_list}. "
        f"Each string in \"based_on_signals\" MUST be from this allowlist only: {signal_ids_list}. "
        "Each string in \"based_on_interpretations\" MUST be an id present in context field "
        "\"allowed_interpretation_ids_for_based_on_interpretations\". "
        "Schema: {\"insights\":[{\"id\":str,\"observation\":str,\"interpretation\":str,"
        "\"implication\":str,\"evidence\":[str],\"based_on_interpretations\":[str],"
        "\"based_on_signals\":[str],\"confidence\":str,\"priority\":str}]}. "
        "No new facts; use only evidence strings that are exact substrings of provided context "
        "(after whitespace normalization). Keep each field concise."
    )
    user = (
        "Context JSON follows. Generate 3-5 insights with clear manager implications.\n"
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
) -> InsightBundleDebug:
    """Generate Step 8 insights with strict validation and deterministic fallback."""
    corpus = _allowed_evidence_corpus(
        signals, interpretations, evidence, gaps, raw_highlights, key_achievements
    )
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
        prompt_json = _serialize_prompt_context(
            signals, interpretations, evidence, gaps, key_achievements, raw_highlights
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
                corpus=corpus,
                interpretation_ids=interpretation_ids,
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

    items = llm_items or _fallback_insights(interpretations)
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
