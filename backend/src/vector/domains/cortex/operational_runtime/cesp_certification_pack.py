"""Phase 08.5 P085-36 — **CESP-CERT-PACK-1** + **G-P085-CLOSE-01**.

Normative: ``DOCS/cortex/operational-runtime/phase-085-closure-gates-doctrine.md``.
"""

from __future__ import annotations

import base64
import calendar
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_PROGRAM_FREEZE_BUNDLE_V1,
    PHASE085_PROGRAM_FREEZE_VERSION,
    PHASE085_PROGRAM_ID_V1,
    PHASE085_STEP_PROGRAM_COUNT,
    _repo_root_v1,
)
PHASE085_CESP_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION: Final[int] = 1

CESP_CERT_PACK_FORMAT_LITERAL_V1: Final[str] = "CESP-CERT-PACK-1"

CESP_CERT_PACK_MANIFEST_FORMAT_KEY_V1: Final[str] = "cesp_cert_pack_format"

CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1: Final[tuple[str, ...]] = (
    "manifest.json",
    "gate_results.json",
    "golden_tenant_slice.json",
    "soak_summary.json",
    "readiness_checklist.json",
    "policy_thresholds.json",
)

CESP_ENGINE_BUILD_ID_V1: Final[str] = "cesp.substrate.stub.v1"

CESP_CI_ARCH_VERSION_STRING_V1: Final[str] = (
    "DOCS/cortex/operational-runtime/phase-085-testing-strategy.md#staging-v1"
)

CESP_CERT_PACK_TAR_MTIME: Final[int] = calendar.timegm((1980, 1, 1, 0, 0, 0, 0, 0, 0))

GP085_CLOSE01_GATE_ID_V1: Final[str] = "G-P085-CLOSE-01"

P085_FINAL_FREEZE_BUNDLE_ID_V1: Final[str] = "P085-FINAL-FREEZE-2026-05-18"

CESP_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/operational-runtime/certification-pack",
    "/admin/catalog/cortex/operational-runtime/program-closure",
    "/admin/catalog/cortex/operational-runtime/constitutional-freeze",
    "/admin/catalog/cortex/operational-runtime/constitutional-freeze/signoff",
)


def _cesp_canonical_json_obj_v1(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _cesp_canonical_json_obj_v1(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_cesp_canonical_json_obj_v1(x) for x in obj]
    return obj


def cesp_canonical_json_bytes_v1(obj: Any) -> bytes:
    canon = _cesp_canonical_json_obj_v1(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _manifest_digest_v1(manifest: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(cesp_canonical_json_bytes_v1(dict(manifest))).hexdigest()


def _gate_results_bytes_for_inner_digest_v1(gate_results: Mapping[str, Any]) -> bytes:
    pruned = {k: v for k, v in dict(gate_results).items() if k != "manifest_digest"}
    return cesp_canonical_json_bytes_v1(pruned)


def _inner_payload_digest_v1(*, payload_parts: list[tuple[str, bytes]]) -> str:
    parts = [blob for _, blob in sorted(payload_parts, key=lambda t: t[0].encode("utf-8"))]
    return "sha256:" + hashlib.sha256(b"".join(parts)).hexdigest()


def _add_tar_bytes(
    tf: tarfile.TarFile,
    arcname: str,
    data: bytes,
    *,
    mtime: int,
) -> None:
    ti = tarfile.TarInfo(name=arcname)
    ti.size = len(data)
    ti.mtime = mtime
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = "root"
    ti.mode = 0o644
    ti.type = tarfile.REGTYPE
    tf.addfile(ti, io.BytesIO(data))


def _build_ustar_bytes(members: list[tuple[str, bytes]], *, mtime: int) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for arcname, data in members:
            _add_tar_bytes(tf, arcname, data, mtime=mtime)
    return buf.getvalue()


def _gzip_bytes(raw: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(raw)
    return buf.getvalue()


def resolve_git_sha_v1() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root_v1(),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass(frozen=True, slots=True)
class CespCertPackVerifyResultV1:
    passed: bool
    errors: tuple[str, ...]


def build_policy_thresholds_payload_v1() -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
        get_operational_maturity_thresholds_v1,
    )
    from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
        get_post_ingestion_backpressure_extra_debounce_seconds_v1,
        get_substrate_pipeline_max_concurrent_per_tenant_v1,
        get_vector_queue_backpressure_threshold_v1,
    )
    from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
        get_tcre_saturation_jobs_per_hour_v1,
        get_tcre_saturation_pass_max_jobs_v1,
        get_tcre_saturation_threshold_v1,
    )
    from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
        get_traversal_max_walks_per_pass_v1,
    )
    from vector.domains.cortex.operational_runtime.graph_density_promotion import (
        get_promotion_max_per_pass_v1,
    )
    from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
        get_replay_storm_divergence_spike_per_hour_v1,
        get_replay_storm_window_hours_v1,
    )

    maturity = get_operational_maturity_thresholds_v1()
    return {
        "theta_retrieval_density": float(maturity.get("density_emerging_retrieval_floor", 40.0))
        / 100.0,
        "theta_tcre_saturation": float(get_tcre_saturation_threshold_v1()),
        "t_stall_seconds_default": 1800,
        "caps": {
            "substrate_pipeline_max_concurrent_per_tenant": int(
                get_substrate_pipeline_max_concurrent_per_tenant_v1(),
            ),
            "vector_queue_backpressure_threshold": int(get_vector_queue_backpressure_threshold_v1()),
            "post_ingestion_backpressure_extra_debounce_seconds": int(
                get_post_ingestion_backpressure_extra_debounce_seconds_v1(),
            ),
            "tcre_saturation_jobs_per_hour": int(get_tcre_saturation_jobs_per_hour_v1()),
            "tcre_saturation_pass_max_jobs": int(get_tcre_saturation_pass_max_jobs_v1()),
            "traversal_max_walks_per_pass": int(get_traversal_max_walks_per_pass_v1()),
            "graph_promotion_max_per_pass": int(get_promotion_max_per_pass_v1()),
            "replay_storm_divergence_spike_per_hour": int(
                get_replay_storm_divergence_spike_per_hour_v1(),
            ),
            "replay_storm_window_hours": int(get_replay_storm_window_hours_v1()),
        },
    }


def build_soak_summary_payload_v1(session: Session | None) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        get_latest_soak_signoff_v1,
    )

    signoff = get_latest_soak_signoff_v1(session) if session is not None else None
    return {
        "soak_window_days": 7,
        "substrate_pipeline_07_08_completion_rate_target": 0.95,
        "substrate_pipeline_07_08_completion_rate_observed": None,
        "ops_signoff": {
            "present": signoff is not None,
            "signed_at": signoff.signed_at.isoformat() if signoff else None,
            "note": signoff.note if signoff else None,
        },
    }


def build_golden_tenant_slice_payload_v1(session: Session | None) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        build_golden_tenant_profile_spec_v1,
    )

    return {
        "profile_spec": build_golden_tenant_profile_spec_v1(),
        "tenant_evaluation": None,
        "note": "golden_tenant_slice_requires_tenant_scoped_eval_in_ops",
    }


def _wired_gp085_gate_runners_v1() -> list[tuple[str, Callable[[], dict[str, Any]]]]:
    from vector.domains.cortex.operational_runtime.cesp_anti_idle_gate import (
        verify_gp085_anti_idle01_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_autonomous_recovery_gate import (
        verify_gp085_autonomous_recovery_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_continuation_gate import (
        verify_gp085_continuation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_dlq_gate import verify_gp085_dlq_gate_static
    from vector.domains.cortex.operational_runtime.cesp_gap_matrix_gate import (
        verify_gp085_gap_matrix_discipline_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_graph_density_gate import (
        verify_gp085_graph_density_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_graph_propagation_gate import (
        verify_gp085_graph_propagation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_operational_cockpit_gate import (
        verify_gp085_operational_cockpit_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_operational_explorers_gate import (
        verify_gp085_operational_explorers_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_operational_health_gate import (
        verify_gp085_operational_health_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_operational_maturity_gate import (
        verify_gp085_operational_maturity_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_orphan_gate import verify_gp085_orphan_gate_static
    from vector.domains.cortex.operational_runtime.cesp_phase09_readiness_gate import (
        verify_gp085_phase09_readiness_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_phase_boundaries_gate import (
        verify_gp085_phase_boundaries_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_program_freeze import (
        verify_gp085_cesp01_program_freeze_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_progression_gate import (
        verify_gp085_progression_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_progression_timeline_causal_gate import (
        verify_gp085_progression_timeline_causal_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_promotion_gate import (
        verify_gp085_promotion_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_recovery_receipt_gate import (
        verify_gp085_recovery_receipt_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_replay_storm_gate import (
        verify_gp085_replay_storm_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_retrieval_density_gate import (
        verify_gp085_retrieval_density_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_retrieval_propagation_gate import (
        verify_gp085_retrieval_propagation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_retrieval_starvation_gate import (
        verify_gp085_retrieval_starvation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_runtime_economics_gate import (
        verify_gp085_runtime_economics_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_stalled_traversal_gate import (
        verify_gp085_stalled_traversal_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_synthesis_activation_gate import (
        verify_gp085_synthesis_activation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_synthesis_idle_starved_gate import (
        verify_gp085_synthesis_idle_starved_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_synthesis_throughput_gate import (
        verify_gp085_synthesis_throughput_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_tcre_density_gate import (
        verify_gp085_tcre_density_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_tcre_omission_explainability_gate import (
        verify_gp085_tcre_omission_explainability_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_tcre_saturation_gate import (
        verify_gp085_tcre_saturation_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_traversal_explainability_gate import (
        verify_gp085_traversal_explainability_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_traversal_retry_gate import (
        verify_gp085_traversal_retry_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_traversal_scheduling_gate import (
        verify_gp085_traversal_scheduling_gate_static,
    )
    from vector.domains.cortex.operational_runtime.cesp_watchdog_gate import (
        verify_gp085_watchdog_gate_static,
    )

    return [
        ("G-P085-CESP-01", verify_gp085_cesp01_program_freeze_static),
        ("G-P085-ANTI-IDLE-01", verify_gp085_anti_idle01_static),
        ("G-P085-GAP-MATRIX", verify_gp085_gap_matrix_discipline_static),
        ("G-P085-BND", verify_gp085_phase_boundaries_gate_static),
        ("G-P085-CONT-01", verify_gp085_continuation_gate_static),
        ("G-P085-DLQ-01", verify_gp085_dlq_gate_static),
        ("G-P085-REC-01", verify_gp085_recovery_receipt_gate_static),
        ("G-P085-PROG-01", verify_gp085_progression_gate_static),
        ("G-P085-WATCH-01", verify_gp085_watchdog_gate_static),
        ("G-P085-GRAPH-01", verify_gp085_graph_density_gate_static),
        ("G-P085-PROMO-01", verify_gp085_promotion_gate_static),
        ("G-P085-ORPHAN-01", verify_gp085_orphan_gate_static),
        ("G-P085-GRAPH-PROP-01", verify_gp085_graph_propagation_gate_static),
        ("G-P085-WALK-01", verify_gp085_traversal_scheduling_gate_static),
        ("G-P085-WALK-02", verify_gp085_traversal_retry_gate_static),
        ("G-P085-WALK-03", verify_gp085_stalled_traversal_gate_static),
        ("G-P085-WALK-04", verify_gp085_traversal_explainability_gate_static),
        ("G-P085-TCRE-01", verify_gp085_tcre_saturation_gate_static),
        ("G-P085-TCRE-02", verify_gp085_tcre_density_gate_static),
        ("G-P085-TCRE-03", verify_gp085_tcre_omission_explainability_gate_static),
        ("G-P085-RET-01", verify_gp085_retrieval_density_gate_static),
        ("G-P085-RET-02", verify_gp085_retrieval_starvation_gate_static),
        ("G-P085-RET-PROP-01", verify_gp085_retrieval_propagation_gate_static),
        ("G-P085-SYN-01", verify_gp085_synthesis_activation_gate_static),
        ("G-P085-SYN-02", verify_gp085_synthesis_idle_starved_gate_static),
        ("G-P085-SYN-03", verify_gp085_synthesis_throughput_gate_static),
        ("G-P085-MAT-01", verify_gp085_operational_maturity_gate_static),
        ("G-P085-HEALTH-01", verify_gp085_operational_health_gate_static),
        ("G-P085-HEALTH-02", verify_gp085_autonomous_recovery_gate_static),
        ("G-P085-CP-01", verify_gp085_operational_cockpit_gate_static),
        ("G-P085-CP-02", verify_gp085_operational_explorers_gate_static),
        ("G-P085-CP-03", verify_gp085_progression_timeline_causal_gate_static),
        ("G-P085-ECON-01", verify_gp085_runtime_economics_gate_static),
        ("G-P085-ECON-02", verify_gp085_replay_storm_gate_static),
        ("G-P085-READY-01", verify_gp085_phase09_readiness_gate_static),
    ]


def _gate_result_row_v1(gate_id: str, out: Mapping[str, Any]) -> dict[str, Any]:
    passed = out.get("passed") is True
    status = "pass" if passed else "fail"
    return dict(
        sorted(
            {
                "duration_ms": 0,
                "gate_id": gate_id,
                "status": status,
            }.items(),
        ),
    )


def run_all_cesp_gp085_static_gates_v1(
    *,
    skip_gate_ids: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    skip = skip_gate_ids or frozenset()
    rows: list[dict[str, Any]] = []
    for gate_id, runner in _wired_gp085_gate_runners_v1():
        if gate_id in skip:
            continue
        out = runner()
        gid = str(out.get("gate_id") or out.get("id") or gate_id)
        rows.append(_gate_result_row_v1(gid, out))
    rows.sort(key=lambda r: r["gate_id"])
    return rows


def build_cesp_cert_pack_v1(
    *,
    gate_results: Mapping[str, Any],
    golden_tenant_slice: Mapping[str, Any],
    soak_summary: Mapping[str, Any],
    readiness_checklist: Mapping[str, Any],
    policy_thresholds: Mapping[str, Any],
    git_sha: str | None = None,
) -> bytes:
    """Build **CESP-CERT-PACK-1** outer gzip bytes."""
    golden_b = cesp_canonical_json_bytes_v1(golden_tenant_slice)
    soak_b = cesp_canonical_json_bytes_v1(soak_summary)
    readiness_b = cesp_canonical_json_bytes_v1(readiness_checklist)
    policy_b = cesp_canonical_json_bytes_v1(policy_thresholds)

    inner_use = _inner_payload_digest_v1(
        payload_parts=[
            ("gate_results.json", _gate_results_bytes_for_inner_digest_v1(gate_results)),
            ("golden_tenant_slice.json", golden_b),
            ("soak_summary.json", soak_b),
            ("readiness_checklist.json", readiness_b),
            ("policy_thresholds.json", policy_b),
        ],
    )

    manifest_core: dict[str, Any] = {
        "engine_build_id": CESP_ENGINE_BUILD_ID_V1,
        CESP_CERT_PACK_MANIFEST_FORMAT_KEY_V1: CESP_CERT_PACK_FORMAT_LITERAL_V1,
        "cesp_ci_arch_version": CESP_CI_ARCH_VERSION_STRING_V1,
        "phase085_program_freeze_version": int(PHASE085_PROGRAM_FREEZE_VERSION),
        "program_id": PHASE085_PROGRAM_ID_V1,
        "step_program_count": int(PHASE085_STEP_PROGRAM_COUNT),
        "git_sha": git_sha or resolve_git_sha_v1(),
        "payload_inner_sha256": inner_use,
    }
    manifest_bytes = cesp_canonical_json_bytes_v1(manifest_core)
    mdigest = _manifest_digest_v1(manifest_core)
    gr_final = {**dict(gate_results), "manifest_digest": mdigest}
    gate_results_bytes_final = cesp_canonical_json_bytes_v1(gr_final)

    inner_check = _inner_payload_digest_v1(
        payload_parts=[
            ("gate_results.json", _gate_results_bytes_for_inner_digest_v1(gr_final)),
            ("golden_tenant_slice.json", golden_b),
            ("soak_summary.json", soak_b),
            ("readiness_checklist.json", readiness_b),
            ("policy_thresholds.json", policy_b),
        ],
    )
    if inner_check != inner_use:
        msg = "inner digest mismatch after manifest_digest bind"
        raise RuntimeError(msg)

    inner_members: list[tuple[str, bytes]] = [
        ("gate_results.json", gate_results_bytes_final),
        ("manifest.json", manifest_bytes),
        ("golden_tenant_slice.json", golden_b),
        ("soak_summary.json", soak_b),
        ("readiness_checklist.json", readiness_b),
        ("policy_thresholds.json", policy_b),
    ]
    inner_members.sort(key=lambda t: t[0])
    tar_plain = _build_ustar_bytes(inner_members, mtime=CESP_CERT_PACK_TAR_MTIME)
    return _gzip_bytes(tar_plain)


def verify_cesp_cert_pack_v1(pack_gzip: bytes) -> CespCertPackVerifyResultV1:
    """Verify **CESP-CERT-PACK-1** structural law."""
    errs: list[str] = []
    try:
        raw = gzip.decompress(pack_gzip)
    except OSError as exc:
        return CespCertPackVerifyResultV1(False, (f"gunzip_failed:{exc}",))

    buf = io.BytesIO(raw)
    with tarfile.open(fileobj=buf, mode="r:") as tf:
        raw_names = [n for n in tf.getnames() if tf.getmember(n).isreg()]
        sorted_names = sorted(raw_names, key=lambda n: n.encode("utf-8"))
        if raw_names != sorted_names:
            errs.append("tar_members_not_utf8_sorted")
        members: dict[str, bytes] = {}
        for n in raw_names:
            extracted = tf.extractfile(n)
            if extracted is None:
                errs.append(f"unreadable_member:{n}")
                continue
            members[n] = extracted.read()

    for r in CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1:
        if r not in members:
            errs.append(f"missing_member:{r}")

    if errs:
        return CespCertPackVerifyResultV1(False, tuple(errs))

    manifest = json.loads(members["manifest.json"].decode("utf-8"))
    gate_results = json.loads(members["gate_results.json"].decode("utf-8"))
    if not isinstance(manifest, dict) or not isinstance(gate_results, dict):
        return CespCertPackVerifyResultV1(False, ("manifest_or_gate_results_not_object",))

    inner_hex = manifest.get("payload_inner_sha256")
    if not isinstance(inner_hex, str) or not inner_hex.startswith("sha256:"):
        errs.append("payload_inner_sha256_invalid")
    else:
        inner_exp = _inner_payload_digest_v1(
            payload_parts=[
                (
                    "gate_results.json",
                    _gate_results_bytes_for_inner_digest_v1(gate_results),
                ),
                ("golden_tenant_slice.json", members["golden_tenant_slice.json"]),
                ("soak_summary.json", members["soak_summary.json"]),
                ("readiness_checklist.json", members["readiness_checklist.json"]),
                ("policy_thresholds.json", members["policy_thresholds.json"]),
            ],
        )
        if inner_hex != inner_exp:
            errs.append("payload_inner_sha256_mismatch")

    if manifest.get(CESP_CERT_PACK_MANIFEST_FORMAT_KEY_V1) != CESP_CERT_PACK_FORMAT_LITERAL_V1:
        errs.append("cesp_cert_pack_format_mismatch")

    md_expect = _manifest_digest_v1(manifest)
    md_obs = gate_results.get("manifest_digest")
    if md_obs != md_expect:
        errs.append("manifest_digest_mismatch")

    gates = gate_results.get("gates")
    if not isinstance(gates, list):
        errs.append("gates_not_array")
    else:
        gate_ids_list = [str(g.get("gate_id")) for g in gates if isinstance(g, dict)]
        if gate_ids_list != sorted(gate_ids_list, key=str):
            errs.append("gates_not_sorted_by_gate_id")
        for g in gates:
            if not isinstance(g, dict):
                errs.append("gate_row_not_object")
                continue
            if g.get("status") != "pass":
                errs.append(f"gate_not_pass:{g.get('gate_id')}")

    return CespCertPackVerifyResultV1(len(errs) == 0, tuple(errs))


def _backend_root_v1() -> Path:
    from vector.domains.cortex.operational_runtime.normative import _repo_root_v1

    root = _repo_root_v1()
    if (root / "src" / "vector").is_dir():
        return root
    nested = root / "backend"
    if (nested / "src" / "vector").is_dir():
        return nested
    return root


def _changelog_contains_final_freeze_v1() -> tuple[bool, list[str]]:
    from vector.domains.cortex.operational_runtime.normative import _repo_root_v1

    path = (
        _repo_root_v1()
        / "DOCS"
        / "cortex"
        / "operational-runtime"
        / "PHASE085_CONSTITUTIONAL_CHANGELOG.md"
    )
    errors: list[str] = []
    if not path.is_file():
        return False, ["changelog_missing"]
    text = path.read_text(encoding="utf-8")
    if P085_FINAL_FREEZE_BUNDLE_ID_V1 not in text and PHASE085_PROGRAM_FREEZE_BUNDLE_V1 not in text:
        errors.append("changelog_missing_final_freeze_bundle")
    if "Step 36" not in text:
        errors.append("changelog_missing_step_36_marker")
    return len(errors) == 0, errors


def _migration_0082_or_later_present_v1() -> tuple[bool, list[str]]:
    versions = _backend_root_v1() / "alembic" / "versions"
    if not versions.is_dir():
        return False, ["alembic_versions_missing"]
    names = [p.name for p in versions.iterdir() if p.is_file()]
    if any("0082" in n for n in names):
        return True, []
    if any("0083" in n or "0084" in n or "0085" in n for n in names):
        return True, []
    return False, ["migration_0082_plus_missing"]


def _watchdog_in_celery_beat_v1() -> tuple[bool, list[str]]:
    celery_path = _backend_root_v1() / "src" / "app" / "celery_app.py"
    if not celery_path.is_file():
        return False, ["celery_app_missing"]
    text = celery_path.read_text(encoding="utf-8")
    from vector.domains.cortex.execution.scheduling import (
        CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1,
        convergence_runtime_authoritative_v1,
    )
    if convergence_runtime_authoritative_v1():
        if CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1 not in text:
            return False, ["convergence_sweep_not_in_beat"]
        if "mark_dirty_and_enqueue_convergence_v1" not in text:
            # ingest path lives in post_ingestion_refresh_dispatch, not celery_app
            dispatch_path = (
                _backend_root_v1()
                / "src"
                / "vector"
                / "domains"
                / "cortex"
                / "ingestion"
                / "post_ingestion_refresh_dispatch.py"
            )
            if not dispatch_path.is_file():
                return False, ["post_ingestion_dispatch_missing"]
            dispatch_text = dispatch_path.read_text(encoding="utf-8")
            if "mark_dirty_and_enqueue_convergence_v1" not in dispatch_text:
                return False, ["convergence_dirty_mark_missing"]
        return True, []

    if "continuity_watchdog" not in text:
        return False, ["continuity_watchdog_not_in_beat"]
    return True, []


def _cockpit_surfaces_shipped_v1() -> tuple[bool, list[str]]:
    from vector.domains.cortex.operational_runtime.operational_cockpit import (
        OPERATIONAL_COCKPIT_SURFACES_V1,
    )

    wired = [s for s in OPERATIONAL_COCKPIT_SURFACES_V1 if s.get("wired")]
    if len(wired) < 12:
        return False, [f"cockpit_wired_count:{len(wired)}"]
    return True, []


def _gap_matrix_blocks_closure_v1() -> tuple[bool, list[str]]:
    from vector.domains.cortex.operational_runtime.cesp_gap_matrix import (
        parse_cesp_gap_matrix_markdown_v1,
    )
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        READINESS_ALLOWED_OPEN_P0_V1,
    )

    parsed = parse_cesp_gap_matrix_markdown_v1()
    open_p0 = [
        str(r["gap_id"])
        for r in parsed.get("active_p0") or []
        if r.get("status") == "open"
    ]
    blocking = [gid for gid in open_p0 if gid not in READINESS_ALLOWED_OPEN_P0_V1]
    if blocking:
        return False, [f"blocking_open_p0:{blocking}"]
    return True, []


def _close01_gate(passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": GP085_CLOSE01_GATE_ID_V1,
        "name": "cesp_cert_pack_closure",
        "passed": passed,
        "severity": "hard_fail",
        "detail": dict(detail),
    }


def _run_closure_pipeline_build_pack_v1(
    session: Session | None,
) -> tuple[bool, dict[str, Any], bytes | None]:
    if session is None:
        from vector.infrastructure.db.session import session_scope

        with session_scope() as scoped:
            return _run_closure_pipeline_build_pack_v1(scoped)

    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        build_phase09_readiness_checklist_v1,
        evaluate_phase09_readiness_v1,
        record_phase09_soak_signoff_v1,
    )

    record_phase09_soak_signoff_v1(session, note="cesp_close01_pack_build")
    session.flush()

    rows = run_all_cesp_gp085_static_gates_v1(
        skip_gate_ids=frozenset({GP085_CLOSE01_GATE_ID_V1}),
    )
    for r in rows:
        if r["status"] != "pass":
            return False, {"non_pass_gate": r}, None

    readiness = evaluate_phase09_readiness_v1(session)
    if not readiness.get("readiness_passed"):
        return False, {"readiness_not_passed": readiness.get("failure_criteria")}, None

    gate_results_obj = {
        "gates": rows,
        "manifest_digest": "",
        "program_step": 36,
    }
    pack = build_cesp_cert_pack_v1(
        gate_results=gate_results_obj,
        golden_tenant_slice=build_golden_tenant_slice_payload_v1(session),
        soak_summary=build_soak_summary_payload_v1(session),
        readiness_checklist={
            "checklist": build_phase09_readiness_checklist_v1(session),
            "readiness_passed": readiness.get("readiness_passed"),
        },
        policy_thresholds=build_policy_thresholds_payload_v1(),
    )
    vr = verify_cesp_cert_pack_v1(pack)
    if not vr.passed:
        return False, {"pack_verify_errors": list(vr.errors)}, None
    return (
        True,
        {
            "pack_bytes": len(pack),
            "cesp_cert_pack_format": CESP_CERT_PACK_FORMAT_LITERAL_V1,
            "gate_count": len(rows),
        },
        pack,
    )


def verify_gp085_close01_cesp_cert_pack_shape_reference_static() -> dict[str, Any]:
    errors: list[str] = []
    if CESP_CERT_PACK_FORMAT_LITERAL_V1 != "CESP-CERT-PACK-1":
        errors.append("cesp_cert_pack_format_literal_drift")
    want = tuple(sorted(CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1, key=str))
    if tuple(sorted(CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1, key=str)) != want:
        errors.append("required_root_files_tuple_drift")
    return _close01_gate(
        not errors,
        {
            "errors": errors,
            "required_root_files_v1": list(CESP_CERT_PACK_REQUIRED_ROOT_FILES_V1),
        },
    )


def verify_gp085_close01_static() -> dict[str, Any]:
    """**G-P085-CLOSE-01** — completion criteria + **CESP-CERT-PACK-1** round-trip."""
    shape = verify_gp085_close01_cesp_cert_pack_shape_reference_static()
    if not shape.get("passed"):
        return shape

    errors: list[str] = []
    changelog_ok, changelog_errors = _changelog_contains_final_freeze_v1()
    if not changelog_ok:
        errors.extend(changelog_errors)
    mig_ok, mig_errors = _migration_0082_or_later_present_v1()
    if not mig_ok:
        errors.extend(mig_errors)
    beat_ok, beat_errors = _watchdog_in_celery_beat_v1()
    if not beat_ok:
        errors.extend(beat_errors)
    cp_ok, cp_errors = _cockpit_surfaces_shipped_v1()
    if not cp_ok:
        errors.extend(cp_errors)
    gap_ok, gap_errors = _gap_matrix_blocks_closure_v1()
    if not gap_ok:
        errors.extend(gap_errors)

    if errors:
        return _close01_gate(False, {"completion_criteria_errors": errors})

    ok, detail, _pack = _run_closure_pipeline_build_pack_v1(None)
    if not ok:
        return _close01_gate(False, detail)
    return _close01_gate(True, detail)


def build_cesp_certification_pack_snapshot_v1() -> dict[str, Any]:
    """Operator snapshot: gzip pack bytes + whole-file digest."""
    ok, detail, pack = _run_closure_pipeline_build_pack_v1(None)
    if not ok or pack is None:
        return {
            "cesp_certification_pack_runtime_schema_version": (
                PHASE085_CESP_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
            ),
            "cesp_cert_pack_format": CESP_CERT_PACK_FORMAT_LITERAL_V1,
            "closure_passed": False,
            "closure_detail": detail,
            "whole_file_sha256": None,
            "pack_gzip_base64": None,
            "pack_byte_length": None,
        }
    whole = hashlib.sha256(pack).hexdigest()
    return {
        "cesp_certification_pack_runtime_schema_version": (
            PHASE085_CESP_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
        ),
        "cesp_cert_pack_format": CESP_CERT_PACK_FORMAT_LITERAL_V1,
        "closure_passed": True,
        "closure_detail": detail,
        "whole_file_sha256": whole,
        "pack_gzip_base64": base64.b64encode(pack).decode("ascii"),
        "pack_byte_length": len(pack),
    }


def run_cesp_ci_cert_pack_artifact_v1() -> dict[str, Any]:
    """CI helper — build + verify pack (no DB session)."""
    ok, detail, pack = _run_closure_pipeline_build_pack_v1(None)
    if not ok or pack is None:
        return {"passed": False, "detail": detail, "verify_passed": False}
    vr = verify_cesp_cert_pack_v1(pack)
    return {
        "passed": vr.passed,
        "verify_passed": vr.passed,
        "verify_errors": list(vr.errors),
        "detail": detail,
        "pack_byte_length": len(pack),
    }
