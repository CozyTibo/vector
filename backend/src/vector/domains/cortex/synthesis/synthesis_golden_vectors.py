"""Phase 08 P08-27 — synthesis golden vectors + policy fixture binding.

Normative: ``DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md`` §2,
``DOCS/cortex/synthesis/fixtures/SynthesisPolicyPackV1_Default.json``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.normative import (
    PHASE08_POLICY_PACK_FIXTURE_REF_V1,
    PHASE08_PROGRAM_FREEZE_VERSION,
)
from vector.domains.cortex.synthesis.synthesis_degradation import (
    map_rd_to_sd_via_matrix_v1,
    propagate_rd_omissions_via_matrix_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    enforce_synthesis_job_workload_and_intent_v1,
)
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    aggregate_synthesis_legality_class_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1

PHASE08_SYNTHESIS_GOLDEN_VECTORS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_GOLDEN_CORPUS_SCHEMA_VERSION_V1: Final[int] = 1

SYNTHESIS_GOLDEN_CORPUS_ID_V1: Final[str] = "synthesis_golden_v1"

SYNTHESIS_GOLDEN_VECTORS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-evaluation-quality-governance.md"
)

SYNTHESIS_GOLDEN_VECTORS_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/synthesis/golden-vectors",
)

_SYNTHESIS_GOLDEN_V1_PATH_TAIL: Final[tuple[str, ...]] = (
    "tests",
    "vector",
    "domains",
    "cortex",
    "synthesis",
    "synthesis_golden_vectors",
    "v1",
)

_GTC_FILE_LOAD_ERRORS: Final[tuple[type[BaseException], ...]] = (
    OSError,
    json.JSONDecodeError,
    RuntimeError,
    ValueError,
    FileNotFoundError,
)


class SynthesisGoldenVectorsError(ValueError):
    """Fail-closed golden corpus manifest / case binding."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def _repo_root_v1() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "synthesis").is_dir():
            return root
    msg = "could not locate DOCS/cortex/synthesis from synthesis package"
    raise RuntimeError(msg)


def synthesis_golden_vectors_v1_root() -> Path:
    """Canonical on-disk home for synthesis golden vectors (host + compose ``/app``)."""
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        candidate = root.joinpath(*_SYNTHESIS_GOLDEN_V1_PATH_TAIL)
        if candidate.is_dir():
            return candidate
        alt = root / "backend" / Path(*_SYNTHESIS_GOLDEN_V1_PATH_TAIL)
        if alt.is_dir():
            return alt
    raise FileNotFoundError("synthesis_golden_vectors/v1 not found")


def synthesis_policy_pack_fixture_path_v1() -> Path:
    return _repo_root_v1() / "DOCS" / "cortex" / "synthesis" / "fixtures" / (
        f"{DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1}.json"
    )


def load_synthesis_policy_pack_fixture_v1() -> dict[str, Any]:
    path = synthesis_policy_pack_fixture_path_v1()
    if not path.is_file():
        raise SynthesisGoldenVectorsError(
            "synthesis_policy_pack_fixture_missing",
            detail={"path": str(path)},
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SynthesisGoldenVectorsError("synthesis_policy_pack_fixture_not_object")
    return raw


def hash_synthesis_policy_pack_fixture_file_v1() -> str:
    """Deterministic **sha256** over canonical JSON of the default policy pack fixture."""
    return hash_reasoning_canonical_json_sha256_v1(load_synthesis_policy_pack_fixture_v1())


def load_synthesis_corpus_manifest_v1(path: Path | None = None) -> dict[str, Any]:
    root = synthesis_golden_vectors_v1_root()
    manifest_path = path or (root / "corpus_manifest.json")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SynthesisGoldenVectorsError("corpus_manifest_not_object")
    return doc


def load_synthesis_golden_case_v1(case_id: str) -> dict[str, Any]:
    root = synthesis_golden_vectors_v1_root()
    path = root / "cases" / case_id / "case.json"
    if not path.is_file():
        raise FileNotFoundError(f"golden case not found: {case_id}")
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SynthesisGoldenVectorsError("golden_case_not_object")
    return loaded


def validate_synthesis_corpus_manifest_v1(manifest: Mapping[str, Any]) -> None:
    errors: list[str] = []
    cid = manifest.get("corpus_id")
    if not isinstance(cid, str) or not cid.strip():
        errors.append("corpus_id_invalid")
    csv = manifest.get("corpus_schema_version")
    if not isinstance(csv, int) or int(csv) != SYNTHESIS_GOLDEN_CORPUS_SCHEMA_VERSION_V1:
        errors.append("corpus_schema_version_mismatch")
    pfv = manifest.get("phase08_program_freeze_version")
    if int(pfv or -1) != PHASE08_PROGRAM_FREEZE_VERSION:
        errors.append("phase08_program_freeze_version_mismatch")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases_missing")
    for i, row in enumerate(cases or []):
        if not isinstance(row, Mapping):
            errors.append(f"cases_{i}_not_object")
            continue
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"cases_{i}_case_id_invalid")
    if errors:
        raise SynthesisGoldenVectorsError(
            "corpus_manifest_invalid",
            detail={"errors": errors},
        )


def validate_synthesis_golden_case_header_v1(case: Mapping[str, Any]) -> None:
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise SynthesisGoldenVectorsError("case_id_invalid")
    gate_id = case.get("gate_id")
    if not isinstance(gate_id, str) or not gate_id.strip():
        raise SynthesisGoldenVectorsError("gate_id_invalid")
    if not isinstance(case.get("inputs"), Mapping):
        raise SynthesisGoldenVectorsError("inputs_missing")
    if not isinstance(case.get("expected"), Mapping):
        raise SynthesisGoldenVectorsError("expected_missing")


def hash_synthesis_corpus_manifest_digest_v1(manifest: Mapping[str, Any]) -> str:
    body = {
        "cases": manifest.get("cases"),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_schema_version": manifest.get("corpus_schema_version"),
        "phase08_program_freeze_version": manifest.get("phase08_program_freeze_version"),
        "policy_pack_fixture_ref": manifest.get("policy_pack_fixture_ref"),
    }
    return hash_reasoning_canonical_json_sha256_v1(body)


def synthesis_golden_corpus_case_count_v1() -> int:
    root = synthesis_golden_vectors_v1_root()
    cases_dir = root / "cases"
    if not cases_dir.is_dir():
        return 0
    return sum(1 for _ in cases_dir.rglob("case.json"))


def run_synthesis_golden_degraded_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    inputs = case["inputs"]
    expected = case["expected"]
    rd_codes = [str(c) for c in inputs.get("upstream_rd_codes") or []]
    rd_rows = [{"rd_code": c, "reason": "golden"} for c in rd_codes]
    sd_rows = propagate_rd_omissions_via_matrix_v1(rd_rows)
    for rd in rd_codes:
        sd = map_rd_to_sd_via_matrix_v1(rd)
        want_sd = expected.get("sd_codes_contains")
        if isinstance(want_sd, list) and sd not in want_sd:
            raise SynthesisGoldenVectorsError(
                "sd_propagation_mismatch",
                detail={"rd_code": rd, "sd_code": sd, "want": want_sd},
            )
    legality = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality=str(
            inputs.get("upstream_retrieval_legality") or "retrieval_degraded",
        ),
        synthesis_intent=str(inputs.get("synthesis_intent") or "inspect"),
        execution_partition=str(inputs.get("execution_partition") or "authoritative"),
        synthesis_omission_rows=sd_rows,
    )
    exp_leg = expected.get("synthesis_legality_class")
    if exp_leg and legality != exp_leg:
        raise SynthesisGoldenVectorsError(
            "legality_mismatch",
            detail={"expected": exp_leg, "actual": legality},
        )
    return {
        "case_id": case.get("case_id"),
        "gate_id": case.get("gate_id"),
        "sd_rows": sd_rows,
        "synthesis_legality_class": legality,
    }


def run_synthesis_golden_legality_empty_scope_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    inputs = case["inputs"]
    expected = case["expected"]
    sd_rows = [
        {
            "sd_code": str(expected.get("sd_code") or "SD-SCOPE-EMPTY"),
            "reason": "no eligible scopes",
        },
    ]
    legality = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality=str(
            inputs.get("upstream_retrieval_legality") or "retrieval_replay_safe",
        ),
        synthesis_intent=str(inputs.get("synthesis_intent") or "inspect"),
        execution_partition=str(inputs.get("execution_partition") or "authoritative"),
        synthesis_omission_rows=sd_rows,
    )
    exp_leg = expected.get("synthesis_legality_class")
    if exp_leg and legality != exp_leg:
        raise SynthesisGoldenVectorsError(
            "legality_mismatch",
            detail={"expected": exp_leg, "actual": legality},
        )
    return {
        "case_id": case.get("case_id"),
        "gate_id": case.get("gate_id"),
        "synthesis_legality_class": legality,
    }


def run_synthesis_golden_pipeline_minimal_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    inputs = case["inputs"]
    expected = case["expected"]
    envelope = dict(inputs.get("envelope") or {})
    wl, intent = enforce_synthesis_job_workload_and_intent_v1(envelope)
    pack = load_synthesis_policy_pack_v1()
    if pack.get("synthesis_policy_pack_id") != DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1:
        raise SynthesisGoldenVectorsError("policy_pack_id_mismatch")
    exp_wl = expected.get("synthesis_workload_class")
    if exp_wl and wl != exp_wl:
        raise SynthesisGoldenVectorsError("workload_mismatch")
    return {
        "case_id": case.get("case_id"),
        "gate_id": case.get("gate_id"),
        "synthesis_workload_class": wl,
        "synthesis_intent": intent,
    }


def run_synthesis_golden_case_v1(case: Mapping[str, Any]) -> dict[str, Any]:
    """Dispatch golden case runner by ``gate_id``."""
    validate_synthesis_golden_case_header_v1(case)
    gate_id = str(case.get("gate_id"))
    if gate_id == "G-P08-REPLAY-01":
        from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
            run_synthesis_golden_replay_equivalence_case_v1,
        )

        return run_synthesis_golden_replay_equivalence_case_v1(case)
    if gate_id == "G-P08-DEG-02":
        return run_synthesis_golden_degraded_case_v1(case)
    if gate_id == "G-P08-LEG-01":
        return run_synthesis_golden_legality_empty_scope_case_v1(case)
    if gate_id in ("G-P08-SCHEMA-01", "G-P08-FSM-01"):
        return run_synthesis_golden_pipeline_minimal_case_v1(case)
    raise SynthesisGoldenVectorsError(
        "unsupported_golden_gate",
        detail={"gate_id": gate_id},
    )


def bind_synthesis_golden_corpus_at_root_v1(
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate shipped manifest + every listed ``cases/<id>/case.json``."""
    base = synthesis_golden_vectors_v1_root() if root is None else root
    manifest = load_synthesis_corpus_manifest_v1(base / "corpus_manifest.json")
    validate_synthesis_corpus_manifest_v1(manifest)
    bound: list[str] = []
    for row in manifest.get("cases") or []:
        if not isinstance(row, Mapping):
            continue
        case_id = str(row["case_id"]).strip()
        case_path = base / "cases" / case_id / "case.json"
        if not case_path.is_file():
            raise SynthesisGoldenVectorsError(f"missing_case_file:{case_id}")
        case = load_synthesis_golden_case_v1(case_id)
        if str(case.get("case_id")) != case_id:
            raise SynthesisGoldenVectorsError("case_id_manifest_mismatch")
        run_synthesis_golden_case_v1(case)
        bound.append(case_id)
    fixture_digest = hash_synthesis_policy_pack_fixture_file_v1()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "manifest_digest_sha256": hash_synthesis_corpus_manifest_digest_v1(manifest),
        "policy_pack_fixture_digest_sha256": fixture_digest,
        "policy_pack_fixture_ref": PHASE08_POLICY_PACK_FIXTURE_REF_V1,
        "cases_bound": tuple(bound),
        "synthesis_golden_vectors_root": str(base),
        "phase08_synthesis_golden_vectors_runtime_schema_version": (
            PHASE08_SYNTHESIS_GOLDEN_VECTORS_RUNTIME_SCHEMA_VERSION
        ),
    }


def build_synthesis_golden_vectors_catalog_v1() -> dict[str, Any]:
    """Admin catalog pointer — corpus manifest + fixture digest (read-only)."""
    root = synthesis_golden_vectors_v1_root()
    manifest = load_synthesis_corpus_manifest_v1(root / "corpus_manifest.json")
    validate_synthesis_corpus_manifest_v1(manifest)
    fixture_path = synthesis_policy_pack_fixture_path_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "spec_ref": SYNTHESIS_GOLDEN_VECTORS_SPEC_REF_V1,
        "synthesis_golden_vectors_runtime_schema_version": (
            PHASE08_SYNTHESIS_GOLDEN_VECTORS_RUNTIME_SCHEMA_VERSION
        ),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_schema_version": manifest.get("corpus_schema_version"),
        "phase08_program_freeze_version": manifest.get("phase08_program_freeze_version"),
        "policy_pack_fixture_ref": PHASE08_POLICY_PACK_FIXTURE_REF_V1,
        "policy_pack_fixture_path": str(fixture_path),
        "policy_pack_fixture_digest_sha256": hash_synthesis_policy_pack_fixture_file_v1(),
        "policy_pack_fixture_present": fixture_path.is_file(),
        "manifest_digest_sha256": hash_synthesis_corpus_manifest_digest_v1(manifest),
        "golden_corpus_case_count": synthesis_golden_corpus_case_count_v1(),
        "cases": list(manifest.get("cases") or []),
        "synthesis_golden_vectors_root": str(root),
    }


def _gtc_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "P08-27-gtc",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_golden_vectors_runtime_schema_version": (
                PHASE08_SYNTHESIS_GOLDEN_VECTORS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_gtc01_corpus_manifest_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        manifest = load_synthesis_corpus_manifest_v1()
        validate_synthesis_corpus_manifest_v1(manifest)
        if manifest.get("corpus_id") != SYNTHESIS_GOLDEN_CORPUS_ID_V1:
            errors.append("corpus_id_drift")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    return _gtc_meta("gp08_gtc01_corpus_manifest_shape", errors)


def verify_gp08_gtc02_replay_double_run_case_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        case = load_synthesis_golden_case_v1("replay_equivalence/double_run_v1")
        a = run_synthesis_golden_case_v1(case)
        b = run_synthesis_golden_case_v1(case)
        if a.get("gp08_replay_proof_passed") != b.get("gp08_replay_proof_passed"):
            errors.append("replay_case_non_deterministic")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    return _gtc_meta("gp08_gtc02_replay_double_run_case", errors)


def verify_gp08_gtc03_degraded_rd_upstream_case_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        run_synthesis_golden_case_v1(
            load_synthesis_golden_case_v1("degradation/degraded_brief_rd_upstream_v1"),
        )
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    return _gtc_meta("gp08_gtc03_degraded_rd_upstream_case", errors)


def verify_gp08_gtc04_empty_scope_legality_case_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        run_synthesis_golden_case_v1(load_synthesis_golden_case_v1("legality/empty_scope_v1"))
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    return _gtc_meta("gp08_gtc04_empty_scope_legality_case", errors)


def verify_gp08_gtc05_policy_pack_fixture_digest_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        path = synthesis_policy_pack_fixture_path_v1()
        if not path.is_file():
            errors.append("fixture_missing")
        digest = hash_synthesis_policy_pack_fixture_file_v1()
        if len(digest) != 64:
            errors.append("digest_not_sha256_hex")
        pack = load_synthesis_policy_pack_fixture_v1()
        if pack.get("synthesis_policy_pack_id") != DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1:
            errors.append("fixture_pack_id_mismatch")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    return _gtc_meta("gp08_gtc05_policy_pack_fixture_digest", errors)


def verify_gp08_gtc06_full_bind_roundtrip_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        out = bind_synthesis_golden_corpus_at_root_v1()
        if len(out.get("cases_bound") or ()) < 4:
            errors.append("cases_bound_count_low")
    except _GTC_FILE_LOAD_ERRORS as exc:
        errors.append(str(exc))
    return _gtc_meta("gp08_gtc06_full_bind_roundtrip", errors)


def verify_gp08_gtc07_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/catalog/cortex/synthesis/golden-vectors",)
    if SYNTHESIS_GOLDEN_VECTORS_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    return _gtc_meta("gp08_gtc07_admin_openapi_path_matrix", errors)


def verify_gp08_gtc01_synthesis_golden_vectors_static_bundle() -> dict[str, Any]:
    """**G-P08-GTC-01** — PR-blocking golden corpus + fixture digest bundle."""
    errors: list[str] = []
    for fn in (
        verify_gp08_gtc01_corpus_manifest_shape_static,
        verify_gp08_gtc02_replay_double_run_case_static,
        verify_gp08_gtc03_degraded_rd_upstream_case_static,
        verify_gp08_gtc04_empty_scope_legality_case_static,
        verify_gp08_gtc05_policy_pack_fixture_digest_static,
        verify_gp08_gtc06_full_bind_roundtrip_static,
        verify_gp08_gtc07_admin_openapi_path_matrix_static,
    ):
        out = fn()
        if not out.get("passed"):
            errors.append(str(out.get("name")))
    return _gtc_meta("gp08_gtc01_synthesis_golden_vectors_static_bundle", errors)
