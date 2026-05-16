"""Phase 06 P06-02 — anti-goals / forbidden cognition (TCRE reasoning package).

Normative: ``DOCS/cortex/reasoning/phase-06-anti-goals-doctrine.md``.
``G-P06-ANTI-01`` (``reasoning-verification-harness-spec.md``): reasoning package file tree —
no banned third-party cognition / LLM / embedding imports.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.traversal.anti_goals import (
    list_forbidden_cognition_key_violations as list_octs_forbidden_cognition_key_violations,
)

PHASE06_ANTI_GOALS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# Root module names / tokens that must not appear on ``import`` / ``from`` lines in this package.
# Mirrors ``phase-06-anti-goals-doctrine.md`` (embeddings, LLM narratives, agents, fuzzy inference, …).
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

# Exact JSON keys (lowercase) forbidden on reasoning / TCRE canonical bodies in addition to OCTS scan.
_TCRE_EXTRA_FORBIDDEN_KEYS_LOWER: Final[frozenset[str]] = frozenset(
    {
        "autonomous_agent",
        "chain_of_thought",
        "cot_evidence",
        "cot_trace",
        "emotional_score",
        "fuzzy_entity_resolution",
        "fuzzy_graph_expansion",
        "graph_clustering",
        "latent_inference",
        "latent_variable",
        "linkage_cluster",
        "motivation_score",
        "performance_scoring",
        "probabilistic_edge_weight",
        "probabilistic_inference",
        "self_directed_planner",
        "semantic_cluster",
        "silent_merge",
        "topic_model",
        "topic_modeling",
        "vector_database_id",
    }
)

_TCRE_EXTRA_KEY_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "chain_of_thought",
    "semantic_similarity",
    "vector_db",
    "autonomous_agent",
    "latent_variable",
    "topic_model",
)


class ReasoningCognitionLeakageError(ValueError):
    """Raised when a canonical reasoning / TCRE JSON body smuggles forbidden cognition-shaped keys."""


def _tcre_extra_key_violations(key: str) -> list[str]:
    lk = key.lower()
    out: list[str] = []
    if lk in _TCRE_EXTRA_FORBIDDEN_KEYS_LOWER:
        out.append("forbidden_tcre_exact_cognition_key")
    for sub in _TCRE_EXTRA_KEY_SUBSTRINGS_LOWER:
        if sub in lk:
            out.append(f"forbidden_tcre_key_substring:{sub}")
            break
    return out


def list_reasoning_forbidden_cognition_key_violations(obj: Any, *, path: str = "") -> list[str]:
    """Return paths for **OCTS** + **TCRE** forbidden cognition keys (recursive mapping walk)."""
    base = list_octs_forbidden_cognition_key_violations(obj, path=path)
    extra = _list_tcre_extra_only_recursive(obj, path=path)
    return base + extra


def _list_tcre_extra_only_recursive(obj: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(obj, Mapping):
        for raw_k, v in obj.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{path}.{raw_k}" if path else raw_k
            for reason in _tcre_extra_key_violations(raw_k):
                violations.append(f"{prefix}:{reason}")
            violations.extend(_list_tcre_extra_only_recursive(v, path=prefix))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(_list_tcre_extra_only_recursive(item, path=f"{path}[{i}]"))
    return violations


def validate_reasoning_canonical_json_mapping_no_cognition_leakage(body: Mapping[str, Any]) -> None:
    """Reject canonical reasoning JSON that includes forbidden cognition keys (P06-02)."""
    hits = list_reasoning_forbidden_cognition_key_violations(body)
    if hits:
        msg = "reasoning cognition leakage in canonical JSON: " + "; ".join(hits[:16])
        if len(hits) > 16:
            msg += f"; …(+{len(hits) - 16} more)"
        raise ReasoningCognitionLeakageError(msg)


def _reasoning_package_dir() -> Path:
    return Path(__file__).resolve().parent


def iter_reasoning_package_py_files() -> Iterable[Path]:
    root = _reasoning_package_dir()
    for path in sorted(root.rglob("*.py")):
        parts = path.parts
        if "__pycache__" in parts:
            continue
        yield path


def list_reasoning_package_banned_import_violations() -> list[str]:
    """Scan ``vector.domains.cortex.reasoning`` for ``import`` / ``from`` lines touching banned roots."""
    violations: list[str] = []
    for path in iter_reasoning_package_py_files():
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path.relative_to(_reasoning_package_dir())}:syntax_error:{exc}")
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


def verify_gp06_anti01_reasoning_package_static() -> dict[str, Any]:
    """``G-P06-ANTI-01`` — banned cognition / ML / LLM imports under the reasoning package."""
    import_errors = list_reasoning_package_banned_import_violations()
    passed = len(import_errors) == 0
    return {
        "id": "G-P06-ANTI-01",
        "name": "reasoning_package_banned_imports",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_anti_goals_runtime_schema_version": PHASE06_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "import_violations": import_errors,
        },
    }


def verify_gp06_json_cognition_keys_static() -> dict[str, Any]:
    """Static JSON cognition checks for TCRE-shaped bodies (P06-02 doctrine)."""
    errors: list[str] = []

    illegal = {"tcre_edges": [], "chain_of_thought": "no"}
    if not list_reasoning_forbidden_cognition_key_violations(illegal):
        errors.append("expected_violation_for_chain_of_thought")

    illegal2 = {"embedding": [0.1, 0.2]}
    if not list_reasoning_forbidden_cognition_key_violations(illegal2):
        errors.append("expected_violation_for_embedding_key")

    legal = {
        "tcre_policy_pack_id": "ReasoningPolicyPackV1_Default",
        "causal_chain_id": "sha256:00",
        "chronology_legality_class": "chronology_strict",
        "hop_receipts": [],
    }
    if list_reasoning_forbidden_cognition_key_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_reasoning_forbidden_cognition_key_violations(legal)}"
        )

    try:
        validate_reasoning_canonical_json_mapping_no_cognition_leakage(legal)
    except ReasoningCognitionLeakageError as exc:
        errors.append(f"unexpected_raise_on_legal_stub:{exc}")

    passed = len(errors) == 0
    return {
        "id": "P06-02-json-cognition",
        "name": "reasoning_json_forbidden_cognition_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_anti_goals_runtime_schema_version": PHASE06_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }
