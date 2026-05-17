"""Phase 07 P07-02 — anti-goals / forbidden retrieval cognition (LRE package).

Normative: ``DOCS/cortex/retrieval/phase-07-anti-goals-doctrine.md``.
``G-P07-ANTI-01``: retrieval package file tree — no banned cognition / LLM / embedding imports.
``G-P07-ANTI-02``: ingress token rejection on query envelopes and retrieval JSON bodies.
``G-P07-SCHEMA-01``: denylist keys on ``RetrievalQueryEnvelopeV1``-shaped bodies.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.traversal.anti_goals import (
    list_forbidden_cognition_key_violations as list_octs_forbidden_cognition_key_violations,
)

PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1: Final[str] = "retrieval_forbidden"

# G-P07-SCHEMA-01 / doctrine static denylist (exact lowercase keys).
_RETRIEVAL_SCHEMA_FORBIDDEN_KEYS_LOWER: Final[frozenset[str]] = frozenset(
    {
        "embedding",
        "embeddings",
        "similarity",
        "llm",
        "summary",
        "summaries",
        "recommendation",
        "recommendations",
    }
)

# Additional retrieval-specific forbidden keys (semantic search / RAG theater).
_RETRIEVAL_EXTRA_FORBIDDEN_KEYS_LOWER: Final[frozenset[str]] = frozenset(
    {
        "approximate_nearest_neighbor",
        "ask_anything",
        "free_text_query",
        "hybrid_rag",
        "natural_language_query",
        "nl_query",
        "prompt",
        "query_text",
        "rag",
        "rerank",
        "reranking",
        "semantic_rank",
        "semantic_search",
        "semantic_similarity",
        "vector_database_id",
        "vector_search",
        "relevance_score",
    }
)

_RETRIEVAL_EXTRA_KEY_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "semantic_search",
    "vector_search",
    "natural_language",
    "relevance_score",
    "rerank",
    "embedding",
)

# Ingress string fields scanned for blocked substrings (G-P07-ANTI-02).
_RETRIEVAL_INGRESS_STRING_FIELD_NAMES_LOWER: Final[frozenset[str]] = frozenset(
    {
        "ask",
        "free_text",
        "natural_language_query",
        "nl_query",
        "prompt",
        "query",
        "query_text",
        "search_text",
    }
)

_RETRIEVAL_INGRESS_BLOCKED_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "semantic search",
    "vector search",
    "ask anything",
    "natural language",
    "hybrid rag",
    "nearest neighbor",
    "gpt-",
    "openai",
    "embedding",
    "similarity",
    "rerank",
    "relevance score",
)

# RET-ANTI-01 — closed authoritative output algebra (top-level keys only).
RETRIEVAL_AUTHORITATIVE_OUTPUT_TOP_LEVEL_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_query_receipt",
        "retrieval_evidence_hits",
        "retrieval_omission_rows",
        "retrieval_degradation_rollup",
        "retrieval_legality_posture",
        "schema_version",
        "tenant_id",
        "workload_class",
        "intent",
        "retrieval_lookup_id",
        "retrieval_policy_digest",
        "retrieval_replay_identity",
        "retrieval_query_replay_identity",
        "chronology_legality_class",
        "causal_legality_class",
        "upstream_chronology_legality_class",
        "upstream_causal_legality_class",
        "retrieval_legality_class",
        "degradation_posture",
        "continuity_posture",
        "omission_summary",
        "replay_posture",
        "artifact_ref",
        "degradation_envelope",
        "lineage",
        "hits",
        "omissions",
        "ingress_provenance",
        "ingress_scope",
        "index_epoch",
        "selection_policy",
        "query_replay_identity_scope",
        "replay_equivalence_twin",
        "addressing_resolution",
        "retrieval_query_receipt",
        "execution_trace",
        "r_leg_precheck",
        "receipt_digest",
        "provenance_coverage_percent",
        "ret_prov01_missing_digests",
        "temporal_scope",
        "temporal_legality_envelope",
        "temporal_skew_audit",
        "selection_sort_trace",
        "selection_policy_profile_id",
        "cap_overflow_totals",
        "retrieval_omission_histogram",
        "retrieval_rd_rollup",
        "substrate_health_state",
        "retrieval_policy_pack_id",
        "retrieval_policy_pack_digest",
        "degradation_propagation_chain",
        "published_index_epoch",
        "index_lag_epochs",
        "tcre_binding_envelope",
        "tcre_replay_artifact_pins",
        "traversal_binding_envelope",
        "retrieval_walk_ref",
        "graph_binding_envelope",
        "graph_scope",
        "lineage_binding_envelope",
        "lineage_chain_digest",
        "retrieval_query_log",
        "reconstruction_receipt",
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


class RetrievalAntiGoalViolationError(ValueError):
    """Raised when retrieval input/output violates Phase 07 anti-goals."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail or {})


class RetrievalCognitionLeakageError(RetrievalAntiGoalViolationError):
    """Raised when retrieval JSON smuggles forbidden cognition-shaped keys."""


def _retrieval_extra_key_violations(key: str) -> list[str]:
    lk = key.lower()
    out: list[str] = []
    if lk in _RETRIEVAL_SCHEMA_FORBIDDEN_KEYS_LOWER:
        out.append("forbidden_schema_denylist_key")
    if lk in _RETRIEVAL_EXTRA_FORBIDDEN_KEYS_LOWER:
        out.append("forbidden_retrieval_exact_cognition_key")
    for sub in _RETRIEVAL_EXTRA_KEY_SUBSTRINGS_LOWER:
        if sub in lk:
            out.append(f"forbidden_retrieval_key_substring:{sub}")
            break
    return out


def list_retrieval_forbidden_cognition_key_violations(obj: Any, *, path: str = "") -> list[str]:
    """Return paths for **OCTS** + **LRE** forbidden cognition keys (recursive mapping walk)."""
    base = list_octs_forbidden_cognition_key_violations(obj, path=path)
    extra = _list_retrieval_extra_only_recursive(obj, path=path)
    return base + extra


def _list_retrieval_extra_only_recursive(obj: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(obj, Mapping):
        for raw_k, v in obj.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{path}.{raw_k}" if path else raw_k
            for reason in _retrieval_extra_key_violations(raw_k):
                violations.append(f"{prefix}:{reason}")
            violations.extend(_list_retrieval_extra_only_recursive(v, path=prefix))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(_list_retrieval_extra_only_recursive(item, path=f"{path}[{i}]"))
    return violations


def validate_retrieval_canonical_json_mapping_no_cognition_leakage(body: Mapping[str, Any]) -> None:
    """Reject retrieval JSON that includes forbidden cognition keys (P07-02)."""
    hits = list_retrieval_forbidden_cognition_key_violations(body)
    if hits:
        msg = "retrieval cognition leakage in canonical JSON: " + "; ".join(hits[:16])
        if len(hits) > 16:
            msg += f"; …(+{len(hits) - 16} more)"
        raise RetrievalCognitionLeakageError(
            RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"violations": hits[:32]},
        )


def _ingress_string_field_violations(key: str, value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    lk = key.lower()
    if lk not in _RETRIEVAL_INGRESS_STRING_FIELD_NAMES_LOWER:
        return []
    norm = value.strip().lower()
    if not norm:
        return []
    out: list[str] = []
    for sub in _RETRIEVAL_INGRESS_BLOCKED_SUBSTRINGS_LOWER:
        if sub in norm:
            out.append(f"forbidden_ingress_token:{sub}")
    return out


def list_retrieval_query_envelope_ingress_violations(body: Mapping[str, Any]) -> list[str]:
    """G-P07-ANTI-02 — forbidden keys + blocked NL-search tokens on envelope-shaped bodies."""
    violations = list_retrieval_forbidden_cognition_key_violations(body)
    if isinstance(body, Mapping):
        for raw_k, v in body.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{raw_k}" if not violations else raw_k
            violations.extend(_ingress_string_field_violations(raw_k, v))
            if isinstance(v, Mapping):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_k, str):
                        violations.extend(_ingress_string_field_violations(sub_k, sub_v))
    return violations


def enforce_retrieval_query_envelope_anti_goals_v1(body: Mapping[str, Any]) -> None:
    """Validate admin/API query bodies before retrieval execution (P07-02)."""
    hits = list_retrieval_query_envelope_ingress_violations(body)
    if hits:
        raise RetrievalAntiGoalViolationError(
            RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"violations": hits[:32]},
        )


def list_retrieval_authoritative_output_algebra_violations(
    body: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
) -> list[str]:
    """RET-ANTI-01 — top-level keys must stay inside the closed authoritative algebra."""
    allowed = set(RETRIEVAL_AUTHORITATIVE_OUTPUT_TOP_LEVEL_KEYS_V1)
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


def validate_retrieval_authoritative_output_algebra_v1(
    body: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
) -> None:
    hits = list_retrieval_authoritative_output_algebra_violations(
        body, execution_partition=execution_partition
    )
    if hits:
        raise RetrievalAntiGoalViolationError(
            RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
            detail={"algebra_violations": hits[:32]},
        )


def _retrieval_package_dir() -> Path:
    return Path(__file__).resolve().parent


def iter_retrieval_package_py_files() -> Iterable[Path]:
    root = _retrieval_package_dir()
    for path in sorted(root.rglob("*.py")):
        parts = path.parts
        if "__pycache__" in parts:
            continue
        yield path


def list_retrieval_package_banned_import_violations() -> list[str]:
    """Scan ``vector.domains.cortex.retrieval`` for ``import`` / ``from`` lines touching banned roots."""
    violations: list[str] = []
    root = _retrieval_package_dir()
    for path in iter_retrieval_package_py_files():
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
                    if mod in _BANNED_IMPORT_ROOTS:
                        violations.append(
                            f"{path}:{getattr(node, 'lineno', 0)}:import:{alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split(".")[0].lower()
                    if mod in _BANNED_IMPORT_ROOTS:
                        violations.append(
                            f"{path}:{getattr(node, 'lineno', 0)}:from:{node.module}"
                        )
    return violations


def verify_gp07_anti01_retrieval_package_static() -> dict[str, Any]:
    """``G-P07-ANTI-01`` — banned cognition / ML / LLM imports under the retrieval package."""
    import_errors = list_retrieval_package_banned_import_violations()
    passed = len(import_errors) == 0
    return {
        "id": "G-P07-ANTI-01",
        "name": "retrieval_package_banned_imports",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase07_anti_goals_runtime_schema_version": PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "import_violations": import_errors,
        },
    }


def verify_gp07_anti02_retrieval_ingress_token_rejection_static() -> dict[str, Any]:
    """``G-P07-ANTI-02`` — ingress envelope must reject smuggled cognition / NL search tokens."""
    errors: list[str] = []

    illegal = {"retrieval_lookup_id": "sha256:00", "embedding": [0.1]}
    if not list_retrieval_query_envelope_ingress_violations(illegal):
        errors.append("expected_violation_for_embedding_key")

    illegal_nl = {"query_text": "semantic search across all teams"}
    if not list_retrieval_query_envelope_ingress_violations(illegal_nl):
        errors.append("expected_violation_for_semantic_search_query_text")

    legal = {"retrieval_lookup_id": "sha256:00", "expected_replay_identity": "rid1"}
    if list_retrieval_query_envelope_ingress_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_retrieval_query_envelope_ingress_violations(legal)}"
        )

    try:
        enforce_retrieval_query_envelope_anti_goals_v1(legal)
    except RetrievalAntiGoalViolationError as exc:
        errors.append(f"unexpected_raise_on_legal_stub:{exc}")

    passed = len(errors) == 0
    return {
        "id": "G-P07-ANTI-02",
        "name": "retrieval_ingress_token_rejection",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase07_anti_goals_runtime_schema_version": PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def verify_gp07_schema01_retrieval_query_envelope_forbidden_keys_static() -> dict[str, Any]:
    """``G-P07-SCHEMA-01`` — schema denylist keys rejected on envelope bodies."""
    errors: list[str] = []

    for key in ("embedding", "similarity", "llm", "summary", "recommendation"):
        bad = {key: True}
        if not list_retrieval_forbidden_cognition_key_violations(bad):
            errors.append(f"expected_violation_for_{key}")

    legal = {
        "schema_version": 1,
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {"retrieval_lookup_id": "sha256:00"},
    }
    if list_retrieval_forbidden_cognition_key_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_retrieval_forbidden_cognition_key_violations(legal)}"
        )

    passed = len(errors) == 0
    return {
        "id": "G-P07-SCHEMA-01",
        "name": "retrieval_query_envelope_forbidden_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase07_anti_goals_runtime_schema_version": PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "forbidden_keys": sorted(_RETRIEVAL_SCHEMA_FORBIDDEN_KEYS_LOWER),
            "errors": errors,
        },
    }


def verify_gp07_retrieval_json_cognition_keys_static() -> dict[str, Any]:
    """Static JSON cognition checks for LRE-shaped bodies (P07-02 doctrine)."""
    errors: list[str] = []

    illegal = {"hits": [{"summary": "blocked"}]}
    if not list_retrieval_forbidden_cognition_key_violations(illegal):
        errors.append("expected_violation_for_nested_summary")

    illegal2 = {"semantic_search": True}
    if not list_retrieval_forbidden_cognition_key_violations(illegal2):
        errors.append("expected_violation_for_semantic_search_key")

    legal = {
        "retrieval_lookup_id": "sha256:00",
        "retrieval_legality_class": "retrieval_replay_safe",
        "hits": [],
        "omissions": [],
    }
    if list_retrieval_forbidden_cognition_key_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_retrieval_forbidden_cognition_key_violations(legal)}"
        )

    try:
        validate_retrieval_canonical_json_mapping_no_cognition_leakage(legal)
    except RetrievalCognitionLeakageError as exc:
        errors.append(f"unexpected_raise_on_legal_stub:{exc}")

    passed = len(errors) == 0
    return {
        "id": "P07-02-json-cognition",
        "name": "retrieval_json_forbidden_cognition_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase07_anti_goals_runtime_schema_version": PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def retrieval_query_envelope_schema_path_v1() -> Path:
    """Normative JSON Schema path for ``RetrievalQueryEnvelopeV1`` (G-P07-SCHEMA-01)."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        candidate = (
            root / "DOCS" / "cortex" / "retrieval" / "schemas" / "retrieval-query-envelope-v1.schema.json"
        )
        if candidate.is_file():
            return candidate
    return start.parents[4] / "DOCS" / "cortex" / "retrieval" / "schemas" / "retrieval-query-envelope-v1.schema.json"


def verify_gp07_schema01_schema_file_present_static() -> dict[str, Any]:
    path = retrieval_query_envelope_schema_path_v1()
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    errors: list[str] = []
    if not path.is_file():
        errors.append(f"missing_schema_file:{path}")
    else:
        for key in ("embedding", "similarity", "llm", "summary", "recommendation"):
            if key not in text:
                errors.append(f"schema_missing_forbidden_key_documentation:{key}")
    passed = len(errors) == 0
    return {
        "id": "G-P07-SCHEMA-01-file",
        "name": "retrieval_query_envelope_schema_file",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"path": str(path), "errors": errors},
    }
