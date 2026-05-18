"""Phase 08 P08-12 — prompt assembly law (**SYN-PRM-01..04**, **G-P08-PRM-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-law-system.md`` §Prompts.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
    compute_retrieval_hit_digest_v1,
    normalize_retrieval_hits_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import compute_claim_slot_plan_digest_v1

PHASE08_SYNTHESIS_PROMPT_ASSEMBLY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_PRM01_GATE_ID_V1: Final[str] = "G-P08-PRM-01"

PHASE08_PROMPT_ASSEMBLY_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-law-system.md"
)

_TEMPLATE_REQUIRED_FIELDS_V1: Final[tuple[str, ...]] = (
    "prompt_template_id",
    "prompt_template_version",
    "allowed_variant_ids",
    "default_variant_id",
    "system_instruction",
)


class SynthesisPromptAssemblyError(ValueError):
    """Fail-closed synthesis prompt template / hash law."""

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


def _repo_root_v1() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "synthesis" / "templates").is_dir():
            return root
    return start.parents[6]


def _template_file_path_v1(prompt_template_id: str, prompt_template_version: int) -> Path:
    return (
        _repo_root_v1()
        / "DOCS"
        / "cortex"
        / "synthesis"
        / "templates"
        / f"{prompt_template_id}.v{prompt_template_version}.json"
    )


def load_synthesis_prompt_template_v1(
    *,
    prompt_template_id: str,
    prompt_template_version: int,
) -> dict[str, Any]:
    """Load registered prompt template body from doctrine templates directory."""
    path = _template_file_path_v1(prompt_template_id, prompt_template_version)
    if not path.is_file():
        raise SynthesisPromptAssemblyError(
            "prompt_template_not_found",
            detail={
                "prompt_template_id": prompt_template_id,
                "prompt_template_version": prompt_template_version,
                "path": str(path),
            },
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SynthesisPromptAssemblyError("invalid_prompt_template")
    violations = validate_synthesis_prompt_template_v1(raw)
    if violations:
        raise SynthesisPromptAssemblyError(
            "invalid_prompt_template",
            detail={"violations": violations, "path": str(path)},
        )
    if str(raw.get("prompt_template_id")) != prompt_template_id:
        raise SynthesisPromptAssemblyError("prompt_template_id_mismatch")
    if int(raw.get("prompt_template_version", -1)) != prompt_template_version:
        raise SynthesisPromptAssemblyError("prompt_template_version_mismatch")
    return raw


def validate_synthesis_prompt_template_v1(template: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in _TEMPLATE_REQUIRED_FIELDS_V1:
        if template.get(field) in (None, ""):
            errors.append(f"missing:{field}")
    variants = template.get("allowed_variant_ids")
    if not isinstance(variants, list) or not variants:
        errors.append("allowed_variant_ids_must_be_nonempty_list")
    elif template.get("default_variant_id") not in variants:
        errors.append("default_variant_not_in_allowed_variant_ids")
    return errors


def list_synthesis_prompt_templates_v1() -> list[dict[str, Any]]:
    """Scan ``DOCS/cortex/synthesis/templates/*.v*.json`` registry."""
    templates_dir = _repo_root_v1() / "DOCS" / "cortex" / "synthesis" / "templates"
    if not templates_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(templates_dir.glob("*.v*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            out.append(dict(raw))
    return out


def resolve_template_variant_id_v1(
    *,
    prompt_template_id: str,
    template: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> str:
    """**SYN-PRM-04** — operator override must be a registered variant id, never raw text."""
    allowed = {str(v) for v in (template.get("allowed_variant_ids") or [])}
    default = str(template.get("default_variant_id") or "default")
    overrides = envelope.get("synthesis_prompt_overrides")
    if isinstance(overrides, Mapping):
        for key, value in overrides.items():
            if str(key) == prompt_template_id and isinstance(value, str):
                variant = value.strip()
                if variant not in allowed:
                    raise SynthesisPromptAssemblyError(
                        "invalid_template_variant_override",
                        detail={
                            "prompt_template_id": prompt_template_id,
                            "template_variant_id": variant,
                            "allowed_variant_ids": sorted(allowed),
                        },
                    )
                return variant
    if default not in allowed:
        raise SynthesisPromptAssemblyError("invalid_template_default_variant")
    return default


def build_synthesis_prompt_context_v1(
    *,
    envelope: Mapping[str, Any],
    claim_slots: Sequence[Mapping[str, Any]],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """**SYN-PRM-02** — deterministic prompt context (pins only, no NL queries)."""
    policy_digest = str(
        envelope.get("_synthesis_policy_pack_digest")
        or envelope.get("synthesis_policy_pack_digest")
        or synthesis_policy_pack_digest_v1(
            policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
        ),
    )
    hits = []
    if isinstance(retrieval_ingress, Mapping):
        hits = normalize_retrieval_hits_v1(retrieval_ingress)
    hit_digests = sorted(
        compute_retrieval_hit_digest_v1(hit)
        for hit in hits
        if isinstance(hit, Mapping)
    )
    omission_rows: list[dict[str, Any]] = []
    for row in synthesis_omission_rows:
        if not isinstance(row, Mapping):
            continue
        omission_rows.append(
            {
                "sd_code": str(row.get("sd_code") or row.get("synthesis_omission_class") or ""),
                "reason": str(row.get("reason") or ""),
            },
        )
    omission_rows.sort(key=lambda r: (r["sd_code"], r["reason"]))
    slots: list[dict[str, Any]] = []
    for row in claim_slots:
        if not isinstance(row, Mapping):
            continue
        slots.append(
            {
                "claim_id": row.get("claim_id"),
                "claim_kind": row.get("claim_kind"),
                "citation_placeholders": list(row.get("citation_placeholders") or []),
                "discourse_only": bool(row.get("discourse_only")),
            },
        )
    slots.sort(key=lambda r: str(r.get("claim_id") or ""))
    return {
        "synthesis_policy_pack_digest": policy_digest,
        "hit_digests_sorted": hit_digests,
        "synthesis_omission_rows": omission_rows,
        "claim_slot_plan": slots,
        "claim_slot_plan_digest": compute_claim_slot_plan_digest_v1(claim_slots),
        "synthesis_workload_class": envelope.get("synthesis_workload_class"),
        "synthesis_intent": envelope.get("synthesis_intent"),
        "execution_partition": envelope.get("execution_partition"),
    }


def compute_synthesis_prompt_hash_v1(
    *,
    prompt_template_id: str,
    prompt_template_version: int,
    context: Mapping[str, Any],
    template_variant_id: str,
) -> str:
    """**SYN-PRM-03** — ``sha256(canonical_json({template_version, variant, context}))``."""
    body = {
        "prompt_template_id": prompt_template_id,
        "prompt_template_version": int(prompt_template_version),
        "template_variant_id": template_variant_id,
        "context": context,
    }
    return hash_reasoning_canonical_json_sha256_v1(body)


def assemble_synthesis_prompt_for_route_v1(
    *,
    envelope: Mapping[str, Any],
    model_route: Mapping[str, Any],
    claim_slots: Sequence[Mapping[str, Any]],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Assemble one route-bound prompt package (**SYN-PRM-01**)."""
    template_id = str(model_route["prompt_template_id"])
    template_version = int(model_route["prompt_template_version"])
    template = load_synthesis_prompt_template_v1(
        prompt_template_id=template_id,
        prompt_template_version=template_version,
    )
    variant_id = resolve_template_variant_id_v1(
        prompt_template_id=template_id,
        template=template,
        envelope=envelope,
    )
    context = build_synthesis_prompt_context_v1(
        envelope=envelope,
        claim_slots=claim_slots,
        synthesis_omission_rows=synthesis_omission_rows,
        retrieval_ingress=retrieval_ingress,
    )
    prompt_hash = compute_synthesis_prompt_hash_v1(
        prompt_template_id=template_id,
        prompt_template_version=template_version,
        context=context,
        template_variant_id=variant_id,
    )
    return {
        "model_route_id": str(model_route.get("model_route_id") or ""),
        "prompt_template_id": template_id,
        "prompt_template_version": template_version,
        "template_variant_id": variant_id,
        "prompt_hash": prompt_hash,
        "context": context,
        "assembled_prompt": {
            "system_instruction": str(template.get("system_instruction") or ""),
            "template_variant_id": variant_id,
            "output_schema_ref": template.get("output_schema_ref"),
            "context": context,
        },
    }


def assemble_synthesis_prompts_for_job_v1(
    *,
    envelope: Mapping[str, Any],
    claim_slots: Sequence[Mapping[str, Any]],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """ASSEMBLE phase — all selected model routes receive pinned prompt packages."""
    from vector.domains.cortex.synthesis.synthesis_llm_router import (
        get_model_route_v1,
        select_model_route_ids_for_job_v1,
    )

    pack = load_synthesis_policy_pack_v1(
        policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
    )
    route_ids = select_model_route_ids_for_job_v1(envelope, claim_slots=claim_slots)
    assemblies: list[dict[str, Any]] = []
    for route_id in route_ids:
        route = get_model_route_v1(route_id, pack=pack)
        assemblies.append(
            assemble_synthesis_prompt_for_route_v1(
                envelope=envelope,
                model_route=route,
                claim_slots=claim_slots,
                synthesis_omission_rows=synthesis_omission_rows,
                retrieval_ingress=retrieval_ingress,
            ),
        )
    return assemblies


def build_synthesis_prompt_template_catalog_v1() -> dict[str, Any]:
    """Admin doctrine catalog — registered prompt templates."""
    from vector.domains.cortex.synthesis.synthesis_llm_router import (
        list_model_routes_from_policy_pack_v1,
    )

    templates = list_synthesis_prompt_templates_v1()
    routes = list_model_routes_from_policy_pack_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_prompt_templates_v1",
        "phase08_synthesis_prompt_assembly_runtime_schema_version": (
            PHASE08_SYNTHESIS_PROMPT_ASSEMBLY_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_PRM01_GATE_ID_V1,
        "spec_ref": PHASE08_PROMPT_ASSEMBLY_SPEC_REF_V1,
        "syn_prm_rules": ["SYN-PRM-01", "SYN-PRM-02", "SYN-PRM-03", "SYN-PRM-04"],
        "prompt_templates": templates,
        "model_route_template_bindings": [
            {
                "model_route_id": r.get("model_route_id"),
                "prompt_template_id": r.get("prompt_template_id"),
                "prompt_template_version": r.get("prompt_template_version"),
            }
            for r in routes
            if isinstance(r, Mapping)
        ],
    }


def build_synthesis_prompt_assembly_preview_v1(
    envelope: Mapping[str, Any],
    *,
    claim_slots: Sequence[Mapping[str, Any]] | None = None,
    synthesis_omission_rows: Sequence[Mapping[str, Any]] | None = None,
    retrieval_ingress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Admin preview — prompt hashes without LLM invocation."""
    assemblies = assemble_synthesis_prompts_for_job_v1(
        envelope=envelope,
        claim_slots=list(claim_slots or []),
        synthesis_omission_rows=list(synthesis_omission_rows or []),
        retrieval_ingress=retrieval_ingress,
    )
    return {
        "surface_kind": "synthesis_prompt_assembly_preview",
        "gate_id": GP08_PRM01_GATE_ID_V1,
        "prompt_assembly_count": len(assemblies),
        "prompt_assemblies": assemblies,
        "prompt_hashes": sorted(a["prompt_hash"] for a in assemblies if a.get("prompt_hash")),
    }


def _prm_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_PRM01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_prm01_template_registry_static() -> dict[str, Any]:
    errors: list[str] = []
    templates = list_synthesis_prompt_templates_v1()
    if len(templates) < 1:
        errors.append("no_templates_registered")
    ids = {str(t.get("prompt_template_id")) for t in templates}
    for required in (
        "synthesis_struct_default",
        "synthesis_narrate_default",
        "synthesis_audit_default",
    ):
        if required not in ids:
            errors.append(f"missing_template:{required}")
    for template in templates:
        errors.extend(validate_synthesis_prompt_template_v1(template))
    return _prm_meta("gp08_prm01_template_registry", errors)


def verify_gp08_prm01_prompt_hash_stable_static() -> dict[str, Any]:
    errors: list[str] = []
    env: dict[str, Any] = {
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "synthesis_policy_pack_id": "SynthesisPolicyPackV1_Default",
    }
    ctx = build_synthesis_prompt_context_v1(
        envelope=env,
        claim_slots=[{"claim_id": "clm-0001", "claim_kind": "discourse_only", "discourse_only": True}],
        synthesis_omission_rows=[],
        retrieval_ingress={"retrieval_evidence_hits": []},
    )
    a = compute_synthesis_prompt_hash_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
        context=ctx,
        template_variant_id="default",
    )
    b = compute_synthesis_prompt_hash_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
        context=ctx,
        template_variant_id="default",
    )
    if a != b:
        errors.append("prompt_hash_not_stable")
    if len(a) != 64:
        errors.append("prompt_hash_not_sha256_hex")
    return _prm_meta("gp08_prm01_prompt_hash_stable", errors)


def verify_gp08_prm01_context_required_fields_static() -> dict[str, Any]:
    errors: list[str] = []
    env = {
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
    }
    ctx = build_synthesis_prompt_context_v1(
        envelope=env,
        claim_slots=[],
        synthesis_omission_rows=[{"sd_code": "SD-SCOPE-EMPTY", "reason": "test"}],
        retrieval_ingress={
            "retrieval_evidence_hits": [
                {"retrieval_lookup_id": "sha256:" + "a" * 64, "evidence_legality_class": "replay_safe"},
            ],
        },
    )
    for key in (
        "synthesis_policy_pack_digest",
        "hit_digests_sorted",
        "synthesis_omission_rows",
        "claim_slot_plan",
    ):
        if key not in ctx:
            errors.append(f"missing_context_field:{key}")
    if not ctx.get("hit_digests_sorted"):
        errors.append("expected_hit_digest")
    return _prm_meta("gp08_prm01_context_required_fields", errors)


def verify_gp08_prm01_variant_override_law_static() -> dict[str, Any]:
    errors: list[str] = []
    template = load_synthesis_prompt_template_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
    )
    variant = resolve_template_variant_id_v1(
        prompt_template_id="synthesis_struct_default",
        template=template,
        envelope={
            "synthesis_prompt_overrides": {
                "synthesis_struct_default": "variant_pin_a",
            },
        },
    )
    if variant != "variant_pin_a":
        errors.append("variant_override_not_applied")
    try:
        resolve_template_variant_id_v1(
            prompt_template_id="synthesis_struct_default",
            template=template,
            envelope={
                "synthesis_prompt_overrides": {
                    "synthesis_struct_default": "not_a_registered_variant",
                },
            },
        )
        errors.append("expected_invalid_variant_rejection")
    except SynthesisPromptAssemblyError as exc:
        if exc.code != "invalid_template_variant_override":
            errors.append(f"unexpected_error_code:{exc.code}")
    return _prm_meta("gp08_prm01_variant_override_law", errors)
