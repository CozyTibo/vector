"""Phase 08 P08-30 — **SYNTHESIS-CERT-PACK-1** + **G-P08-CLOSE-01** (closure gate).

Normative: ``DOCS/cortex/synthesis/phase-08-closure-gates-doctrine.md``,
``DOCS/cortex/synthesis/phase-08-testing-strategy.md`` (**G-P08-CLOSE-01**).
"""

from __future__ import annotations

import base64
import calendar
import gzip
import hashlib
import io
import json
import tarfile
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.normative import PHASE08_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    hash_synthesis_corpus_manifest_digest_v1,
    load_synthesis_corpus_manifest_v1,
    synthesis_golden_vectors_v1_root,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.infrastructure.db.models.cortex_synthesis_certification_archive import (
    CortexSynthesisCertificationArchive,
)

PHASE08_SYNTHESIS_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1: Final[str] = "SYNTHESIS-CERT-PACK-1"

SYNTHESIS_CERT_PACK_MANIFEST_FORMAT_KEY_V1: Final[str] = "synthesis_cert_pack_format"

SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1: Final[tuple[str, ...]] = (
    "manifest.json",
    "gate_results.json",
    "vectors/manifest.json",
    "legality_matrix.json",
    "policy_pack.sha256",
)

SYNTHESIS_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack",
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack/archive",
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack/archives",
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack/archives/{archive_id}",
    "/admin/tenants/{tenant_id}/cortex/synthesis/program-closure",
)

SYNTHESIS_ENGINE_BUILD_ID_V1: Final[str] = "synthesis.engine.stub.v1"

SYNTHESIS_CI_ARCH_VERSION_STRING_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-testing-strategy.md#staging-v1"
)

SYNTHESIS_CERT_PACK_TAR_MTIME: Final[int] = calendar.timegm((1980, 1, 1, 0, 0, 0, 0, 0, 0))

SYNTHESIS_CERTIFICATION_PACK_SCHEMA_VERSION: Final[int] = 1


def synthesis_policy_pack_fixture_path_v1() -> Path:
    from vector.domains.cortex.synthesis.synthesis_job_contract import (
        DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    )
    from vector.domains.cortex.synthesis.synthesis_query_plan import (
        synthesis_policy_pack_fixture_path_v1 as resolve_policy_pack_fixture_v1,
    )

    path = resolve_policy_pack_fixture_v1(policy_pack_id=DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1)
    if path is None:
        msg = f"synthesis policy pack fixture not found: {DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1}"
        raise FileNotFoundError(msg)
    return path


def _synthesis_canonical_json_obj_v1(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _synthesis_canonical_json_obj_v1(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_synthesis_canonical_json_obj_v1(x) for x in obj]
    return obj


def synthesis_canonical_json_bytes_v1(obj: Any) -> bytes:
    canon = _synthesis_canonical_json_obj_v1(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_synthesis_vectors_bundle_hash_v1() -> str:
    manifest = load_synthesis_corpus_manifest_v1()
    return hash_synthesis_corpus_manifest_digest_v1(manifest)


def _manifest_digest_v1(manifest: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(synthesis_canonical_json_bytes_v1(dict(manifest))).hexdigest()


def _gate_results_bytes_for_inner_digest_v1(gate_results: Mapping[str, Any]) -> bytes:
    pruned = {k: v for k, v in dict(gate_results).items() if k != "manifest_digest"}
    return synthesis_canonical_json_bytes_v1(pruned)


def _inner_payload_digest_v1(
    *,
    gate_results_bytes: bytes,
    vectors_manifest_b: bytes,
    legality_matrix_b: bytes,
    policy_pack_sha_b: bytes,
    vec_parts: list[tuple[str, bytes]],
) -> str:
    parts: list[bytes] = [
        gate_results_bytes,
        vectors_manifest_b,
        legality_matrix_b,
        policy_pack_sha_b,
    ]
    for _, blob in sorted(vec_parts, key=lambda t: t[0].encode("utf-8")):
        parts.append(blob)
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


@dataclass(frozen=True, slots=True)
class SynthesisCertPackVerifyResultV1:
    passed: bool
    errors: tuple[str, ...]


def default_synthesis_cert_pack_legality_matrix_bytes_v1() -> bytes:
    from vector.domains.cortex.synthesis.synthesis_runtime_legality_matrix import (
        build_synthesis_runtime_legality_matrix_catalog_v1,
    )

    doc = build_synthesis_runtime_legality_matrix_catalog_v1(
        None,
        tenant_id=uuid.UUID(int=0),
    )
    return synthesis_canonical_json_bytes_v1(doc)


def default_synthesis_cert_pack_policy_pack_sha_bytes_v1() -> bytes:
    from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
        hash_synthesis_policy_pack_fixture_file_v1,
    )

    digest = hash_synthesis_policy_pack_fixture_file_v1()
    if not digest.startswith("sha256:"):
        digest = f"sha256:{digest}"
    return digest.encode("utf-8")


def default_synthesis_cert_pack_vector_files_v1() -> dict[str, bytes]:
    root = synthesis_golden_vectors_v1_root()
    out: dict[str, bytes] = {}
    for rel in (
        "corpus_manifest.json",
        "tenant_verification/org_graph_synthesis_slice_good_v1.json",
    ):
        p = root / rel
        if p.is_file():
            out[f"vectors/{rel}"] = p.read_bytes()
    for case_path in sorted(root.glob("cases/*/case.json"), key=lambda p: str(p).lower()):
        rel = case_path.relative_to(root).as_posix()
        out[f"vectors/{rel}"] = case_path.read_bytes()
    return out


def build_synthesis_cert_pack_v1(
    *,
    gate_results: Mapping[str, Any],
    vector_files: Mapping[str, bytes],
    legality_matrix_bytes: bytes | None = None,
    policy_pack_sha256_bytes: bytes | None = None,
) -> bytes:
    """Build **SYNTHESIS-CERT-PACK-1** outer gzip bytes."""
    legality_b = legality_matrix_bytes or default_synthesis_cert_pack_legality_matrix_bytes_v1()
    policy_b = policy_pack_sha256_bytes or default_synthesis_cert_pack_policy_pack_sha_bytes_v1()

    vec_manifest_rows: list[dict[str, str]] = []
    vec_members: list[tuple[str, bytes]] = []
    for rel in sorted(vector_files.keys(), key=str):
        data = vector_files[rel]
        h = hashlib.sha256(data).hexdigest()
        vec_manifest_rows.append(
            {
                "fixture_version": "v1",
                "path": rel,
                "sha256": f"sha256:{h}",
            },
        )
        vec_members.append((rel, data))

    vectors_manifest_obj = {"vectors": vec_manifest_rows}
    vectors_manifest_bytes = synthesis_canonical_json_bytes_v1(vectors_manifest_obj)

    bundle_hash = compute_synthesis_vectors_bundle_hash_v1()
    policy_digest = synthesis_policy_pack_digest_v1()
    manifest_core: dict[str, Any] = {
        "engine_build_id": SYNTHESIS_ENGINE_BUILD_ID_V1,
        SYNTHESIS_CERT_PACK_MANIFEST_FORMAT_KEY_V1: SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
        "synthesis_ci_arch_version": SYNTHESIS_CI_ARCH_VERSION_STRING_V1,
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "synthesis_policy_digest": policy_digest,
        "synthesis_vectors_bundle_hash": bundle_hash,
        "vector_bundle_version": "v1",
    }

    inner_use = _inner_payload_digest_v1(
        gate_results_bytes=_gate_results_bytes_for_inner_digest_v1(gate_results),
        vectors_manifest_b=vectors_manifest_bytes,
        legality_matrix_b=legality_b,
        policy_pack_sha_b=policy_b,
        vec_parts=vec_members,
    )
    manifest = dict(sorted({**manifest_core, "payload_inner_sha256": inner_use}.items()))
    manifest_bytes = synthesis_canonical_json_bytes_v1(manifest)
    mdigest = _manifest_digest_v1(manifest)
    gr_final = {**dict(gate_results), "manifest_digest": mdigest}
    gate_results_bytes_final = synthesis_canonical_json_bytes_v1(gr_final)
    inner_check = _inner_payload_digest_v1(
        gate_results_bytes=_gate_results_bytes_for_inner_digest_v1(gr_final),
        vectors_manifest_b=vectors_manifest_bytes,
        legality_matrix_b=legality_b,
        policy_pack_sha_b=policy_b,
        vec_parts=vec_members,
    )
    if inner_check != inner_use:
        msg = "inner digest mismatch after manifest_digest bind"
        raise RuntimeError(msg)

    inner_members: list[tuple[str, bytes]] = [
        ("gate_results.json", gate_results_bytes_final),
        ("manifest.json", manifest_bytes),
        ("vectors/manifest.json", vectors_manifest_bytes),
        ("legality_matrix.json", legality_b),
        ("policy_pack.sha256", policy_b),
    ]
    inner_members.extend(vec_members)
    inner_members.sort(key=lambda t: t[0])
    tar_plain = _build_ustar_bytes(inner_members, mtime=SYNTHESIS_CERT_PACK_TAR_MTIME)
    return _gzip_bytes(tar_plain)


def verify_synthesis_cert_pack_v1(pack_gzip: bytes) -> SynthesisCertPackVerifyResultV1:
    """Verify **SYNTHESIS-CERT-PACK-1** structural law."""
    errs: list[str] = []
    try:
        raw = gzip.decompress(pack_gzip)
    except OSError as exc:
        return SynthesisCertPackVerifyResultV1(False, (f"gunzip_failed:{exc}",))

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

    for r in SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1:
        if r not in members:
            errs.append(f"missing_member:{r}")

    if errs:
        return SynthesisCertPackVerifyResultV1(False, tuple(errs))

    manifest = json.loads(members["manifest.json"].decode("utf-8"))
    gate_results = json.loads(members["gate_results.json"].decode("utf-8"))
    if not isinstance(manifest, dict) or not isinstance(gate_results, dict):
        return SynthesisCertPackVerifyResultV1(False, ("manifest_or_gate_results_not_object",))

    vm_doc = json.loads(members["vectors/manifest.json"].decode("utf-8"))
    vm = vm_doc.get("vectors") if isinstance(vm_doc, dict) else None

    inner_hex = manifest.get("payload_inner_sha256")
    if not isinstance(inner_hex, str) or not inner_hex.startswith("sha256:"):
        errs.append("payload_inner_sha256_invalid")
    else:
        vec_parts_inner: list[tuple[str, bytes]] = []
        if isinstance(vm, list):
            for row in vm:
                if isinstance(row, dict) and isinstance(row.get("path"), str):
                    p = row["path"]
                    if p in members:
                        vec_parts_inner.append((p, members[p]))
        inner_exp = _inner_payload_digest_v1(
            gate_results_bytes=_gate_results_bytes_for_inner_digest_v1(gate_results),
            vectors_manifest_b=members["vectors/manifest.json"],
            legality_matrix_b=members["legality_matrix.json"],
            policy_pack_sha_b=members["policy_pack.sha256"],
            vec_parts=vec_parts_inner,
        )
        if inner_hex != inner_exp:
            errs.append("payload_inner_sha256_mismatch")

    if manifest.get(SYNTHESIS_CERT_PACK_MANIFEST_FORMAT_KEY_V1) != SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1:
        errs.append("synthesis_cert_pack_format_mismatch")

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

    if not isinstance(vm, list):
        errs.append("vectors_manifest_vectors_not_array")
    else:
        for row in vm:
            if not isinstance(row, dict):
                errs.append("vector_manifest_row_not_object")
                continue
            p = row.get("path")
            exp = row.get("sha256")
            if not isinstance(p, str) or not isinstance(exp, str):
                errs.append("vector_manifest_bad_shape")
                continue
            if p not in members:
                errs.append(f"vector_missing:{p}")
                continue
            got = "sha256:" + hashlib.sha256(members[p]).hexdigest()
            if got != exp:
                errs.append(f"vector_hash_mismatch:{p}")

    policy_sha = members.get("policy_pack.sha256", b"").decode("utf-8").strip()
    if not policy_sha.startswith("sha256:") or len(policy_sha) < 71:
        errs.append("policy_pack_sha256_invalid")

    from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
        hash_synthesis_policy_pack_fixture_file_v1,
    )

    fixture_hex = hash_synthesis_policy_pack_fixture_file_v1()
    fixture_prefixed = fixture_hex if fixture_hex.startswith("sha256:") else f"sha256:{fixture_hex}"
    if policy_sha != fixture_prefixed:
        errs.append("policy_pack_sha256_mismatch_fixture")

    return SynthesisCertPackVerifyResultV1(len(errs) == 0, tuple(errs))


def _close01_gate(passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_verification_harness import (
        default_severity_for_synthesis_gate_v1,
    )

    return {
        "id": "G-P08-CLOSE-01",
        "name": "synthesis_cert_pack_closure",
        "passed": passed,
        "severity": default_severity_for_synthesis_gate_v1("G-P08-CLOSE-01"),
        "detail": dict(detail),
    }


def _gate_result_row_v1(gate_id: str, out: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_verification_harness import (
        default_severity_for_synthesis_gate_v1,
    )

    passed = out.get("passed") is True
    sev = str(out.get("severity") or default_severity_for_synthesis_gate_v1(gate_id))
    status = "pass" if passed else ("skipped" if sev == "warn" else "fail")
    return dict(
        sorted(
            {
                "duration_ms": 0,
                "gate_id": gate_id,
                "status": status,
            }.items(),
        ),
    )


def _gate_rows_from_pr_blocking_v1(pr: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage_key in ("stage_a", "stage_b", "stage_c"):
        for item in pr.get(stage_key, []) or []:
            if not isinstance(item, dict):
                continue
            gid = str(item.get("id") or item.get("gate_id") or "")
            if gid:
                rows.append(_gate_result_row_v1(gid, item))
    return rows


def _gate_rows_from_wired_body_v1(body: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in body.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        gid = str(item.get("gate_id") or "")
        res = item.get("result") or {}
        if isinstance(res, dict) and gid:
            rows.append(_gate_result_row_v1(gid, res))
    return rows


def _run_closure_pipeline_build_pack_v1() -> tuple[bool, dict[str, Any], bytes | None]:
    """PR **A–C** + stages **D, E, Z** (skip **G-P08-CLOSE-01**), build + verify pack."""
    from vector.domains.cortex.synthesis.synthesis_verification_harness import (
        run_synthesis_gp08_pr_blocking_static_stages_v1,
        run_synthesis_gp08_wired_verification_stages_v1,
    )

    pr = run_synthesis_gp08_pr_blocking_static_stages_v1(record_ledger=False)
    if not pr.get("passed"):
        return False, {"pr_blocking": pr}, None

    extra = run_synthesis_gp08_wired_verification_stages_v1(
        ("D", "E", "Z"),
        skip_gate_ids=frozenset({"G-P08-CLOSE-01"}),
        abort_on_hard_fail=False,
        record_ledger=False,
    )
    if not extra.get("passed"):
        return False, {"stages_d_e_z": extra}, None

    rows = _gate_rows_from_pr_blocking_v1(pr) + _gate_rows_from_wired_body_v1(extra)
    rows.sort(key=lambda r: r["gate_id"])
    for r in rows:
        if r["status"] != "pass":
            return False, {"non_pass_gate": r}, None

    gate_results_obj = {
        "gates": rows,
        "manifest_digest": "",
        "stages_completed": ["A", "B", "C", "D", "E", "Z"],
    }
    pack = build_synthesis_cert_pack_v1(
        gate_results=gate_results_obj,
        vector_files=default_synthesis_cert_pack_vector_files_v1(),
    )
    vr = verify_synthesis_cert_pack_v1(pack)
    if not vr.passed:
        return False, {"pack_verify_errors": list(vr.errors), "pack_bytes": len(pack)}, None
    return (
        True,
        {
            "pack_bytes": len(pack),
            "synthesis_cert_pack_format": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
            "synthesis_cert_pack_format_literal_v1": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
            "vector_file_count": len(default_synthesis_cert_pack_vector_files_v1()),
        },
        pack,
    )


def verify_gp08_close01_synthesis_cert_pack_shape_reference_static() -> dict[str, Any]:
    """**G-P08-CLOSE-01** (shape) — **SYNTHESIS-CERT-PACK-1** literals + five root files."""
    from vector.domains.cortex.synthesis.synthesis_verification_harness import (
        SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
    )

    errors: list[str] = []
    if SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1 != "SYNTHESIS-CERT-PACK-1":
        errors.append("synthesis_cert_pack_format_literal_drift")
    want_files = (
        "manifest.json",
        "gate_results.json",
        "vectors/manifest.json",
        "legality_matrix.json",
        "policy_pack.sha256",
    )
    if tuple(sorted(SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1, key=str)) != tuple(
        sorted(want_files, key=str),
    ):
        errors.append("required_root_files_tuple_drift")
    if not synthesis_policy_pack_fixture_path_v1().is_file():
        errors.append("missing_policy_pack_fixture")
    return {
        "id": "G-P08-CLOSE-01",
        "name": "synthesis_cert_pack_shape_reference",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "synthesis_cert_pack_format_literal_v1": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
            "required_root_files_v1": list(SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1),
            "synthesis_verification_harness_catalog_version": (
                SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1
            ),
        },
    }


def verify_gp08_close01_synthesis_cert_pack_closure_static() -> dict[str, Any]:
    """**G-P08-CLOSE-01** — wired gates green + **SYNTHESIS-CERT-PACK-1** round-trip."""
    shape = verify_gp08_close01_synthesis_cert_pack_shape_reference_static()
    if not shape.get("passed"):
        return shape
    ok, detail, _pack = _run_closure_pipeline_build_pack_v1()
    if not ok:
        return _close01_gate(False, detail)
    return _close01_gate(True, detail)


def verify_gp08_scpk01_synthesis_cert_pack_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want_prefixes = (
        "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack",
        "/admin/tenants/{tenant_id}/cortex/synthesis/program-closure",
    )
    for prefix in want_prefixes:
        if not any(p.startswith(prefix) for p in SYNTHESIS_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1):
            errors.append(f"missing_admin_path_prefix:{prefix}")
    return {
        "id": "P08-30-scpk-paths",
        "name": "synthesis_certification_pack_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def build_synthesis_certification_pack_snapshot_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Operator snapshot: gzip pack bytes + whole-file digest (read-only)."""
    ok, detail, pack = _run_closure_pipeline_build_pack_v1()
    tid = "" if tenant_id is None else str(tenant_id)
    if not ok or pack is None:
        return {
            "tenant_id": tid,
            "synthesis_certification_pack_runtime_schema_version": (
                PHASE08_SYNTHESIS_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
            ),
            "synthesis_cert_pack_format": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
            "closure_passed": False,
            "closure_detail": detail,
            "whole_file_sha256": None,
            "pack_gzip_base64": None,
            "pack_byte_length": None,
        }
    whole = hashlib.sha256(pack).hexdigest()
    return {
        "tenant_id": tid,
        "synthesis_certification_pack_runtime_schema_version": (
            PHASE08_SYNTHESIS_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION
        ),
        "synthesis_cert_pack_format": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
        "closure_passed": True,
        "closure_detail": {"note": "operator_export_matches_closure_pipeline"},
        "whole_file_sha256": f"sha256:{whole}",
        "pack_gzip_base64": base64.b64encode(pack).decode("ascii"),
        "pack_byte_length": len(pack),
    }


def run_synthesis_gp08_ci_cert_pack_artifact_v1() -> dict[str, Any]:
    """CI entry: build + verify **SYNTHESIS-CERT-PACK-1** (doctrine criterion 8 / CLOSE-01)."""
    ok, detail, pack = _run_closure_pipeline_build_pack_v1()
    verify_passed = False
    if pack is not None:
        verify_passed = verify_synthesis_cert_pack_v1(pack).passed
    return {
        "passed": bool(ok and verify_passed),
        "synthesis_cert_pack_format": SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
        "pack_bytes": len(pack) if pack else 0,
        "build_detail": detail,
        "verify_passed": verify_passed,
    }


def persist_synthesis_certification_archive_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Persist certification archive when program closure passes."""
    from vector.domains.cortex.synthesis.synthesis_program_closure import (
        build_synthesis_program_closure_snapshot_v1,
    )

    snapshot = build_synthesis_program_closure_snapshot_v1(session, tenant_id=tenant_id)
    passed = bool(snapshot.get("program_closure_passed"))
    if not passed:
        return {
            "persisted": False,
            "passed": False,
            "archive_id": None,
            "snapshot": snapshot,
        }
    row = CortexSynthesisCertificationArchive(
        tenant_id=tenant_id,
        synthesis_certification_pack_schema_version=SYNTHESIS_CERTIFICATION_PACK_SCHEMA_VERSION,
        passed=True,
        pack_json=snapshot,
    )
    session.add(row)
    session.flush()
    return {
        "persisted": True,
        "passed": True,
        "archive_id": row.id,
        "snapshot": snapshot,
    }


def synthesis_certification_archive_public_dict_v1(
    row: CortexSynthesisCertificationArchive,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "synthesis_certification_pack_schema_version": row.synthesis_certification_pack_schema_version,
        "passed": row.passed,
        "created_at": row.created_at,
    }


def list_synthesis_certification_archives_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> list[CortexSynthesisCertificationArchive]:
    lim = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(CortexSynthesisCertificationArchive)
            .where(CortexSynthesisCertificationArchive.tenant_id == tenant_id)
            .order_by(
                CortexSynthesisCertificationArchive.created_at.desc(),
                CortexSynthesisCertificationArchive.id.desc(),
            )
            .limit(lim),
        ).all(),
    )


def get_synthesis_certification_archive_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    archive_id: int,
) -> CortexSynthesisCertificationArchive | None:
    return session.scalars(
        select(CortexSynthesisCertificationArchive).where(
            CortexSynthesisCertificationArchive.tenant_id == tenant_id,
            CortexSynthesisCertificationArchive.id == archive_id,
        ),
    ).first()
