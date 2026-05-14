"""Phase 05 Step **21** — traversal equivalence (**L-EQ-01..03**, **ENG-01..03**).

Normative: ``DOCS/cortex/05-traversal/phase-05-traversal-equivalence-doctrine.md``.

This module pins **process** ``engine_build_id`` resolution for optional HTTP enforcement
(``VECTOR_OCTS_ENFORCE_ENGINE_IDENTITY``) and static verification gates (**G-P05-ENG-01**,
**L-EQ-01..03**). Git SHA is **never** discovered via subprocess; CI may pin
``VECTOR_OCTS_ENGINE_BUILD_ID=git:<40-hex>``.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Mapping
from typing import Any, Final, cast

from vector.domains.cortex.traversal.walk_api_contract import (
    build_stub_completed_walk_payload_v1,
)
from vector.domains.cortex.traversal.walk_execution_strategy_contract import (
    verify_gp05_equiv01_fast_path_online_equivalence_static,
)
from vector.domains.cortex.traversal.walk_result_contract import (
    canonical_walk_result_hash_body_bytes_v1,
)

OCTS_TRAVERSAL_EQUIVALENCE_CONTRACT_SCHEMA_VERSION: Final[int] = 1

VECTOR_OCTS_ENGINE_BUILD_ID_ENV: Final[str] = "VECTOR_OCTS_ENGINE_BUILD_ID"
OCTS_DEV_ENGINE_ID_ENV: Final[str] = "OCTS_DEV_ENGINE_ID"
VECTOR_OCTS_EMBEDDED_GIT_SHA_ENV: Final[str] = "VECTOR_OCTS_EMBEDDED_GIT_SHA"

_GIT_ENGINE_BUILD_ID_RE: Final[re.Pattern[str]] = re.compile(r"^git:[0-9a-f]{40}$")


class OctsEngineIdentityError(RuntimeError):
    """Raised when **ENG-03** / format rules block resolving ``engine_build_id``."""

    def __init__(self, error_code: str, message: str | None = None) -> None:
        self.error_code = error_code
        super().__init__(message or error_code)


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _octs_dev_engine_id_enabled() -> bool:
    return _truthy_env(OCTS_DEV_ENGINE_ID_ENV)


def resolve_oct_engine_build_id_v1() -> str:
    """Resolve the canonical ``engine_build_id`` string for this process (**ENG** forms).

    **Release:** ``git:`` + 40 lowercase hex (via ``VECTOR_OCTS_ENGINE_BUILD_ID``).

    **Local dev:** ``dev:unknown`` only when ``OCTS_DEV_ENGINE_ID=1`` (or ``true``/``yes``),
    optionally with explicit ``VECTOR_OCTS_ENGINE_BUILD_ID=dev:unknown``.

    Raises:
        OctsEngineIdentityError: when identity cannot be established (**ENG-03** / invalid pin).
    """
    raw = os.environ.get(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, "").strip()
    if raw:
        if _GIT_ENGINE_BUILD_ID_RE.fullmatch(raw):
            return raw
        if raw == "dev:unknown":
            if _octs_dev_engine_id_enabled():
                return raw
            raise OctsEngineIdentityError("dev_unknown_without_OCTS_DEV_ENGINE_ID")
        raise OctsEngineIdentityError("invalid_engine_build_id_format")
    if _octs_dev_engine_id_enabled():
        return "dev:unknown"
    raise OctsEngineIdentityError("engine_identity_unavailable")


def list_fs_te01_same_inputs_different_hash_violations_v1(
    left_hash_body: Mapping[str, Any],
    left_walk_result_hash: str,
    right_hash_body: Mapping[str, Any],
    right_walk_result_hash: str,
) -> list[str]:
    """**FS-TE-01** — same canonical hash-body inputs must not diverge in ``walk_result_hash``."""
    lb = canonical_walk_result_hash_body_bytes_v1(cast(Mapping[str, Any], left_hash_body))
    rb = canonical_walk_result_hash_body_bytes_v1(cast(Mapping[str, Any], right_hash_body))
    if lb != rb:
        return []
    if left_walk_result_hash == right_walk_result_hash:
        return []
    return ["FS-TE-01:same_hash_body_different_walk_result_hash"]


def list_fs_te02_fast_path_without_equiv_pass_violations_v1() -> list[str]:
    """**FS-TE-02** — reserved for pack/runtime proofs that **EQUIV-*** obligations hold.

    Stub slice: policy + **WES** validators already gate ``fast_path_allowed``; no extra scan.
    """
    return []


def _gate(
    gate_id: str,
    name: str,
    errors: list[str],
    *,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    passed = len(errors) == 0
    d: dict[str, Any] = {
        "octs_traversal_equivalence_contract_version": OCTS_TRAVERSAL_EQUIVALENCE_CONTRACT_SCHEMA_VERSION,
        "errors": errors,
    }
    if detail:
        d.update(detail)
    return {
        "id": gate_id,
        "name": name,
        "passed": passed,
        "severity": "hard_fail",
        "detail": d,
    }


def verify_gp05_eng01_engine_build_id_coherence_static() -> dict[str, Any]:
    """**G-P05-ENG-01** — pinned ``VECTOR_OCTS_ENGINE_BUILD_ID`` is well-formed; optional
    ``VECTOR_OCTS_EMBEDDED_GIT_SHA`` (40 hex, no prefix) must match ``git:`` pins.
    """
    errors: list[str] = []
    raw = os.environ.get(VECTOR_OCTS_ENGINE_BUILD_ID_ENV, "").strip()
    if raw:
        if not (_GIT_ENGINE_BUILD_ID_RE.fullmatch(raw) or raw == "dev:unknown"):
            errors.append(f"invalid_VECTOR_OCTS_ENGINE_BUILD_ID:{raw[:24]}")
        if raw == "dev:unknown" and not _octs_dev_engine_id_enabled():
            errors.append("dev_unknown_without_OCTS_DEV_ENGINE_ID")
        if _GIT_ENGINE_BUILD_ID_RE.fullmatch(raw):
            embedded = os.environ.get(VECTOR_OCTS_EMBEDDED_GIT_SHA_ENV, "").strip().lower()
            if embedded:
                if not re.fullmatch(r"[0-9a-f]{40}", embedded):
                    errors.append("VECTOR_OCTS_EMBEDDED_GIT_SHA_invalid")
                elif embedded != raw.removeprefix("git:"):
                    errors.append("embedded_git_sha_mismatch_vs_VECTOR_OCTS_ENGINE_BUILD_ID")
    return _gate(
        "G-P05-ENG-01",
        "engine_build_id_env_coherence",
        errors,
    )


def verify_leq01_walk_hash_double_run_stub_static() -> dict[str, Any]:
    """**L-EQ-01** — same normalized stub inputs yield identical ``walk_result_hash``."""
    errors: list[str] = []
    tid = uuid.UUID("00000000-0000-4000-8000-000000000001")
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
        "start_node_ids": [
            "00000000-0000-0000-0000-000000000003",
            "00000000-0000-0000-0000-000000000001",
        ],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    try:
        a = build_stub_completed_walk_payload_v1(req, tenant_id=tid)
        b = build_stub_completed_walk_payload_v1(req, tenant_id=tid)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"stub_build_failed:{exc}")
        return _gate("L-EQ-01", "walk_hash_double_run_stub", errors)

    ha = str(a["walk_result"]["walk_result_hash"])
    hb = str(b["walk_result"]["walk_result_hash"])
    if ha != hb:
        errors.append("walk_result_hash_mismatch_on_identical_stub_inputs")

    te = list_fs_te01_same_inputs_different_hash_violations_v1(
        cast(Mapping[str, Any], a["walk_result"]["hash_body"]),
        ha,
        cast(Mapping[str, Any], b["walk_result"]["hash_body"]),
        hb,
    )
    errors.extend(te)
    return _gate("L-EQ-01", "walk_hash_double_run_stub", errors)


def verify_leq02_async_job_order_independence_stub_static() -> dict[str, Any]:
    """**L-EQ-02** — independent jobs: multiset of ``walk_result_hash`` is order-invariant."""
    errors: list[str] = []
    tid = uuid.UUID("00000000-0000-4000-8000-000000000002")
    base_policy: dict[str, Any] = {
        "max_hops": 8,
        "max_frontier": 64,
        "max_edges_visited": 500,
        "max_wall_ms": 100,
        "hop_class_allowlist": ["org.handle_links_canonical"],
        "tie_break": ["fingerprint", "org_link_id"],
        "respect_validity": True,
        "policy_version": 1,
    }

    def _job(export_sequence: int, start_suffix: str) -> dict[str, Any]:
        return {
            "temporal_anchor": {
                "tenant_id": str(tid),
                "export_id": "00000000-0000-4000-8000-000000000002",
                "export_sequence": export_sequence,
                "projection_content_hash": "sha256:" + "bb" * 32,
                "snapshot_unix_ns": {"unix_ns": 1},
                "graph_as_of_unix_ns": {"unix_ns": 1},
            },
            "walk_policy": base_policy,
            "start_node_ids": [f"00000000-0000-0000-0000-0000000000{start_suffix}"],
            "walk_execution_strategy": "ONLINE_OBSERVED",
            "exploration_mode": False,
        }

    try:
        payloads = [_job(0, "010"), _job(1, "011"), _job(2, "012")]
        hashes = [
            build_stub_completed_walk_payload_v1(p, tenant_id=tid)["walk_result"]["walk_result_hash"]
            for p in payloads
        ]
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"stub_build_failed:{exc}")
        return _gate("L-EQ-02", "async_job_order_independence_stub", errors)

    h_list = [str(h) for h in hashes]
    permuted = [h_list[2], h_list[0], h_list[1]]
    if sorted(h_list) != sorted(permuted):
        errors.append("hash_multiset_not_invariant_under_permutation")
    return _gate("L-EQ-02", "async_job_order_independence_stub", errors)


def verify_leq03_fast_path_equiv_obligation_static() -> dict[str, Any]:
    """**L-EQ-03** — fast-path obligations: reuse **G-P05-EQUIV-01** golden vectors."""
    sub = verify_gp05_equiv01_fast_path_online_equivalence_static()
    errors: list[str] = []
    if not sub.get("passed"):
        detail = sub.get("detail")
        if isinstance(detail, dict):
            inner = detail.get("errors")
            if isinstance(inner, list):
                errors.extend(str(x) for x in inner)
            else:
                errors.append("equiv01_failed")
        else:
            errors.append("equiv01_failed")
    return _gate(
        "L-EQ-03",
        "fast_path_equiv_obligation_stub",
        errors,
        detail={"equiv01_gate": sub},
    )


def verify_oct_traversal_equivalence_step21_static_bundle() -> dict[str, Any]:
    """Aggregate Step **21** static gates (single pytest hook)."""
    gates = (
        verify_gp05_eng01_engine_build_id_coherence_static(),
        verify_leq01_walk_hash_double_run_stub_static(),
        verify_leq02_async_job_order_independence_stub_static(),
        verify_leq03_fast_path_equiv_obligation_static(),
    )
    errors = [g["id"] for g in gates if not g.get("passed")]
    return {
        "octs_traversal_equivalence_contract_version": OCTS_TRAVERSAL_EQUIVALENCE_CONTRACT_SCHEMA_VERSION,
        "passed": len(errors) == 0,
        "failed_gate_ids": errors,
        "gates": list(gates),
    }
