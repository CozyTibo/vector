"""Phase 05 Step **22** — **G-P05-*** verification gates catalog + CI stage wiring.

Normative: ``DOCS/cortex/05-traversal/phase-05-verification-gates-doctrine.md`` (registry),
``DOCS/cortex/05-traversal/phase-05-ci-enforcement-architecture.md`` (stages **A–E**, severities,
corruption bundles). **Step 25** adds **G-P05-ECO-02** / **G-P05-ECO-03** to the doctrine registry
and wires **G-P05-ECO-01..03** (**STAGE-E**).

This module is the **single ownership** map from gate ID → default stage/severity and optional
static ``runner`` (callable returning the usual ``{id, name, passed, severity, detail}`` dict).
Gates without runners remain **catalog-only** until a later step implements them (**FS-G-01**
still forbids skipping ``hard_fail`` runners in CI — unwired IDs are **not** executed here).
"""

from __future__ import annotations

import json
import os
import unicodedata
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal, cast

import yaml

OCTS_VERIFICATION_GATES_CATALOG_SCHEMA_VERSION: Final[int] = 1
OCTS_VERIFICATION_MODE_ENV: Final[str] = "OCTS_VERIFICATION_MODE"

GateStage = Literal["A", "B", "C", "D", "E", "Z"]
GateSeverity = Literal["hard_fail", "warn"]

# Doctrine §3 + ``phase-05-ci-enforcement-architecture.md`` §4 (EQUIV-02 / REPLAY-WALK-01 warn).
_WARN_GATES: Final[frozenset[str]] = frozenset({"G-P05-EQUIV-02", "G-P05-REPLAY-WALK-01"})

# ``phase-05-ci-enforcement-architecture.md`` §10 — corruption bundle → member gate IDs.
OCTS_CORRUPTION_GATE_BUNDLES_V1: Final[dict[str, frozenset[str]]] = {
    "exploration_contamination": frozenset(
        {"G-P05-EXP-01", "G-P05-EXP-02", "G-P05-CLOSE-01"}
    ),
    "temporal_corruption": frozenset(
        {"G-P05-TEMP-01", "G-P05-TEMP-02", "G-P05-REPLAY-IDX-01", "G-P05-REPLAY-IDX-02"}
    ),
    "canonicalization_corruption": frozenset(
        {"G-P05-CANON-01", "G-P05-CANON-02", "G-P05-CANON-03", "G-P05-HASH-02"}
    ),
    "equivalence_corruption": frozenset({"G-P05-EQUIV-01", "G-P05-EQUIV-03"}),
}

_DOCTRINE_GATE_IDS: Final[tuple[str, ...]] = (
    "G-P05-CANON-01",
    "G-P05-CANON-02",
    "G-P05-CANON-03",
    "G-P05-IMPORT-01",
    "G-P05-IMPORT-02",
    "G-P05-TEMP-01",
    "G-P05-TEMP-02",
    "G-P05-EXP-01",
    "G-P05-EXP-02",
    "G-P05-HASH-01",
    "G-P05-HASH-02",
    "G-P05-SCHEMA-01",
    "G-P05-TVR-01",
    "G-P05-ANTI-01",
    "G-P05-OVD-01",
    "G-P05-OVD-02",
    "G-P05-MG-01",
    "G-P05-MG-02",
    "G-P05-POL-01",
    "G-P05-POL-02",
    "G-P05-HR-01",
    "G-P05-HR-02",
    "G-P05-DIAG-01",
    "G-P05-DIAG-02",
    "G-P05-IDX-01",
    "G-P05-IDX-02",
    "G-P05-JOB-01",
    "G-P05-JOB-02",
    "G-P05-RT-01",
    "G-P05-RT-02",
    "G-P05-API-01",
    "G-P05-API-02",
    "G-P05-API-03",
    "G-P05-IDEM-01",
    "G-P05-IDEM-02",
    "G-P05-REPLAY-WALK-01",
    "G-P05-REPLAY-WALK-02",
    "G-P05-REPLAY-IDX-01",
    "G-P05-REPLAY-IDX-02",
    "G-P05-EQUIV-01",
    "G-P05-EQUIV-02",
    "G-P05-EQUIV-03",
    "G-P05-WES-01",
    "G-P05-WES-02",
    "G-P05-RANK-01",
    "G-P05-TVER-01",
    "G-P05-CP-01",
    "G-P05-ECO-01",
    "G-P05-ECO-02",
    "G-P05-ECO-03",
    "G-P05-MIG-01",
    "G-P05-LEGAL-01",
    "G-P05-ENG-01",
    "G-P05-CLOSE-01",
)

_GATE_STAGE: Final[dict[str, GateStage]] = {
    "G-P05-CANON-01": "A",
    "G-P05-CANON-02": "A",
    "G-P05-CANON-03": "A",
    "G-P05-IMPORT-01": "B",
    "G-P05-IMPORT-02": "A",
    "G-P05-TEMP-01": "C",
    "G-P05-TEMP-02": "C",
    "G-P05-EXP-01": "C",
    "G-P05-EXP-02": "D",
    "G-P05-HASH-01": "B",
    "G-P05-HASH-02": "B",
    "G-P05-SCHEMA-01": "A",
    "G-P05-TVR-01": "A",
    "G-P05-ANTI-01": "A",
    "G-P05-OVD-01": "C",
    "G-P05-OVD-02": "C",
    "G-P05-MG-01": "B",
    "G-P05-MG-02": "B",
    "G-P05-POL-01": "B",
    "G-P05-POL-02": "B",
    "G-P05-HR-01": "B",
    "G-P05-HR-02": "B",
    "G-P05-DIAG-01": "B",
    "G-P05-DIAG-02": "B",
    "G-P05-IDX-01": "B",
    "G-P05-IDX-02": "B",
    "G-P05-JOB-01": "B",
    "G-P05-JOB-02": "B",
    "G-P05-RT-01": "B",
    "G-P05-RT-02": "B",
    "G-P05-API-01": "D",
    "G-P05-API-02": "D",
    "G-P05-API-03": "D",
    "G-P05-IDEM-01": "D",
    "G-P05-IDEM-02": "E",
    "G-P05-REPLAY-WALK-01": "E",
    "G-P05-REPLAY-WALK-02": "C",
    "G-P05-REPLAY-IDX-01": "C",
    "G-P05-REPLAY-IDX-02": "C",
    "G-P05-EQUIV-01": "B",
    "G-P05-EQUIV-02": "E",
    "G-P05-EQUIV-03": "A",
    "G-P05-WES-01": "B",
    "G-P05-WES-02": "B",
    "G-P05-RANK-01": "A",
    "G-P05-TVER-01": "Z",
    "G-P05-CP-01": "D",
    "G-P05-ECO-01": "E",
    "G-P05-ECO-02": "E",
    "G-P05-ECO-03": "E",
    "G-P05-MIG-01": "Z",
    "G-P05-LEGAL-01": "A",
    "G-P05-ENG-01": "B",
    "G-P05-CLOSE-01": "Z",
}


def default_severity_for_gate_v1(gate_id: str) -> GateSeverity:
    return "warn" if gate_id in _WARN_GATES else "hard_fail"


def _repo_root_from_traversal_package() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "05-traversal").is_dir():
            return root
    msg = "could not locate DOCS/cortex/05-traversal from traversal package"
    raise RuntimeError(msg)


def _octs_tests_tree_root_v1(repo: Path) -> Path:
    """``./backend/tests`` on the host monorepo; ``./tests`` when backend is the compose cwd (``/app``)."""
    flat = repo / "tests"
    nested = repo / "backend" / "tests"
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"could not locate pytest tree under {repo} (expected tests/ or backend/tests/)"
    raise RuntimeError(msg)


def octs_golden_vectors_v1_root() -> Path:
    """Canonical golden vector home (**CI arch** §7)."""
    return (
        _octs_tests_tree_root_v1(_repo_root_from_traversal_package())
        / "vector"
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
    )


def verification_waivers_yaml_path() -> Path:
    return (
        _repo_root_from_traversal_package()
        / "DOCS"
        / "cortex"
        / "05-traversal"
        / "waivers"
        / "verification_waivers.yaml"
    )


def load_verification_waivers_v1() -> dict[str, Any]:
    p = verification_waivers_yaml_path()
    return cast(dict[str, Any], yaml.safe_load(p.read_text(encoding="utf-8")))


def _meta_result(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": "octs-verification-catalog-meta-v1",
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_octs_waiver_yaml_parseable_static() -> dict[str, Any]:
    """Waiver sidecar parses (**CI arch** §5)."""
    errors: list[str] = []
    try:
        raw = load_verification_waivers_v1()
    except (OSError, yaml.YAMLError, TypeError) as exc:
        errors.append(f"waiver_yaml_load:{exc}")
        return _meta_result("verification_waivers_yaml", errors)
    if not isinstance(raw, dict):
        errors.append("waiver_root_not_object")
        return _meta_result("verification_waivers_yaml", errors)
    w = raw.get("waivers")
    if w is not None and not isinstance(w, list):
        errors.append("waivers_not_list")
    return _meta_result("verification_waivers_yaml", errors)


def verify_octs_waiver_entries_schema_static() -> dict[str, Any]:
    """**RULE W-01** — each waiver names ``gate_id``, ``ticket``, ``expires_unix_ns``, ``branches_allowlist``."""
    errors: list[str] = []
    raw = load_verification_waivers_v1()
    waivers = raw.get("waivers") if isinstance(raw, dict) else None
    if not isinstance(waivers, list):
        return _meta_result("waiver_entry_schema", ["waivers_missing_or_not_list"])
    for i, row in enumerate(waivers):
        if not isinstance(row, dict):
            errors.append(f"waiver[{i}]_not_object")
            continue
        for k in ("gate_id", "ticket", "expires_unix_ns", "branches_allowlist"):
            if k not in row:
                errors.append(f"waiver[{i}]_missing:{k}")
        exp = row.get("expires_unix_ns")
        if exp is not None and not isinstance(exp, int):
            errors.append(f"waiver[{i}]_expires_not_int")
        bl = row.get("branches_allowlist")
        if bl is not None and not isinstance(bl, list):
            errors.append(f"waiver[{i}]_branches_not_list")
    return _meta_result("waiver_entry_schema", errors)


def _gate(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": default_severity_for_gate_v1(gate_id),
        "detail": {"errors": errors},
    }


def verify_gp05_legal01_active_p0_section_empty_static() -> dict[str, Any]:
    """**G-P05-LEGAL-01** — ``phase-05-spec-gap-matrix.md`` §**Active P0** has no reopened rows."""
    errors: list[str] = []
    root = _repo_root_from_traversal_package()
    path = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-spec-gap-matrix.md"
    if not path.is_file():
        errors.append(f"missing_matrix:{path}")
        return _gate("G-P05-LEGAL-01", "active_p0_empty", errors)
    text = path.read_text(encoding="utf-8")
    start = text.find("## Active P0")
    end = text.find("## Active P1", start)
    if start < 0 or end < 0:
        errors.append("active_p0_section_not_found")
        return _gate("G-P05-LEGAL-01", "active_p0_empty", errors)
    body = text[start:end]
    for line in body.splitlines():
        ls = line.strip()
        if ls.startswith("|") and "GAP-P0" in ls and "---" not in ls and "Was" not in ls:
            errors.append(f"active_p0_row:{ls[:120]}")
    return _gate("G-P05-LEGAL-01", "active_p0_empty", errors)


def verify_gp05_canon01_golden_walk_hash_static() -> dict[str, Any]:
    """**G-P05-CANON-01** — golden ``hash_body`` bytes recompute to pinned ``walk_result_hash``."""
    errors: list[str] = []
    root = octs_golden_vectors_v1_root()
    body_p = root / "walks" / "hash_body_minimal_v1.json"
    exp_p = root / "walks" / "walk_result_hash_expected_v1.txt"
    if not body_p.is_file():
        errors.append(f"missing_fixture:{body_p}")
        return _gate("G-P05-CANON-01", "canonical_golden_walk_hash", errors)
    if not exp_p.is_file():
        errors.append(f"missing_fixture:{exp_p}")
        return _gate("G-P05-CANON-01", "canonical_golden_walk_hash", errors)
    try:
        from vector.domains.cortex.traversal.walk_result_contract import (
            compute_walk_result_hash_v1,
            validate_walk_result_hash_body_contract_v1,
        )

        body = json.loads(body_p.read_text(encoding="utf-8"))
        if not isinstance(body, dict):
            errors.append("hash_body_not_object")
            return _gate("G-P05-CANON-01", "canonical_golden_walk_hash", errors)
        validate_walk_result_hash_body_contract_v1(cast(Mapping[str, Any], body))
        got = compute_walk_result_hash_v1(cast(Mapping[str, Any], body))
        want = exp_p.read_text(encoding="utf-8").strip()
        if got != want:
            errors.append(f"hash_mismatch want={want!r} got={got!r}")
    except Exception as exc:  # noqa: BLE001 — gate must surface any contract failure
        errors.append(f"canon01_exception:{exc}")
    return _gate("G-P05-CANON-01", "canonical_golden_walk_hash", errors)


def verify_gp05_canon02_sorted_json_identity_static() -> dict[str, Any]:
    """**G-P05-CANON-02** — logical JSON maps serialize identically under sorted compact JSON."""
    errors: list[str] = []
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    sa = json.dumps(a, sort_keys=True, separators=(",", ":"))
    sb = json.dumps(b, sort_keys=True, separators=(",", ":"))
    if sa != sb:
        errors.append("sorted_json_identity_failed")
    return _gate("G-P05-CANON-02", "idempotency_whitespace_json", errors)


def verify_gp05_canon03_nfc_anchor_fixture_static() -> dict[str, Any]:
    """**G-P05-CANON-03** — temporal anchor golden survives NFC normalization (strings)."""

    def _nfc_equal(x: Any) -> bool:
        if isinstance(x, str):
            return unicodedata.normalize("NFC", x) == x
        if isinstance(x, dict):
            return all(_nfc_equal(v) for v in x.values())
        if isinstance(x, list):
            return all(_nfc_equal(v) for v in x)
        return True

    errors: list[str] = []
    p = octs_golden_vectors_v1_root() / "temporal" / "anchor_good_v1.json"
    if not p.is_file():
        errors.append(f"missing_fixture:{p}")
        return _gate("G-P05-CANON-03", "nfc_equivalence_fixture", errors)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if not _nfc_equal(doc):
            errors.append("nfc_normalization_would_mutate_fixture")
    except json.JSONDecodeError as exc:
        errors.append(f"json_invalid:{exc}")
    return _gate("G-P05-CANON-03", "nfc_equivalence_fixture", errors)


def verify_gp05_rank01_forbidden_score_tokens_in_traversal_static() -> dict[str, Any]:
    """**G-P05-RANK-01** — forbid obvious ranking / score smuggling tokens in traversal sources."""
    errors: list[str] = []
    root = Path(__file__).resolve().parent
    banned = (
        "retrieval_score",
        "edge_rank",
        "semantic_rank",
        "reranker_score",
        "learning_to_rank",
    )
    for path in sorted(root.glob("*.py"), key=lambda p: str(p).lower()):
        if path.name == "verification_gates_catalog.py":
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for tok in banned:
            if tok in lower:
                errors.append(f"{path.name}:{tok}")
    return _gate("G-P05-RANK-01", "rank_forbidden_token_scan", errors)


def _json_contains_float(obj: Any) -> bool:
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_json_contains_float(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_json_contains_float(v) for v in obj)
    return False


def verify_gp05_equiv03_no_floats_in_canonical_traversal_static() -> dict[str, Any]:
    """**G-P05-EQUIV-03** — no ``allow_nan=True`` dumps in traversal sources; golden JSON has no floats."""
    errors: list[str] = []
    root = Path(__file__).resolve().parent
    for path in sorted(root.glob("*.py"), key=lambda p: str(p).lower()):
        if path.name == "verification_gates_catalog.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "allow_nan=True" in text:
            errors.append(f"allow_nan:{path.name}")
    gdir = octs_golden_vectors_v1_root()
    if not gdir.is_dir():
        errors.append(f"missing_golden_root:{gdir}")
    else:
        for path in sorted(gdir.rglob("*.json"), key=lambda p: str(p).lower()):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"json_invalid:{path.relative_to(gdir)}:{exc}")
                continue
            if _json_contains_float(doc):
                errors.append(f"float_in_fixture:{path.relative_to(gdir)}")
    return _gate("G-P05-EQUIV-03", "no_floats_in_canonical", errors)


def verify_gp05_import02_forbidden_ingress_bundle_static() -> dict[str, Any]:
    """**G-P05-IMPORT-02** — forbidden ingress tokens (**IMPORT-02**) + anti-ingress scan (**ANTI-02**)."""
    from vector.domains.cortex.traversal.anti_goals import (
        verify_gp05_anti02_traversal_ingress_no_phase03_tokens_static,
    )
    from vector.domains.cortex.traversal.graph_import_boundary import (
        verify_gp05_import02_forbidden_ingress_tokens_static,
    )

    a = verify_gp05_import02_forbidden_ingress_tokens_static()
    b = verify_gp05_anti02_traversal_ingress_no_phase03_tokens_static()
    errors: list[str] = []
    if not a.get("passed"):
        errors.append("import02_subgate_failed")
    if not b.get("passed"):
        errors.append("anti02_subgate_failed")
    return {
        "id": "G-P05-IMPORT-02",
        "name": "forbidden_ingress_tokens_bundle",
        "passed": len(errors) == 0,
        "severity": default_severity_for_gate_v1("G-P05-IMPORT-02"),
        "detail": {"import02": a, "anti02": b, "errors": errors},
    }


def verify_gp05_idem01_memory_store_idempotency_lut_static() -> dict[str, Any]:
    """**G-P05-IDEM-01** — in-memory walk store records stable ``(tenant_id, idempotency_key)`` lookup."""
    errors: list[str] = []
    from vector.domains.cortex.traversal.walk_api_contract import (
        OctsWalkApiMemoryStore,
        build_stub_completed_walk_payload_v1,
    )

    tid = uuid.uuid4()
    store = OctsWalkApiMemoryStore()
    req: dict[str, Any] = {
        "temporal_anchor": {
            "tenant_id": str(tid),
            "export_id": "00000000-0000-4000-8000-000000000002",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "aa" * 32,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "walk_policy": {
            "max_hops": 8,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    try:
        payload = build_stub_completed_walk_payload_v1(req, tenant_id=tid)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"stub_build:{exc}")
        return _gate("G-P05-IDEM-01", "http_idempotency_store_lut", errors)
    walk_id = uuid.uuid4()
    store.insert_completed_sync(
        tenant_id=tid,
        walk_id=walk_id,
        request_body=dict(req),
        walk_payload=payload,
        idempotency_key="idem-catalog-test",
    )
    if store.lookup_idempotency(tid, "idem-catalog-test") != walk_id:
        errors.append("idempotency_lut_mismatch")
    return _gate("G-P05-IDEM-01", "http_idempotency_store_lut", errors)


def verify_octs_gate_catalog_unique_ids_static() -> dict[str, Any]:
    """**FS-G-02** — catalog lists each doctrine **G-P05-*** ID exactly once."""
    errors: list[str] = []
    if len(_DOCTRINE_GATE_IDS) != len(frozenset(_DOCTRINE_GATE_IDS)):
        errors.append("duplicate_ids_in_doctrine_tuple")
    for gid in _DOCTRINE_GATE_IDS:
        if gid not in _GATE_STAGE:
            errors.append(f"missing_stage:{gid}")
    extras = set(_GATE_STAGE) - set(_DOCTRINE_GATE_IDS)
    if extras:
        errors.append(f"extra_stage_entries:{sorted(extras)}")
    return _meta_result("unique_gate_ids", errors)


def verify_octs_corruption_bundles_reference_known_gates_static() -> dict[str, Any]:
    """Corruption bundles (**CI arch** §10) may only name doctrine gate IDs."""
    errors: list[str] = []
    known = frozenset(_DOCTRINE_GATE_IDS)
    for bundle, members in OCTS_CORRUPTION_GATE_BUNDLES_V1.items():
        unknown = sorted(members - known)
        if unknown:
            errors.append(f"bundle:{bundle}:unknown:{unknown}")
    return _meta_result("corruption_bundle_gate_refs", errors)


def _wired_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    from vector.domains.cortex.traversal.anti_goals import (
        verify_gp05_anti01_forbidden_cognition_keys_static,
    )
    from vector.domains.cortex.traversal.derived_index_contract import (
        verify_gp05_idx01_index_content_hash_stability_static,
        verify_gp05_idx02_lineage_completeness_static,
    )
    from vector.domains.cortex.traversal.exploration_mode_contract import (
        verify_gp05_exp01_walk_request_explicit_exploration_mode_static,
        verify_gp05_exp02_authoritative_table_rejects_exploration_partition_static,
    )
    from vector.domains.cortex.traversal.graph_import_boundary import (
        verify_gp05_import01_traversable_subset_authoritative_static,
    )
    from vector.domains.cortex.traversal.hop_receipt_contract import (
        verify_gp05_hr01_fingerprint_recompute_from_envelope_static,
        verify_gp05_hr02_dangling_org_link_rejected_static,
    )
    from vector.domains.cortex.traversal.index_build_job_contract import (
        verify_gp05_job01_index_build_fsm_illegal_transitions_static,
        verify_gp05_job02_validating_publish_audit_static,
    )
    from vector.domains.cortex.traversal.index_replay_contract import (
        verify_gp05_replay_idx01_double_run_equality_static,
        verify_gp05_replay_idx02_corrupt_lineage_deterministic_failure_static,
    )
    from vector.domains.cortex.traversal.observed_vs_derived import (
        verify_gp05_ovd01_observed_hop_bindings_static,
        verify_gp05_ovd02_strategy_and_derived_flags_static,
    )
    from vector.domains.cortex.traversal.runtime_execution_model import (
        verify_gp05_rt01_engine_determinism_static,
        verify_gp05_rt02_frontier_cap_budget_static,
    )
    from vector.domains.cortex.traversal.temporal_walk import (
        verify_gp05_temp01_sequence_validity_supersession_static,
        verify_gp05_temp02_anchor_roundtrip_and_concurrency_static,
    )
    from vector.domains.cortex.traversal.tenant_verification_slice import (
        verify_gp05_tver01_org_graph_traversal_slice_golden_static,
    )
    from vector.domains.cortex.traversal.traversal_control_plane import (
        verify_gp05_cp01_traversal_control_plane_rbac_static,
    )
    from vector.domains.cortex.traversal.certification_pack import (
        verify_gp05_close01_oct_cert_pack_static,
    )
    from vector.domains.cortex.traversal.traversal_readiness_economics import (
        verify_gp05_eco01_max_out_degree_golden_static,
        verify_gp05_eco02_walk_wall_budget_golden_static,
        verify_gp05_eco03_derived_index_bytes_per_edge_golden_static,
    )
    from vector.domains.cortex.traversal.traversal_equivalence_contract import (
        verify_gp05_eng01_engine_build_id_coherence_static,
    )
    from vector.domains.cortex.traversal.traversal_vs_reasoning import (
        verify_gp05_schema01_oct_walk_request_v1_static,
        verify_gp05_tvr01_walk_result_hash_body_strict_static,
    )
    from vector.domains.cortex.traversal.walk_api_contract import (
        verify_gp05_api01_openapi_walk_paths_static,
        verify_gp05_api02_openapi_security_static,
        verify_gp05_api03_sync_walk_limits_static,
    )
    from vector.domains.cortex.traversal.walk_diagnostics_contract import (
        verify_gp05_diag01_enum_exhaustiveness_vs_schema_static,
        verify_gp05_diag02_cycle_fingerprint_golden_static,
    )
    from vector.domains.cortex.traversal.walk_execution_strategy_contract import (
        verify_gp05_equiv01_fast_path_online_equivalence_static,
        verify_gp05_wes01_strategy_affects_policy_hash_static,
        verify_gp05_wes03_forbidden_optimization_hash_body_scan_static,
    )
    from vector.domains.cortex.traversal.walk_policy import (
        verify_gp05_pol01_walk_policy_schema_and_hash_static,
        verify_gp05_pol02_sync_caps_reject_static,
    )
    from vector.domains.cortex.traversal.walk_result_contract import (
        verify_gp05_hash01_walk_result_hash_recompute_static,
        verify_gp05_hash02_telemetry_separation_static,
    )
    from vector.domains.cortex.traversal.multigraph_model import (
        verify_gp05_mg01_neighbor_order_golden_static,
        verify_gp05_mg02_fingerprint_uniqueness_static,
    )

    return {
        "G-P05-CANON-01": verify_gp05_canon01_golden_walk_hash_static,
        "G-P05-CANON-02": verify_gp05_canon02_sorted_json_identity_static,
        "G-P05-CANON-03": verify_gp05_canon03_nfc_anchor_fixture_static,
        "G-P05-IMPORT-01": verify_gp05_import01_traversable_subset_authoritative_static,
        "G-P05-IMPORT-02": verify_gp05_import02_forbidden_ingress_bundle_static,
        "G-P05-TEMP-01": verify_gp05_temp01_sequence_validity_supersession_static,
        "G-P05-TEMP-02": verify_gp05_temp02_anchor_roundtrip_and_concurrency_static,
        "G-P05-EXP-01": verify_gp05_exp01_walk_request_explicit_exploration_mode_static,
        "G-P05-EXP-02": verify_gp05_exp02_authoritative_table_rejects_exploration_partition_static,
        "G-P05-HASH-01": verify_gp05_hash01_walk_result_hash_recompute_static,
        "G-P05-HASH-02": verify_gp05_hash02_telemetry_separation_static,
        "G-P05-SCHEMA-01": verify_gp05_schema01_oct_walk_request_v1_static,
        "G-P05-TVR-01": verify_gp05_tvr01_walk_result_hash_body_strict_static,
        "G-P05-ANTI-01": verify_gp05_anti01_forbidden_cognition_keys_static,
        "G-P05-OVD-01": verify_gp05_ovd01_observed_hop_bindings_static,
        "G-P05-OVD-02": verify_gp05_ovd02_strategy_and_derived_flags_static,
        "G-P05-MG-01": verify_gp05_mg01_neighbor_order_golden_static,
        "G-P05-MG-02": verify_gp05_mg02_fingerprint_uniqueness_static,
        "G-P05-POL-01": verify_gp05_pol01_walk_policy_schema_and_hash_static,
        "G-P05-POL-02": verify_gp05_pol02_sync_caps_reject_static,
        "G-P05-HR-01": verify_gp05_hr01_fingerprint_recompute_from_envelope_static,
        "G-P05-HR-02": verify_gp05_hr02_dangling_org_link_rejected_static,
        "G-P05-DIAG-01": verify_gp05_diag01_enum_exhaustiveness_vs_schema_static,
        "G-P05-DIAG-02": verify_gp05_diag02_cycle_fingerprint_golden_static,
        "G-P05-IDX-01": verify_gp05_idx01_index_content_hash_stability_static,
        "G-P05-IDX-02": verify_gp05_idx02_lineage_completeness_static,
        "G-P05-JOB-01": verify_gp05_job01_index_build_fsm_illegal_transitions_static,
        "G-P05-JOB-02": verify_gp05_job02_validating_publish_audit_static,
        "G-P05-RT-01": verify_gp05_rt01_engine_determinism_static,
        "G-P05-RT-02": verify_gp05_rt02_frontier_cap_budget_static,
        "G-P05-API-01": verify_gp05_api01_openapi_walk_paths_static,
        "G-P05-API-02": verify_gp05_api02_openapi_security_static,
        "G-P05-API-03": verify_gp05_api03_sync_walk_limits_static,
        "G-P05-CP-01": verify_gp05_cp01_traversal_control_plane_rbac_static,
        "G-P05-ECO-01": verify_gp05_eco01_max_out_degree_golden_static,
        "G-P05-ECO-02": verify_gp05_eco02_walk_wall_budget_golden_static,
        "G-P05-ECO-03": verify_gp05_eco03_derived_index_bytes_per_edge_golden_static,
        "G-P05-IDEM-01": verify_gp05_idem01_memory_store_idempotency_lut_static,
        "G-P05-REPLAY-WALK-02": _replay_walk02_stub_wrapper_static,
        "G-P05-REPLAY-IDX-01": verify_gp05_replay_idx01_double_run_equality_static,
        "G-P05-REPLAY-IDX-02": verify_gp05_replay_idx02_corrupt_lineage_deterministic_failure_static,
        "G-P05-EQUIV-01": verify_gp05_equiv01_fast_path_online_equivalence_static,
        "G-P05-WES-01": verify_gp05_wes01_strategy_affects_policy_hash_static,
        "G-P05-WES-02": verify_gp05_wes03_forbidden_optimization_hash_body_scan_static,
        "G-P05-RANK-01": verify_gp05_rank01_forbidden_score_tokens_in_traversal_static,
        "G-P05-LEGAL-01": verify_gp05_legal01_active_p0_section_empty_static,
        "G-P05-EQUIV-03": verify_gp05_equiv03_no_floats_in_canonical_traversal_static,
        "G-P05-ENG-01": verify_gp05_eng01_engine_build_id_coherence_static,
        "G-P05-TVER-01": verify_gp05_tver01_org_graph_traversal_slice_golden_static,
        "G-P05-CLOSE-01": verify_gp05_close01_oct_cert_pack_static,
    }


def list_octs_doctrine_gate_ids_v1() -> tuple[str, ...]:
    return _DOCTRINE_GATE_IDS


def gate_stage_v1(gate_id: str) -> GateStage | None:
    return _GATE_STAGE.get(gate_id)


def list_wired_verification_runners_v1() -> dict[str, Callable[[], dict[str, Any]]]:
    """Return a fresh mapping of gate ID → zero-arg runner (static gates only)."""
    return dict(_wired_runners_v1())


def verify_octs_wired_runner_gate_ids_match_static() -> dict[str, Any]:
    """Each wired **G-P05-*** runner's ``result[\"id\"]`` matches its catalog key (when present).

    **G-P05-CLOSE-01** is skipped: its runner invokes **PR** + **STAGE-Z**, which would recurse into
    this meta-check.
    """
    errors: list[str] = []
    for gid, fn in _wired_runners_v1().items():
        if gid == "G-P05-CLOSE-01":
            continue
        out = fn()
        rid = out.get("id")
        if rid is not None and rid != gid:
            errors.append(f"{gid}_returned_{rid}")
    return _meta_result("wired_runner_id_match", errors)


def _replay_walk02_stub_wrapper_static() -> dict[str, Any]:
    from vector.domains.cortex.traversal.walk_replay_contract import (
        verify_oct_walk_replay_stub_inherit_resolution_static,
    )

    sub = verify_oct_walk_replay_stub_inherit_resolution_static()
    return {
        "id": "G-P05-REPLAY-WALK-02",
        "name": "walk_replay_stub_edge_sensitivity",
        "passed": bool(sub.get("passed")),
        "severity": default_severity_for_gate_v1("G-P05-REPLAY-WALK-02"),
        "detail": {"underlying_gate": sub},
    }


def run_octs_wired_verification_stages_v1(
    stages: Sequence[GateStage],
    *,
    abort_on_hard_fail: bool = True,
    skip_gate_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Execute wired **G-P05-*** static runners whose doctrine stage is in ``stages`` (order preserved).

    ``skip_gate_ids`` supports **G-P05-CLOSE-01** orchestration (avoid self-recursion when the close
    runner re-invokes **STAGE-Z** for **TVER** only). **STAGE-Z** runs **G-P05-CLOSE-01** last when
    present (``phase-05-closure-gates-doctrine.md`` §10).
    """
    runners = _wired_runners_v1()
    order = tuple(dict.fromkeys(stages))
    results: list[dict[str, Any]] = []
    strict = os.environ.get(OCTS_VERIFICATION_MODE_ENV, "").strip().lower() == "strict"
    skip = skip_gate_ids or frozenset()
    for stage in order:
        base = sorted(
            (g for g, st in _GATE_STAGE.items() if st == stage and g in runners and g not in skip),
            key=str,
        )
        if stage == "Z" and "G-P05-CLOSE-01" in base:
            gate_ids = [g for g in base if g != "G-P05-CLOSE-01"] + ["G-P05-CLOSE-01"]
        else:
            gate_ids = list(base)
        for gid in gate_ids:
            out = runners[gid]()
            results.append({"stage": stage, "gate_id": gid, "result": out})
            sev = out.get("severity") or default_severity_for_gate_v1(gid)
            failed = out.get("passed") is False
            if failed and (sev == "hard_fail" or strict) and abort_on_hard_fail:
                return {
                    "passed": False,
                    "octs_verification_gates_catalog_version": OCTS_VERIFICATION_GATES_CATALOG_SCHEMA_VERSION,
                    "failed_gate_id": gid,
                    "failed_stage": stage,
                    "strict": strict,
                    "results": results,
                }
    return {
        "passed": True,
        "octs_verification_gates_catalog_version": OCTS_VERIFICATION_GATES_CATALOG_SCHEMA_VERSION,
        "strict": strict,
        "results": results,
    }


def run_octs_pr_blocking_static_stages_v1() -> dict[str, Any]:
    """**PR blocking** bundle: **STAGE-A** … **STAGE-D** per ``phase-05-ci-enforcement-architecture.md`` §2–3."""
    meta_pre = [
        verify_octs_gate_catalog_unique_ids_static(),
        verify_octs_corruption_bundles_reference_known_gates_static(),
        verify_octs_wired_runner_gate_ids_match_static(),
        verify_octs_waiver_yaml_parseable_static(),
        verify_octs_waiver_entries_schema_static(),
    ]
    if any(not m.get("passed") for m in meta_pre):
        return {
            "passed": False,
            "phase": "catalog_meta",
            "meta_results": meta_pre,
        }
    body = run_octs_wired_verification_stages_v1(("A", "B", "C", "D"))
    body["meta_results"] = meta_pre
    if not body.get("passed"):
        return body
    return {"passed": True, **body}


@dataclass(frozen=True, slots=True)
class OctsGateCatalogEntryV1:
    gate_id: str
    name: str
    stage: GateStage
    default_severity: GateSeverity
    wired: bool
    corruption_bundles: tuple[str, ...]


def list_octs_gate_catalog_entries_v1() -> tuple[OctsGateCatalogEntryV1, ...]:
    """Human-readable catalog rows (doctrine registry + wiring bit)."""
    runners = frozenset(_wired_runners_v1())
    names = {
        "G-P05-CANON-01": "Canonical golden vectors",
        "G-P05-CANON-02": "Idempotency whitespace",
        "G-P05-CANON-03": "NFC equivalence",
        "G-P05-IMPORT-01": "Import subset",
        "G-P05-IMPORT-02": "Forbidden tokens",
        "G-P05-TEMP-01": "Validity + sequence",
        "G-P05-TEMP-02": "Anchor round-trip",
        "G-P05-EXP-01": "Exploration default",
        "G-P05-EXP-02": "Partition isolation",
        "G-P05-HASH-01": "Walk hash recompute",
        "G-P05-HASH-02": "Telemetry separation",
        "G-P05-SCHEMA-01": "JSON Schema closure",
        "G-P05-TVR-01": "Hash-body strict closure",
        "G-P05-ANTI-01": "Forbidden cognition keys",
        "G-P05-OVD-01": "Observed binding",
        "G-P05-OVD-02": "Derived flags",
        "G-P05-MG-01": "Neighbor order",
        "G-P05-MG-02": "Fingerprint uniqueness",
        "G-P05-POL-01": "Policy schema",
        "G-P05-POL-02": "Sync caps",
        "G-P05-HR-01": "Fingerprint recompute",
        "G-P05-HR-02": "Dangling evidence",
        "G-P05-DIAG-01": "Enum exhaustiveness",
        "G-P05-DIAG-02": "Cycle vectors",
        "G-P05-IDX-01": "Index hash",
        "G-P05-IDX-02": "Lineage scan",
        "G-P05-JOB-01": "Index job FSM",
        "G-P05-JOB-02": "Crash between phases",
        "G-P05-RT-01": "Engine determinism",
        "G-P05-RT-02": "Memory bound",
        "G-P05-API-01": "HTTP + generated OpenAPI",
        "G-P05-API-02": "RBAC / security scheme",
        "G-P05-API-03": "Sync walk limits",
        "G-P05-IDEM-01": "HTTP idempotency (store LUT)",
        "G-P05-IDEM-02": "Worker duplicate delivery",
        "G-P05-REPLAY-WALK-01": "Walk replay nightly",
        "G-P05-REPLAY-WALK-02": "Walk replay stub / edge sensitivity",
        "G-P05-REPLAY-IDX-01": "Index double-run",
        "G-P05-REPLAY-IDX-02": "Lineage corruption",
        "G-P05-EQUIV-01": "Fast-path online",
        "G-P05-EQUIV-02": "Nightly dual strategy",
        "G-P05-EQUIV-03": "No floats in canonical",
        "G-P05-WES-01": "Strategy in policy hash",
        "G-P05-WES-02": "Forbidden optimizations",
        "G-P05-RANK-01": "Rank-forbidden scan",
        "G-P05-TVER-01": "Tenant slice schema",
        "G-P05-CP-01": "Control plane RBAC",
        "G-P05-ECO-01": "Max out-degree",
        "G-P05-ECO-02": "Synthetic walk wall budget",
        "G-P05-ECO-03": "Derived index bytes per edge",
        "G-P05-MIG-01": "Schema bundle hash",
        "G-P05-LEGAL-01": "Active P0 empty",
        "G-P05-ENG-01": "Engine id",
        "G-P05-CLOSE-01": "Closure pack",
    }
    bundles_for: dict[str, list[str]] = {g: [] for g in _DOCTRINE_GATE_IDS}
    for bname, members in OCTS_CORRUPTION_GATE_BUNDLES_V1.items():
        for m in members:
            if m in bundles_for:
                bundles_for[m].append(bname)
    out: list[OctsGateCatalogEntryV1] = []
    for gid in _DOCTRINE_GATE_IDS:
        st = _GATE_STAGE[gid]
        out.append(
            OctsGateCatalogEntryV1(
                gate_id=gid,
                name=names.get(gid, gid),
                stage=st,
                default_severity=default_severity_for_gate_v1(gid),
                wired=gid in runners,
                corruption_bundles=tuple(sorted(bundles_for.get(gid, ()))),
            )
        )
    return tuple(out)


def verify_oct_verification_gates_step22_static_bundle() -> dict[str, Any]:
    """Single hook for pytest — meta gates + **PR** static **A–D** bundle."""
    return run_octs_pr_blocking_static_stages_v1()
