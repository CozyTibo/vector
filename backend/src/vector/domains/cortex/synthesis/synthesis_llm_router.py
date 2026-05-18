"""Phase 08 P08-11 — LLM authority boundary + model routing (**SYN-AI-***, **G-P08-LLM-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-law-system.md`` §AI.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.adapters.llm.fake_llm_adapter import FakeLlmAdapter
from vector.domains.cortex.synthesis.adapters.llm.protocol import (
    LlmAdapterError,
    LlmCompletionRequestV1,
    LlmCompletionResultV1,
    LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    selection_policy_caps_for_synthesis_workload_v1,
)
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SD_LLM_SCHEMA_V1,
    upstream_retrieval_legality_from_ingress_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1

PHASE08_SYNTHESIS_LLM_ROUTER_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_LLM01_GATE_ID_V1: Final[str] = "G-P08-LLM-01"

PHASE08_LLM_LAW_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-law-system.md"
)

SD_LLM_TIMEOUT_V1: Final[str] = "SD-LLM-TIMEOUT"
SD_LLM_POLICY_V1: Final[str] = "SD-LLM-POLICY"
SD_CAP_LLM_V1: Final[str] = "SD-CAP-LLM"

LLM_AUTHORITY_STRUCTURING_V1: Final[str] = "llm_structuring"
LLM_AUTHORITY_NARRATION_V1: Final[str] = "llm_narration"

_MODEL_ROUTE_REQUIRED_FIELDS_V1: Final[tuple[str, ...]] = (
    "model_route_id",
    "authority_class",
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "response_format",
    "prompt_template_id",
    "prompt_template_version",
)


class SynthesisLlmRouterError(ValueError):
    """Fail-closed synthesis LLM routing / adapter law."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def list_model_routes_from_policy_pack_v1(
    pack: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    raw_pack = dict(pack) if pack is not None else load_synthesis_policy_pack_v1()
    routes = raw_pack.get("model_routes")
    if not isinstance(routes, list):
        return []
    return [dict(row) for row in routes if isinstance(row, Mapping)]


def validate_model_route_v1(route: Mapping[str, Any]) -> list[str]:
    """**SYN-AI-01** — route registry pins."""
    errors: list[str] = []
    for field in _MODEL_ROUTE_REQUIRED_FIELDS_V1:
        if route.get(field) is None or route.get(field) == "":
            errors.append(f"missing:{field}")
    if str(route.get("response_format") or "") != LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1:
        errors.append("response_format_must_be_json_schema")
    try:
        float(route.get("temperature", 0))
    except (TypeError, ValueError):
        errors.append("invalid:temperature")
    try:
        int(route.get("max_tokens", 0))
    except (TypeError, ValueError):
        errors.append("invalid:max_tokens")
    authority = str(route.get("authority_class") or "")
    if authority not in {LLM_AUTHORITY_STRUCTURING_V1, LLM_AUTHORITY_NARRATION_V1}:
        errors.append(f"invalid:authority_class:{authority}")
    return errors


def get_model_route_v1(
    model_route_id: str,
    *,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    for row in list_model_routes_from_policy_pack_v1(pack):
        if str(row.get("model_route_id")) == model_route_id:
            violations = validate_model_route_v1(row)
            if violations:
                raise SynthesisLlmRouterError(
                    "invalid_model_route",
                    detail={"model_route_id": model_route_id, "violations": violations},
                )
            return row
    raise SynthesisLlmRouterError(
        "model_route_not_found",
        detail={"model_route_id": model_route_id},
    )


def should_skip_llm_for_retrieval_legality_v1(
    retrieval_ingress: Mapping[str, Any],
    *,
    synthesis_intent: str,
    execution_partition: str,
) -> tuple[bool, str]:
    """**SYN-FSM-01** — block LLM when retrieval floor forbids it."""
    upstream = upstream_retrieval_legality_from_ingress_v1(retrieval_ingress)
    if upstream == "retrieval_forbidden":
        return True, "retrieval_forbidden"
    if upstream == "retrieval_unverifiable":
        if execution_partition.strip().lower() == "authoritative" and synthesis_intent != "audit":
            return True, "retrieval_unverifiable_authoritative_non_audit"
    return False, ""


def compute_prompt_hash_v1(
    *,
    model_route: Mapping[str, Any],
    context: Mapping[str, Any],
    template_variant_id: str = "default",
) -> str:
    """Delegate to **SYN-PRM-03** prompt assembly (Step **12**)."""
    from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
        compute_synthesis_prompt_hash_v1,
    )

    return compute_synthesis_prompt_hash_v1(
        prompt_template_id=str(model_route["prompt_template_id"]),
        prompt_template_version=int(model_route["prompt_template_version"]),
        context=context,
        template_variant_id=template_variant_id,
    )


def select_model_route_ids_for_job_v1(
    envelope: Mapping[str, Any],
    *,
    claim_slots: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Choose policy-pack routes for this job (struct + optional narrate/audit)."""
    routes: list[str] = ["struct-v1"]
    if any(isinstance(row, Mapping) and row.get("discourse_only") for row in claim_slots):
        routes.append("narrate-v1")
    if str(envelope.get("synthesis_intent")) == "audit":
        routes.append("audit-v1")
    pack = load_synthesis_policy_pack_v1(
        policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
    )
    known = {str(r.get("model_route_id")) for r in list_model_routes_from_policy_pack_v1(pack)}
    return [rid for rid in routes if rid in known]


def _build_sd_llm_row_v1(sd_code: str, *, reason: str, model_route_id: str = "") -> dict[str, Any]:
    return {
        "synthesis_omission_class": sd_code,
        "sd_code": sd_code,
        "reason": reason,
        "model_route_id": model_route_id,
    }


def _map_adapter_error_to_sd_v1(exc: LlmAdapterError) -> str:
    code = exc.code
    if code == "llm_timeout":
        return SD_LLM_TIMEOUT_V1
    if code == "llm_policy_refusal":
        return SD_LLM_POLICY_V1
    if code in {"llm_schema_invalid", "invalid_fake_llm_fixture"}:
        return SD_LLM_SCHEMA_V1
    return SD_LLM_SCHEMA_V1


def _invoke_route_v1(
    *,
    model_route: Mapping[str, Any],
    prompt_hash: str,
    context: dict[str, Any],
    simulate: str | None,
    adapter: FakeLlmAdapter,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], bool]:
    """Return ``(invocation_row, completion, sd_rows, schema_failed)``."""
    route_id = str(model_route["model_route_id"])
    request = LlmCompletionRequestV1(
        model_route_id=route_id,
        provider=str(model_route["provider"]),
        model=str(model_route["model"]),
        temperature=float(model_route["temperature"]),
        max_tokens=int(model_route["max_tokens"]),
        response_format=str(model_route["response_format"]),
        prompt_hash=prompt_hash,
        context=context,
        simulate=simulate,
    )
    sd_rows: list[dict[str, Any]] = []
    schema_failed = False

    def _attempt() -> LlmCompletionResultV1:
        return adapter.complete_structured_v1(request)

    try:
        result = _attempt()
    except LlmAdapterError as first_exc:
        sd_code = _map_adapter_error_to_sd_v1(first_exc)
        if sd_code == SD_LLM_SCHEMA_V1:
            try:
                result = _attempt()
            except LlmAdapterError as second_exc:
                sd_rows.append(
                    _build_sd_llm_row_v1(
                        SD_LLM_SCHEMA_V1,
                        reason=second_exc.code,
                        model_route_id=route_id,
                    ),
                )
                schema_failed = True
                invocation = {
                    "model_route_id": route_id,
                    "authority_class": model_route.get("authority_class"),
                    "provider": model_route.get("provider"),
                    "model": model_route.get("model"),
                    "temperature": model_route.get("temperature"),
                    "max_tokens": model_route.get("max_tokens"),
                    "response_format": model_route.get("response_format"),
                    "prompt_template_id": model_route.get("prompt_template_id"),
                    "prompt_template_version": model_route.get("prompt_template_version"),
                    "prompt_hash": prompt_hash,
                    "completion_hash": "",
                    "tokens_used": 0,
                    "status": "schema_error",
                }
                return invocation, {}, sd_rows, schema_failed
        else:
            sd_rows.append(
                _build_sd_llm_row_v1(sd_code, reason=first_exc.code, model_route_id=route_id),
            )
            invocation = {
                "model_route_id": route_id,
                "authority_class": model_route.get("authority_class"),
                "provider": model_route.get("provider"),
                "model": model_route.get("model"),
                "temperature": model_route.get("temperature"),
                "max_tokens": model_route.get("max_tokens"),
                "response_format": model_route.get("response_format"),
                "prompt_template_id": model_route.get("prompt_template_id"),
                "prompt_template_version": model_route.get("prompt_template_version"),
                "prompt_hash": prompt_hash,
                "completion_hash": "",
                "tokens_used": 0,
                "status": sd_code,
            }
            return invocation, {}, sd_rows, schema_failed

    invocation = {
        "model_route_id": route_id,
        "authority_class": model_route.get("authority_class"),
        "provider": model_route.get("provider"),
        "model": model_route.get("model"),
        "temperature": model_route.get("temperature"),
        "max_tokens": model_route.get("max_tokens"),
        "response_format": model_route.get("response_format"),
        "prompt_template_id": model_route.get("prompt_template_id"),
        "prompt_template_version": model_route.get("prompt_template_version"),
        "prompt_hash": prompt_hash,
        "completion_hash": result.completion_hash,
        "tokens_used": result.tokens_used,
        "status": "ok",
    }
    return invocation, dict(result.completion), sd_rows, schema_failed


def apply_discourse_phrases_to_claims_v1(
    claims: Sequence[Mapping[str, Any]],
    completion: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Merge LLM discourse phrases into ``discourse_only`` claims only."""
    phrase_map: dict[str, str] = {}
    phrases = completion.get("discourse_phrases")
    if isinstance(phrases, list):
        for row in phrases:
            if isinstance(row, Mapping) and row.get("claim_id"):
                phrase_map[str(row["claim_id"])] = str(row.get("phrase") or "")
    out: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        updated = dict(claim)
        if updated.get("discourse_only") and phrase_map.get(str(updated.get("claim_id") or "")):
            updated["discourse_text"] = phrase_map[str(updated["claim_id"])]
        out.append(updated)
    return out


def execute_synthesis_llm_phase_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_ingress: Mapping[str, Any],
    claim_slots: Sequence[Mapping[str, Any]],
    claims: Sequence[Mapping[str, Any]],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    synthesis_citation_envelope: Mapping[str, Any] | None,
    prompt_assemblies: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run LLM phase — adapter-isolated, pinned routes, SD-LLM-* on failure."""
    intent = str(envelope["synthesis_intent"])
    partition = str(envelope["execution_partition"])
    skip, skip_reason = should_skip_llm_for_retrieval_legality_v1(
        retrieval_ingress,
        synthesis_intent=intent,
        execution_partition=partition,
    )
    if skip:
        return {
            "skipped": True,
            "skip_reason": skip_reason,
            "llm_invocations": [],
            "llm_trace_refs": [],
            "claims": [dict(c) for c in claims if isinstance(c, Mapping)],
            "synthesis_omission_rows": [],
            "llm_schema_failed": False,
            "tokens_used_total": 0,
        }

    wl = str(envelope["synthesis_workload_class"])
    caps = dict(envelope.get("selection_policy") or {})
    if not caps:
        caps = selection_policy_caps_for_synthesis_workload_v1(wl)
    max_tokens = int(caps.get("max_llm_tokens", 8192))

    simulate = None
    selection = envelope.get("selection_policy")
    if isinstance(selection, Mapping):
        raw_sim = selection.get("llm_simulate")
        if isinstance(raw_sim, str):
            simulate = raw_sim

    pack = load_synthesis_policy_pack_v1(
        policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
    )
    route_ids = select_model_route_ids_for_job_v1(envelope, claim_slots=claim_slots)
    assembly_by_route: dict[str, Mapping[str, Any]] = {}
    if prompt_assemblies:
        for row in prompt_assemblies:
            if isinstance(row, Mapping) and row.get("model_route_id"):
                assembly_by_route[str(row["model_route_id"])] = row
    adapter = FakeLlmAdapter()
    invocations: list[dict[str, Any]] = []
    trace_refs: list[dict[str, Any]] = []
    sd_rows: list[dict[str, Any]] = []
    merged_claims = [dict(c) for c in claims if isinstance(c, Mapping)]
    schema_failed = False
    tokens_total = 0

    for route_id in route_ids:
        if tokens_total >= max_tokens:
            sd_rows.append(
                _build_sd_llm_row_v1(SD_CAP_LLM_V1, reason="max_llm_tokens_exceeded", model_route_id=route_id),
            )
            break
        model_route = get_model_route_v1(route_id, pack=pack)
        assembly = assembly_by_route.get(route_id)
        if assembly is not None:
            context = dict(assembly.get("context") or {})
            prompt_hash = str(assembly.get("prompt_hash") or "")
            template_variant_id = str(assembly.get("template_variant_id") or "default")
        else:
            from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
                assemble_synthesis_prompt_for_route_v1,
            )

            built = assemble_synthesis_prompt_for_route_v1(
                envelope=envelope,
                model_route=model_route,
                claim_slots=claim_slots,
                synthesis_omission_rows=synthesis_omission_rows,
                retrieval_ingress=retrieval_ingress,
            )
            context = dict(built.get("context") or {})
            prompt_hash = str(built.get("prompt_hash") or "")
            template_variant_id = str(built.get("template_variant_id") or "default")
        invocation, completion, route_sd, route_schema_failed = _invoke_route_v1(
            model_route=model_route,
            prompt_hash=prompt_hash,
            context=context,
            simulate=simulate if route_id == route_ids[0] else None,
            adapter=adapter,
        )
        invocations.append(invocation)
        trace_refs.append(
            {
                "model_route_id": route_id,
                "prompt_hash": prompt_hash,
                "completion_hash": invocation.get("completion_hash") or "",
                "prompt_template_id": model_route.get("prompt_template_id"),
                "prompt_template_version": model_route.get("prompt_template_version"),
                "template_variant_id": template_variant_id,
            },
        )
        sd_rows.extend(route_sd)
        schema_failed = schema_failed or route_schema_failed
        tokens_total += int(invocation.get("tokens_used") or 0)
        if completion and str(model_route.get("authority_class")) == LLM_AUTHORITY_STRUCTURING_V1:
            merged_claims = apply_discourse_phrases_to_claims_v1(merged_claims, completion)

    if tokens_total > max_tokens and not any(r.get("sd_code") == SD_CAP_LLM_V1 for r in sd_rows):
        sd_rows.append(_build_sd_llm_row_v1(SD_CAP_LLM_V1, reason="max_llm_tokens_exceeded"))

    return {
        "skipped": False,
        "skip_reason": "",
        "llm_invocations": invocations,
        "llm_trace_refs": trace_refs,
        "claims": merged_claims,
        "synthesis_omission_rows": sd_rows,
        "llm_schema_failed": schema_failed,
        "tokens_used_total": tokens_total,
    }


def build_synthesis_llm_model_route_catalog_v1() -> dict[str, Any]:
    """Admin catalog — model route registry."""
    pack = load_synthesis_policy_pack_v1()
    routes = list_model_routes_from_policy_pack_v1(pack)
    caps = pack.get("caps") if isinstance(pack.get("caps"), Mapping) else {}
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_llm_model_routes_v1",
        "phase08_synthesis_llm_router_runtime_schema_version": (
            PHASE08_SYNTHESIS_LLM_ROUTER_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_LLM01_GATE_ID_V1,
        "spec_ref": PHASE08_LLM_LAW_SPEC_REF_V1,
        "model_routes": routes,
        "max_llm_tokens_default": int((caps or {}).get("max_llm_tokens", 8192)),
        "sd_llm_codes": [SD_LLM_TIMEOUT_V1, SD_LLM_SCHEMA_V1, SD_LLM_POLICY_V1, SD_CAP_LLM_V1],
        "adapter_id": "FakeLlmAdapter",
        "response_format_required": LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1,
    }


def build_synthesis_llm_route_preview_v1(
    envelope: Mapping[str, Any],
    *,
    claim_slots: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Admin preview — selected routes + prompt hashes without invoking adapter."""
    slots = list(claim_slots or [])
    route_ids = select_model_route_ids_for_job_v1(envelope, claim_slots=slots)
    pack = load_synthesis_policy_pack_v1(
        policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
    )
    from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
        assemble_synthesis_prompts_for_job_v1,
    )

    assemblies = assemble_synthesis_prompts_for_job_v1(
        envelope=envelope,
        claim_slots=slots,
        synthesis_omission_rows=[],
        retrieval_ingress=None,
    )
    assembly_by_route = {str(a["model_route_id"]): a for a in assemblies if a.get("model_route_id")}
    previews: list[dict[str, Any]] = []
    for route_id in route_ids:
        route = get_model_route_v1(route_id, pack=pack)
        asm = assembly_by_route.get(route_id) or {}
        previews.append(
            {
                "model_route_id": route_id,
                "authority_class": route.get("authority_class"),
                "prompt_hash": asm.get("prompt_hash", ""),
                "template_variant_id": asm.get("template_variant_id", "default"),
                "violations": validate_model_route_v1(route),
            },
        )
    preview_ingress: dict[str, Any] = {"retrieval_legality_class": "retrieval_replay_safe"}
    preview_raw = envelope.get("_preview_retrieval_legality")
    if isinstance(preview_raw, str) and preview_raw:
        preview_ingress["retrieval_legality_class"] = preview_raw
    skip, reason = should_skip_llm_for_retrieval_legality_v1(
        preview_ingress,
        synthesis_intent=str(envelope["synthesis_intent"]),
        execution_partition=str(envelope["execution_partition"]),
    )
    return {
        "surface_kind": "synthesis_llm_route_preview",
        "gate_id": GP08_LLM01_GATE_ID_V1,
        "llm_would_skip": skip,
        "llm_skip_reason": reason,
        "selected_model_route_ids": route_ids,
        "route_previews": previews,
    }


def _llm_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_LLM01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_llm01_model_route_registry_static() -> dict[str, Any]:
    errors: list[str] = []
    routes = list_model_routes_from_policy_pack_v1()
    if not routes:
        errors.append("no_model_routes")
    ids = {str(r.get("model_route_id")) for r in routes}
    if "struct-v1" not in ids:
        errors.append("missing_struct_v1")
    for route in routes:
        errors.extend(validate_model_route_v1(route))
    return _llm_meta("gp08_llm01_model_route_registry", errors)


def verify_gp08_llm01_fake_adapter_determinism_static() -> dict[str, Any]:
    errors: list[str] = []
    route = get_model_route_v1("struct-v1")
    from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
        build_synthesis_prompt_context_v1,
        compute_synthesis_prompt_hash_v1,
    )

    context = build_synthesis_prompt_context_v1(
        envelope={
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        claim_slots=[{"claim_id": "clm-0001", "discourse_only": True, "claim_kind": "discourse_only"}],
        synthesis_omission_rows=[],
        retrieval_ingress={"retrieval_evidence_hits": []},
    )
    prompt_hash = compute_synthesis_prompt_hash_v1(
        prompt_template_id=str(route["prompt_template_id"]),
        prompt_template_version=int(route["prompt_template_version"]),
        context=context,
        template_variant_id="default",
    )
    adapter = FakeLlmAdapter()
    req = LlmCompletionRequestV1(
        model_route_id="struct-v1",
        provider=str(route["provider"]),
        model=str(route["model"]),
        temperature=0.0,
        max_tokens=4096,
        response_format=LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1,
        prompt_hash=prompt_hash,
        context=context,
    )
    a = adapter.complete_structured_v1(req)
    b = adapter.complete_structured_v1(req)
    if a.completion_hash != b.completion_hash:
        errors.append("completion_hash_not_stable")
    return _llm_meta("gp08_llm01_fake_adapter_determinism", errors)


def verify_gp08_llm01_retrieval_legality_gate_static() -> dict[str, Any]:
    errors: list[str] = []
    skip, _ = should_skip_llm_for_retrieval_legality_v1(
        {"retrieval_legality_class": "retrieval_forbidden"},
        synthesis_intent="inspect",
        execution_partition="authoritative",
    )
    if not skip:
        errors.append("forbidden_should_skip")
    skip2, _ = should_skip_llm_for_retrieval_legality_v1(
        {"retrieval_legality_class": "retrieval_unverifiable"},
        synthesis_intent="inspect",
        execution_partition="authoritative",
    )
    if not skip2:
        errors.append("unverifiable_authoritative_should_skip")
    skip3, _ = should_skip_llm_for_retrieval_legality_v1(
        {"retrieval_legality_class": "retrieval_unverifiable"},
        synthesis_intent="audit",
        execution_partition="authoritative",
    )
    if skip3:
        errors.append("audit_should_not_skip_unverifiable")
    return _llm_meta("gp08_llm01_retrieval_legality_gate", errors)


def verify_gp08_llm01_sd_mapping_static() -> dict[str, Any]:
    errors: list[str] = []
    adapter = FakeLlmAdapter()
    route = get_model_route_v1("struct-v1")
    base_context: dict[str, Any] = {
        "synthesis_policy_pack_digest": "a" * 64,
        "hit_digests_sorted": [],
        "synthesis_omission_rows": [],
        "claim_slot_plan": [],
    }
    for simulate, expected_sd in (
        ("timeout", SD_LLM_TIMEOUT_V1),
        ("policy", SD_LLM_POLICY_V1),
        ("schema", SD_LLM_SCHEMA_V1),
    ):
        _, _, sd_rows, schema_failed = _invoke_route_v1(
            model_route=route,
            prompt_hash="sha256:" + "a" * 64,
            context=base_context,
            simulate=simulate,
            adapter=adapter,
        )
        codes = {str(r.get("sd_code")) for r in sd_rows}
        if expected_sd not in codes and not (expected_sd == SD_LLM_SCHEMA_V1 and schema_failed):
            errors.append(f"expected_sd:{expected_sd}:got:{sorted(codes)}")
    return _llm_meta("gp08_llm01_sd_mapping", errors)
