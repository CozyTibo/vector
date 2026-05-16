"""Phase 06 P06-30 — golden-thread corpus binding (TCRE ``AMB‑*`` / ``CD‑*`` / optional chains).

Normative:
``DOCS/cortex/verification/golden-thread-replay-corpus-spec.md`` §§2–3,
``DOCS/cortex/reasoning/reasoning-verification-harness-spec.md`` §2 (on-disk vectors),
``DOCS/cortex/reasoning/ambiguity-registry-v1.md``,
``DOCS/cortex/reasoning/causal-degradation-spec.md``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import (
    EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
)
from vector.domains.cortex.reasoning.causal_ambiguity_propagation import (
    normalize_ambiguity_corpus_token_to_registry_id_v1,
    validate_ambiguity_class_id_causal_registry_v1,
)
from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    normalize_expected_degradation_classes_corpus_v1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

PHASE06_REASONING_GOLDEN_THREAD_BINDING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REASONING_GOLDEN_THREAD_CORPUS_SCHEMA_VERSION_V1: Final[int] = 1

GOLDEN_THREAD_REPLAY_CORPUS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/verification/golden-thread-replay-corpus-spec.md"
)

REASONING_VERIFICATION_HARNESS_GOLDEN_VECTORS_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-verification-harness-spec.md §2"
)

_REPLAY_LEGALITY_STATES_V1: Final[frozenset[str]] = frozenset(
    {
        "replay_conflicted",
        "replay_degraded",
        "replay_equivalent",
        "replay_partial",
        "replay_unverifiable",
    }
)

_GOLDEN_V1_PATH_TAIL: Final[tuple[str, ...]] = (
    "tests",
    "vector",
    "domains",
    "cortex",
    "reasoning",
    "reasoning_golden_vectors",
    "v1",
)


class ReasoningGoldenThreadCorpusBindingError(ValueError):
    """Fail-closed golden-thread manifest / case binding for TCRE harness vectors."""


_GTC_FILE_LOAD_ERRORS: Final[tuple[type[BaseException], ...]] = (
    OSError,
    json.JSONDecodeError,
    ReasoningGoldenThreadCorpusBindingError,
    RuntimeError,
)


def _repo_root_from_reasoning_package() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "reasoning").is_dir():
            return root
    msg = "could not locate DOCS/cortex/reasoning from reasoning package"
    raise RuntimeError(msg)


def reasoning_golden_vectors_v1_root() -> Path:
    """Canonical on-disk home for **TCRE** golden vectors (host + ``/app`` compose cwd)."""
    repo = _repo_root_from_reasoning_package()
    flat = repo.joinpath(*_GOLDEN_V1_PATH_TAIL)
    nested = repo.joinpath("backend", *_GOLDEN_V1_PATH_TAIL)
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"could not locate reasoning_golden_vectors/v1 under {repo}"
    raise RuntimeError(msg)


def load_reasoning_corpus_manifest_v1(path: Path) -> dict[str, Any]:
    """Load ``corpus_manifest.json`` (UTF-8 JSON object)."""
    raw = path.read_text(encoding="utf-8")
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise ReasoningGoldenThreadCorpusBindingError("corpus manifest root must be a JSON object")
    return doc


def load_reasoning_corpus_case_v1(path: Path) -> dict[str, Any]:
    """Load a per-case ``case.json`` (UTF-8 JSON object)."""
    raw = path.read_text(encoding="utf-8")
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise ReasoningGoldenThreadCorpusBindingError("case.json root must be a JSON object")
    return doc


def validate_reasoning_corpus_manifest_v1(manifest: Mapping[str, Any]) -> None:
    """``golden-thread-replay-corpus-spec.md`` §3.1 — required manifest fields."""
    cid = manifest.get("corpus_id")
    if not isinstance(cid, str) or not cid.strip():
        raise ReasoningGoldenThreadCorpusBindingError("corpus_id must be a non-empty string")
    csv = manifest.get("corpus_schema_version")
    if not isinstance(csv, int) or int(csv) < 1:
        raise ReasoningGoldenThreadCorpusBindingError("corpus_schema_version must be int >= 1")
    if int(csv) != REASONING_GOLDEN_THREAD_CORPUS_SCHEMA_VERSION_V1:
        exp = REASONING_GOLDEN_THREAD_CORPUS_SCHEMA_VERSION_V1
        raise ReasoningGoldenThreadCorpusBindingError(
            f"corpus_schema_version must be {exp}; got {csv!r}"
        )
    rv = manifest.get("reconstruction_version")
    if not isinstance(rv, str) or not rv.strip():
        raise ReasoningGoldenThreadCorpusBindingError(
            "reconstruction_version must be a non-empty string"
        )
    ecv = manifest.get("execution_reconstruction_contract_version")
    if not isinstance(ecv, int) or int(ecv) != int(EXECUTION_RECONSTRUCTION_CONTRACT_VERSION):
        raise ReasoningGoldenThreadCorpusBindingError(
            "execution_reconstruction_contract_version must match "
            f"{EXECUTION_RECONSTRUCTION_CONTRACT_VERSION}; got {ecv!r}"
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ReasoningGoldenThreadCorpusBindingError("cases must be a non-empty list")
    for i, row in enumerate(cases):
        if not isinstance(row, Mapping):
            raise ReasoningGoldenThreadCorpusBindingError(f"cases[{i}] must be an object")
        cc = row.get("corpus_case_id")
        if not isinstance(cc, str) or not cc.strip():
            raise ReasoningGoldenThreadCorpusBindingError(
                f"cases[{i}].corpus_case_id must be non-empty str"
            )


def validate_reasoning_corpus_case_header_v1(case: Mapping[str, Any]) -> None:
    """§3.2 — ``expected_ambiguity_classes``, ``expected_degradation_classes``, optional chains."""
    cc = case.get("corpus_case_id")
    if not isinstance(cc, str) or not cc.strip():
        raise ReasoningGoldenThreadCorpusBindingError("corpus_case_id must be a non-empty string")
    leg = case.get("expected_replay_legality_state")
    if leg is not None and (not isinstance(leg, str) or leg not in _REPLAY_LEGALITY_STATES_V1):
        allowed = ", ".join(sorted(_REPLAY_LEGALITY_STATES_V1))
        raise ReasoningGoldenThreadCorpusBindingError(
            f"expected_replay_legality_state must be one of: {allowed}; got {leg!r}"
        )
    refs = case.get("raw_evidence_bundle_refs")
    if refs is not None:
        if not isinstance(refs, list):
            raise ReasoningGoldenThreadCorpusBindingError("raw_evidence_bundle_refs must be a list")
        for i, r in enumerate(refs):
            pfx = f"raw_evidence_bundle_refs[{i}]"
            if not isinstance(r, Mapping):
                raise ReasoningGoldenThreadCorpusBindingError(f"{pfx} must be object")
            k = r.get("kind")
            ref = r.get("ref")
            if not isinstance(k, str) or not k.strip():
                raise ReasoningGoldenThreadCorpusBindingError(f"{pfx}.kind invalid")
            if not isinstance(ref, str) or not ref.strip():
                raise ReasoningGoldenThreadCorpusBindingError(f"{pfx}.ref invalid")
    amb = case.get("expected_ambiguity_classes")
    if amb is not None:
        if not isinstance(amb, list):
            raise ReasoningGoldenThreadCorpusBindingError(
                "expected_ambiguity_classes must be a list"
            )
        for i, tok in enumerate(amb):
            if not isinstance(tok, str):
                raise ReasoningGoldenThreadCorpusBindingError(
                    f"expected_ambiguity_classes[{i}] must be str"
                )
            canon = normalize_ambiguity_corpus_token_to_registry_id_v1(tok)
            validate_ambiguity_class_id_causal_registry_v1(canon)
    deg = case.get("expected_degradation_classes")
    if deg is not None:
        normalize_expected_degradation_classes_corpus_v1(deg)
    chains = case.get("expected_tcre_causal_chains")
    if chains is not None:
        if not isinstance(chains, list):
            raise ReasoningGoldenThreadCorpusBindingError(
                "expected_tcre_causal_chains must be a list"
            )
        for i, row in enumerate(chains):
            pfx = f"expected_tcre_causal_chains[{i}]"
            if not isinstance(row, Mapping):
                raise ReasoningGoldenThreadCorpusBindingError(f"{pfx} must be object")
            eid = row.get("tcre_causal_edge_id")
            if not isinstance(eid, str) or not eid.strip():
                raise ReasoningGoldenThreadCorpusBindingError(
                    f"{pfx}.tcre_causal_edge_id must be non-empty str"
                )


def hash_reasoning_corpus_manifest_digest_v1(manifest: Mapping[str, Any]) -> str:
    """Deterministic **sha256** over canonical manifest subset (sorted JSON keys)."""
    ecv = manifest.get("execution_reconstruction_contract_version")
    body = {
        "cases": manifest.get("cases"),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_schema_version": manifest.get("corpus_schema_version"),
        "execution_reconstruction_contract_version": ecv,
        "reconstruction_version": manifest.get("reconstruction_version"),
    }
    return hash_reasoning_canonical_json_sha256_v1(body)


def bind_reasoning_golden_corpus_at_root_v1(
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate shipped **v1** manifest + every listed ``cases/<id>/case.json``."""
    base = reasoning_golden_vectors_v1_root() if root is None else root
    manifest_path = base / "corpus_manifest.json"
    manifest = load_reasoning_corpus_manifest_v1(manifest_path)
    validate_reasoning_corpus_manifest_v1(manifest)
    cases_obj = manifest.get("cases")
    if not isinstance(cases_obj, list):
        raise ReasoningGoldenThreadCorpusBindingError("internal: manifest cases must be a list")
    cases = cases_obj
    bound: list[str] = []
    for row in cases:
        if not isinstance(row, Mapping):
            raise ReasoningGoldenThreadCorpusBindingError(
                "internal: manifest case row must be mapping"
            )
        cid = str(row.get("corpus_case_id", "")).strip()
        cpath = base / "cases" / cid / "case.json"
        if not cpath.is_file():
            rel = cpath.relative_to(base)
            raise ReasoningGoldenThreadCorpusBindingError(f"missing case file: {rel}")
        case = load_reasoning_corpus_case_v1(cpath)
        validate_reasoning_corpus_case_header_v1(case)
        if case.get("corpus_case_id") != cid:
            raise ReasoningGoldenThreadCorpusBindingError(
                "case.json corpus_case_id must match manifest row"
            )
        bound.append(cid)
    return {
        "corpus_id": manifest.get("corpus_id"),
        "manifest_digest_sha256": hash_reasoning_corpus_manifest_digest_v1(manifest),
        "cases_bound": tuple(bound),
        "reasoning_golden_vectors_root": str(base),
        "phase06_reasoning_golden_thread_binding_runtime_schema_version": (
            PHASE06_REASONING_GOLDEN_THREAD_BINDING_RUNTIME_SCHEMA_VERSION
        ),
    }


def _gtc_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_reasoning_golden_thread_binding_runtime_schema_version": (
            PHASE06_REASONING_GOLDEN_THREAD_BINDING_RUNTIME_SCHEMA_VERSION
        ),
    }


def verify_gp06_gtc01_default_manifest_shape_static() -> dict[str, Any]:
    """P06-30 — shipped ``corpus_manifest.json`` satisfies §3.1."""
    errors: list[str] = []
    try:
        root = reasoning_golden_vectors_v1_root()
        manifest = load_reasoning_corpus_manifest_v1(root / "corpus_manifest.json")
        validate_reasoning_corpus_manifest_v1(manifest)
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-30-gtc-manifest",
        "name": "gp06_gtc01_default_manifest_shape",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gtc_detail(errors),
    }


def verify_gp06_gtc02_case_ambiguity_binding_static() -> dict[str, Any]:
    """P06-30 — ``expected_ambiguity_classes`` normalizes to registered ``AMB‑*``."""
    errors: list[str] = []
    try:
        root = reasoning_golden_vectors_v1_root()
        case = load_reasoning_corpus_case_v1(
            root / "cases" / "tcre_ambiguity_cd_minimal_v1" / "case.json",
        )
        validate_reasoning_corpus_case_header_v1(case)
        amb = case.get("expected_ambiguity_classes")
        if not isinstance(amb, list) or len(amb) < 1:
            errors.append("expected_ambiguity_classes_too_short")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-30-gtc-ambiguity",
        "name": "gp06_gtc02_case_ambiguity_binding",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gtc_detail(errors),
    }


def verify_gp06_gtc03_case_degradation_cd_binding_static() -> dict[str, Any]:
    """P06-30 — ``expected_degradation_classes`` maps to canonical ``CD‑*``."""
    errors: list[str] = []
    try:
        root = reasoning_golden_vectors_v1_root()
        case = load_reasoning_corpus_case_v1(
            root / "cases" / "tcre_ambiguity_cd_minimal_v1" / "case.json",
        )
        deg = case.get("expected_degradation_classes")
        got = normalize_expected_degradation_classes_corpus_v1(deg)
        if len(got) < 2:
            errors.append("expected_at_least_two_distinct_cd_codes")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-30-gtc-degradation",
        "name": "gp06_gtc03_case_degradation_cd_binding",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gtc_detail(errors),
    }


def verify_gp06_gtc04_optional_tcre_chains_shape_static() -> dict[str, Any]:
    """P06-30 — optional ``expected_tcre_causal_chains`` rows carry ``tcre_causal_edge_id``."""
    errors: list[str] = []
    try:
        root = reasoning_golden_vectors_v1_root()
        case = load_reasoning_corpus_case_v1(
            root / "cases" / "tcre_ambiguity_cd_minimal_v1" / "case.json",
        )
        validate_reasoning_corpus_case_header_v1(case)
        ch = case.get("expected_tcre_causal_chains")
        if not isinstance(ch, list) or not ch:
            errors.append("expected_tcre_causal_chains_missing")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-30-gtc-tcre-chains",
        "name": "gp06_gtc04_optional_tcre_chains_shape",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gtc_detail(errors),
    }


def verify_gp06_gtc05_full_bind_roundtrip_static() -> dict[str, Any]:
    """P06-30 — manifest + all cases validate end-to-end at default root."""
    errors: list[str] = []
    try:
        bind_reasoning_golden_corpus_at_root_v1()
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-30-gtc-bind",
        "name": "gp06_gtc05_full_bind_roundtrip",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gtc_detail(errors),
    }
