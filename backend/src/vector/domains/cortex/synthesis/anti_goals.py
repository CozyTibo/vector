"""Phase 08 P08-02 — anti-goals / forbidden synthesis cognition (SIL package).

Normative: ``DOCS/cortex/synthesis/phase-08-anti-goals-doctrine.md``.
``G-P08-ANTI-01``: synthesis law packages — no banned cognition / LLM / embedding imports.
``G-P08-ANTI-02``: import boundary + ingress token rejection on job envelopes.
``G-P08-SCHEMA-01``: denylist keys on ``SynthesisJobEnvelopeV1``-shaped bodies.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.traversal.anti_goals import (
    list_forbidden_cognition_key_violations as list_octs_forbidden_cognition_key_violations,
)

PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1: Final[str] = "synthesis_forbidden"

# G-P08-SCHEMA-01 — doctrine static denylist (exact lowercase keys).
SYNTHESIS_JOB_ENVELOPE_FORBIDDEN_KEYS_LOWER_V1: Final[frozenset[str]] = frozenset(
    {
        "embedding",
        "embeddings",
        "similarity",
        "vector_search",
        "semantic_search",
        "natural_language_query",
        "query_text",
        "rag",
        "rerank",
        "chat",
        "messages",
        "conversation_id",
        "tool_calls",
        "agent",
        "autonomous",
        "recommendation",
        "recommendations",
        "confidence_score",
        "hidden_reasoning",
        "chain_of_thought",
        "llm",
        "summary",
        "summaries",
        "prompt",
        "system_prompt",
        "user_message",
        "assistant_message",
    }
)

SYNTHESIS_ARTIFACT_FORBIDDEN_TOP_LEVEL_KEYS_LOWER_V1: Final[frozenset[str]] = frozenset(
    {
        "answer",
        "summary",
        "bullets",
        "recommendation",
        "action_items",
        "hypothesis",
        "prediction",
        "sentiment",
        "embedding",
        "similarity",
        "raw_llm_output",
    }
)

_SELECTION_POLICY_CAP_KEYS_LOWER_V1: Final[frozenset[str]] = frozenset(
    {
        "max_claims",
        "max_retrieval_subqueries",
        "max_llm_tokens",
        "max_wall_ms",
        "max_artifact_json_bytes",
    },
)

_SYNTHESIS_EXTRA_KEY_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "semantic_search",
    "vector_search",
    "natural_language",
    "chain_of_thought",
    "hidden_reasoning",
    "conversation_id",
    "rerank",
    "embedding",
)

_SYNTHESIS_INGRESS_STRING_FIELD_NAMES_LOWER: Final[frozenset[str]] = frozenset(
    {
        "ask",
        "free_text",
        "natural_language_query",
        "nl_query",
        "prompt",
        "query",
        "query_text",
        "search_text",
        "user_message",
        "assistant_message",
    }
)

_SYNTHESIS_INGRESS_BLOCKED_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "semantic search",
    "vector search",
    "ask anything",
    "natural language",
    "hybrid rag",
    "chain of thought",
    "gpt-",
    "openai",
    "embedding",
    "similarity",
    "rerank",
    "chat completion",
)

_TEMPLATE_VARIANT_ID_RE_V1: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

# SYN-ANTI-01 — closed authoritative job envelope algebra (top-level keys only).
SYNTHESIS_AUTHORITATIVE_JOB_ENVELOPE_TOP_LEVEL_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "tenant_id",
        "synthesis_workload_class",
        "synthesis_intent",
        "execution_partition",
        "retrieval_scope",
        "retrieval_pins",
        "synthesis_policy_pack_id",
        "selection_policy",
        "idempotency_key",
        "substrate_pipeline_run_id",
        "pinned_retrieval_receipt",
        "synthesis_prompt_overrides",
        "expected_synthesis_job_replay_identity",
        "replay_pins",
    }
)

SYNTHESIS_AUTHORITATIVE_ARTIFACT_TOP_LEVEL_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "artifact_id",
        "artifact_kind",
        "artifact_digest",
        "synthesis_legality_class",
        "synthesis_job_replay_identity",
        "retrieval_query_replay_identity",
        "retrieval_lookup_id",
        "synthesis_policy_pack_digest",
        "synthesis_publication_epoch",
        "evidence_scope_summary",
        "claims",
        "narrative_blocks",
        "synthesis_citation_envelope",
        "synthesis_omission_rows",
        "synthesis_degradation_rollup",
        "synthesis_legality_posture",
        "lineage_chain_digest",
        "llm_trace_refs",
        "retrieval_receipt_embed",
        "non_authoritative",
        "tenant_id",
        "synthesis_workload_class",
        "execution_trace",
        "receipt_digest",
        "tcre_binding_envelope",
        "retrieval_binding_envelope",
        "degradation_propagation_chain",
        "upstream_rollup",
    }
)

_EXPLORATION_PARTITION_EXTRA_TOP_LEVEL_KEYS_V1: Final[frozenset[str]] = frozenset(
    {"non_authoritative"}
)

_BANNED_IMPORT_ROOTS: Final[tuple[str, ...]] = (
    "anthropic",
    "chromadb",
    "faiss",
    "langchain",
    "litellm",
    "openai",
    "pinecone",
    "sentence_transformers",
    "sklearn",
    "tiktoken",
    "torch",
    "tensorflow",
    "transformers",
)

_FORBIDDEN_SYNTHESIS_LAW_IMPORT_MODULES: Final[tuple[str, ...]] = (
    "vector.domains.cortex.retrieval.query_execution",
)


class SynthesisAntiGoalViolationError(ValueError):
    """Raised when synthesis input/output violates Phase 08 anti-goals."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail or {})


class SynthesisCognitionLeakageError(SynthesisAntiGoalViolationError):
    """Raised when synthesis JSON smuggles forbidden cognition-shaped keys."""


def _synthesis_extra_key_violations(key: str) -> list[str]:
    lk = key.lower()
    if lk in _SELECTION_POLICY_CAP_KEYS_LOWER_V1:
        return []
    out: list[str] = []
    if lk in SYNTHESIS_JOB_ENVELOPE_FORBIDDEN_KEYS_LOWER_V1:
        out.append("forbidden_schema_denylist_key")
    if lk in SYNTHESIS_ARTIFACT_FORBIDDEN_TOP_LEVEL_KEYS_LOWER_V1:
        out.append("forbidden_artifact_top_level_key")
    for sub in _SYNTHESIS_EXTRA_KEY_SUBSTRINGS_LOWER:
        if sub in lk:
            out.append(f"forbidden_synthesis_key_substring:{sub}")
            break
    return out


def list_synthesis_forbidden_cognition_key_violations(obj: Any, *, path: str = "") -> list[str]:
    """Return paths for **OCTS** + **SIL** forbidden cognition keys (recursive mapping walk)."""
    base = [
        hit
        for hit in list_octs_forbidden_cognition_key_violations(obj, path=path)
        if not hit.startswith("selection_policy.")
    ]
    extra = _list_synthesis_extra_only_recursive(obj, path=path)
    return base + extra


def _list_synthesis_extra_only_recursive(obj: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(obj, Mapping):
        for raw_k, v in obj.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{path}.{raw_k}" if path else raw_k
            for reason in _synthesis_extra_key_violations(raw_k):
                violations.append(f"{prefix}:{reason}")
            violations.extend(_list_synthesis_extra_only_recursive(v, path=prefix))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(_list_synthesis_extra_only_recursive(item, path=f"{path}[{i}]"))
    return violations


def validate_synthesis_canonical_json_mapping_no_cognition_leakage(body: Mapping[str, Any]) -> None:
    """Reject synthesis JSON that includes forbidden cognition keys (P08-02)."""
    hits = list_synthesis_forbidden_cognition_key_violations(body)
    if hits:
        msg = "synthesis cognition leakage in canonical JSON: " + "; ".join(hits[:16])
        if len(hits) > 16:
            msg += f"; …(+{len(hits) - 16} more)"
        raise SynthesisCognitionLeakageError(
            SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"violations": hits[:32]},
        )


def _ingress_string_field_violations(key: str, value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    lk = key.lower()
    if lk not in _SYNTHESIS_INGRESS_STRING_FIELD_NAMES_LOWER:
        return []
    norm = value.strip().lower()
    if not norm:
        return []
    out: list[str] = []
    for sub in _SYNTHESIS_INGRESS_BLOCKED_SUBSTRINGS_LOWER:
        if sub in norm:
            out.append(f"forbidden_ingress_token:{sub}")
    return out


def _synthesis_prompt_override_violations(body: Mapping[str, Any]) -> list[str]:
    raw = body.get("synthesis_prompt_overrides")
    if raw is None:
        return []
    if not isinstance(raw, Mapping):
        return ["synthesis_prompt_overrides:must_be_object"]
    violations: list[str] = []
    for key, value in raw.items():
        if not isinstance(key, str):
            violations.append("synthesis_prompt_overrides:non_string_key")
            continue
        if not _TEMPLATE_VARIANT_ID_RE_V1.match(key):
            violations.append(f"synthesis_prompt_overrides.{key}:invalid_template_variant_id")
        if isinstance(value, str) and ("\n" in value or len(value) > 128):
            violations.append(f"synthesis_prompt_overrides.{key}:raw_prompt_text_forbidden")
        elif not isinstance(value, str):
            violations.append(f"synthesis_prompt_overrides.{key}:variant_id_must_be_string")
    return violations


def list_synthesis_job_envelope_ingress_violations(body: Mapping[str, Any]) -> list[str]:
    """G-P08-ANTI-02 — forbidden keys + blocked NL-search tokens on envelope-shaped bodies."""
    violations = list_synthesis_forbidden_cognition_key_violations(body)
    if isinstance(body, Mapping):
        for raw_k, v in body.items():
            if not isinstance(raw_k, str):
                continue
            violations.extend(_ingress_string_field_violations(raw_k, v))
            if isinstance(v, Mapping):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_k, str):
                        violations.extend(_ingress_string_field_violations(sub_k, sub_v))
        violations.extend(_synthesis_prompt_override_violations(body))
    return violations


def enforce_synthesis_job_envelope_anti_goals_v1(body: Mapping[str, Any]) -> None:
    """Validate admin/API synthesis job bodies before execution (P08-02)."""
    hits = list_synthesis_job_envelope_ingress_violations(body)
    if hits:
        raise SynthesisAntiGoalViolationError(
            SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"violations": hits[:32]},
        )


def list_synthesis_authoritative_output_algebra_violations(
    body: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
    artifact: bool = False,
) -> list[str]:
    """SYN-ANTI-01 — top-level keys must stay inside the closed authoritative algebra."""
    allowed = (
        set(SYNTHESIS_AUTHORITATIVE_ARTIFACT_TOP_LEVEL_KEYS_V1)
        if artifact
        else set(SYNTHESIS_AUTHORITATIVE_JOB_ENVELOPE_TOP_LEVEL_KEYS_V1)
    )
    if execution_partition.strip().lower() == "exploration":
        allowed |= _EXPLORATION_PARTITION_EXTRA_TOP_LEVEL_KEYS_V1
    violations: list[str] = []
    for raw_k in body:
        if not isinstance(raw_k, str):
            violations.append(f"{raw_k!r}:non_string_top_level_key")
            continue
        if raw_k not in allowed:
            violations.append(f"{raw_k}:forbidden_top_level_output_key")
    return violations


def validate_synthesis_authoritative_job_envelope_algebra_v1(
    body: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
) -> None:
    hits = list_synthesis_authoritative_output_algebra_violations(
        body, execution_partition=execution_partition, artifact=False
    )
    if hits:
        raise SynthesisAntiGoalViolationError(
            SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"algebra_violations": hits[:32]},
        )


def validate_synthesis_authoritative_artifact_algebra_v1(
    body: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
) -> None:
    hits = list_synthesis_authoritative_output_algebra_violations(
        body, execution_partition=execution_partition, artifact=True
    )
    if hits:
        raise SynthesisAntiGoalViolationError(
            SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"algebra_violations": hits[:32]},
        )


def _synthesis_package_dir() -> Path:
    return Path(__file__).resolve().parent


def _is_adapter_law_exempt_path(path: Path) -> bool:
    parts = path.parts
    return "adapters" in parts


def _is_retrieval_client_exempt_path(path: Path) -> bool:
    return path.name == "synthesis_retrieval_client.py"


def iter_synthesis_package_py_files(*, include_adapters: bool = False) -> Iterable[Path]:
    root = _synthesis_package_dir()
    for path in sorted(root.rglob("*.py")):
        parts = path.parts
        if "__pycache__" in parts:
            continue
        if not include_adapters and _is_adapter_law_exempt_path(path):
            continue
        if _is_retrieval_client_exempt_path(path):
            continue
        yield path


def list_synthesis_package_banned_import_violations() -> list[str]:
    """Scan ``vector.domains.cortex.synthesis`` law tree for banned vendor / bypass imports."""
    violations: list[str] = []
    root = _synthesis_package_dir()
    for path in iter_synthesis_package_py_files(include_adapters=False):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path.relative_to(root)}:syntax_error:{exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = (alias.name or "").split(".")[0].lower()
                    full = alias.name or ""
                    if mod in _BANNED_IMPORT_ROOTS:
                        violations.append(
                            f"{path}:{getattr(node, 'lineno', 0)}:import:{alias.name}"
                        )
                    for forbidden in _FORBIDDEN_SYNTHESIS_LAW_IMPORT_MODULES:
                        if full == forbidden or full.startswith(f"{forbidden}."):
                            violations.append(
                                f"{path}:{getattr(node, 'lineno', 0)}:import:{full}"
                            )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split(".")[0].lower()
                    if mod in _BANNED_IMPORT_ROOTS:
                        violations.append(
                            f"{path}:{getattr(node, 'lineno', 0)}:from:{node.module}"
                        )
                    for forbidden in _FORBIDDEN_SYNTHESIS_LAW_IMPORT_MODULES:
                        if node.module == forbidden or node.module.startswith(f"{forbidden}."):
                            violations.append(
                                f"{path}:{getattr(node, 'lineno', 0)}:from:{node.module}"
                            )
    return violations


def build_synthesis_anti_goals_doctrine_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for forbidden cognition keys and import boundary (P08-02)."""
    return {
        "surface_kind": "doctrine_catalog",
        "synthesis_anti_goals_catalog_runtime_schema_version": int(
            PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": "DOCS/cortex/synthesis/phase-08-anti-goals-doctrine.md",
        "synthesis_forbidden_legality_class": SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
        "gate_ids": ["G-P08-ANTI-01", "G-P08-ANTI-02", "G-P08-SCHEMA-01"],
        "job_envelope_forbidden_keys": sorted(SYNTHESIS_JOB_ENVELOPE_FORBIDDEN_KEYS_LOWER_V1),
        "artifact_forbidden_top_level_keys": sorted(
            SYNTHESIS_ARTIFACT_FORBIDDEN_TOP_LEVEL_KEYS_LOWER_V1,
        ),
        "banned_import_roots": list(_BANNED_IMPORT_ROOTS),
        "forbidden_law_import_modules": list(_FORBIDDEN_SYNTHESIS_LAW_IMPORT_MODULES),
        "authoritative_job_envelope_top_level_keys": sorted(
            SYNTHESIS_AUTHORITATIVE_JOB_ENVELOPE_TOP_LEVEL_KEYS_V1,
        ),
        "authoritative_artifact_top_level_keys": sorted(
            SYNTHESIS_AUTHORITATIVE_ARTIFACT_TOP_LEVEL_KEYS_V1,
        ),
        "synthesis_prompt_overrides_rule": (
            "registered_template_variant_ids_only_no_raw_operator_prompt_text"
        ),
    }


def verify_gp08_anti01_synthesis_package_static() -> dict[str, Any]:
    """``G-P08-ANTI-01`` — banned cognition / ML / LLM imports under synthesis law packages."""
    import_errors = list_synthesis_package_banned_import_violations()
    passed = len(import_errors) == 0
    return {
        "id": "G-P08-ANTI-01",
        "name": "synthesis_package_banned_imports",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase08_anti_goals_runtime_schema_version": PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "import_violations": import_errors,
        },
    }


def verify_gp08_anti02_synthesis_ingress_token_rejection_static() -> dict[str, Any]:
    """``G-P08-ANTI-02`` — job envelope must reject smuggled cognition / NL search tokens."""
    errors: list[str] = []

    illegal = {"schema_version": 1, "synthesis_workload_class": "pipeline_default", "chat": True}
    if not list_synthesis_job_envelope_ingress_violations(illegal):
        errors.append("expected_violation_for_chat_key")

    illegal_nl = {"query_text": "semantic search across all teams"}
    if not list_synthesis_job_envelope_ingress_violations(illegal_nl):
        errors.append("expected_violation_for_semantic_search_query_text")

    illegal_prompt = {
        "synthesis_prompt_overrides": {
            "exec_brief_v1": "You are a helpful assistant.\nSummarize everything.",
        }
    }
    if not list_synthesis_job_envelope_ingress_violations(illegal_prompt):
        errors.append("expected_violation_for_raw_prompt_override")

    legal = {
        "schema_version": 1,
        "synthesis_workload_class": "pipeline_default",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_pins": {"retrieval_lookup_id": "sha256:00"},
    }
    if list_synthesis_job_envelope_ingress_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_synthesis_job_envelope_ingress_violations(legal)}"
        )

    try:
        enforce_synthesis_job_envelope_anti_goals_v1(legal)
    except SynthesisAntiGoalViolationError as exc:
        errors.append(f"unexpected_raise_on_legal_stub:{exc}")

    passed = len(errors) == 0
    return {
        "id": "G-P08-ANTI-02",
        "name": "synthesis_ingress_token_rejection",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase08_anti_goals_runtime_schema_version": PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def verify_gp08_schema01_synthesis_job_envelope_forbidden_keys_static() -> dict[str, Any]:
    """``G-P08-SCHEMA-01`` — schema denylist keys rejected on envelope bodies."""
    errors: list[str] = []

    for key in ("embedding", "chat", "rag", "hidden_reasoning", "chain_of_thought"):
        bad = {key: True}
        if not list_synthesis_forbidden_cognition_key_violations(bad):
            errors.append(f"expected_violation_for_{key}")

    legal = {
        "schema_version": 1,
        "synthesis_workload_class": "execution_understanding",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_pins": {"retrieval_lookup_id": "sha256:00"},
    }
    if list_synthesis_forbidden_cognition_key_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_synthesis_forbidden_cognition_key_violations(legal)}"
        )

    passed = len(errors) == 0
    return {
        "id": "G-P08-SCHEMA-01",
        "name": "synthesis_job_envelope_forbidden_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase08_anti_goals_runtime_schema_version": PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "forbidden_keys": sorted(SYNTHESIS_JOB_ENVELOPE_FORBIDDEN_KEYS_LOWER_V1),
            "errors": errors,
        },
    }


def synthesis_job_envelope_schema_path_v1() -> Path:
    """Normative JSON Schema path for ``SynthesisJobEnvelopeV1`` (G-P08-SCHEMA-01)."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        candidate = (
            root
            / "DOCS"
            / "cortex"
            / "synthesis"
            / "schemas"
            / "synthesis-job-envelope-v1.schema.json"
        )
        if candidate.is_file():
            return candidate
    return (
        start.parents[4]
        / "DOCS"
        / "cortex"
        / "synthesis"
        / "schemas"
        / "synthesis-job-envelope-v1.schema.json"
    )


def verify_gp08_schema01_schema_file_present_static() -> dict[str, Any]:
    path = synthesis_job_envelope_schema_path_v1()
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    errors: list[str] = []
    if not path.is_file():
        errors.append(f"missing_schema_file:{path}")
    else:
        for key in ("embedding", "chat", "rag", "hidden_reasoning", "semantic_search"):
            if key not in text:
                errors.append(f"schema_missing_forbidden_key_documentation:{key}")
    passed = len(errors) == 0
    return {
        "id": "G-P08-SCHEMA-01-file",
        "name": "synthesis_job_envelope_schema_file",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"path": str(path), "errors": errors},
    }


def verify_gp08_synthesis_json_cognition_keys_static() -> dict[str, Any]:
    """Static JSON cognition checks for SIL-shaped bodies (P08-02 doctrine)."""
    errors: list[str] = []

    illegal = {"claims": [{"summary": "blocked"}]}
    if not list_synthesis_forbidden_cognition_key_violations(illegal):
        errors.append("expected_violation_for_nested_summary")

    illegal2 = {"semantic_search": True}
    if not list_synthesis_forbidden_cognition_key_violations(illegal2):
        errors.append("expected_violation_for_semantic_search_key")

    legal = {
        "artifact_id": "00000000-0000-4000-8000-000000000001",
        "synthesis_legality_class": "synthesis_replay_safe",
        "claims": [],
        "non_authoritative": False,
    }
    if list_synthesis_forbidden_cognition_key_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_synthesis_forbidden_cognition_key_violations(legal)}"
        )

    try:
        validate_synthesis_canonical_json_mapping_no_cognition_leakage(legal)
    except SynthesisCognitionLeakageError as exc:
        errors.append(f"unexpected_raise_on_legal_stub:{exc}")

    passed = len(errors) == 0
    return {
        "id": "P08-02-json-cognition",
        "name": "synthesis_json_forbidden_cognition_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase08_anti_goals_runtime_schema_version": PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }
