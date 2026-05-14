"""Phase 05 Step **26** — OCTS certification pack (**OCTS-CERT-PACK-1**) + **G-P05-CLOSE-01**.

Normative: ``DOCS/cortex/05-traversal/phase-05-certification-pack-format.md``,
``DOCS/cortex/05-traversal/phase-05-closure-gates-doctrine.md``.

**FS-CG-02:** authoritative vector paths only (no exploration walk bytes under authoritative
``replay_samples/`` tree — this CI fixture uses ``vectors/*.json`` only).
"""

from __future__ import annotations

import calendar
import gzip
import hashlib
import io
import json
import tarfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping, cast

from vector.domains.cortex.traversal.normative import PHASE05_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.traversal.verification_gates_catalog import octs_golden_vectors_v1_root
from vector.domains.cortex.traversal.walk_api_contract import OCTS_STUB_ENGINE_BUILD_ID

OCTS_CERT_PACK_FORMAT_LITERAL: Final[str] = "OCTS-CERT-PACK-1"
OCTS_CI_ARCH_VERSION_STRING: Final[str] = "phase-05-ci-enforcement-architecture.md#normative-v1"
OCTS_CERT_PACK_RUNTIME_SCHEMA_VERSION: Final[int] = 1

OCTS_CERT_PACK_TAR_MTIME: Final[int] = calendar.timegm((1980, 1, 1, 0, 0, 0, 0, 0, 0))


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "05-traversal" / "schemas").is_dir():
            return root
    msg = "could not locate DOCS/cortex/05-traversal/schemas from certification_pack"
    raise RuntimeError(msg)


def compute_octs_schema_bundle_hash_v1() -> str:
    r"""Deterministic digest over sorted ``*.schema.json`` under ``05-traversal/schemas/``."""
    root = _repo_root_with_octs_docs() / "DOCS" / "cortex" / "05-traversal" / "schemas"
    entries: list[dict[str, str]] = []
    for p in sorted(root.rglob("*.schema.json"), key=lambda x: str(x).lower()):
        rel = p.relative_to(root).as_posix()
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        entries.append({"path": rel, "sha256": f"sha256:{h}"})
    body = {"entries": entries}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _octs_canonical_json_obj_v1(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _octs_canonical_json_obj_v1(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_octs_canonical_json_obj_v1(x) for x in obj]
    return obj


def octs_canonical_json_bytes_v1(obj: Any) -> bytes:
    """Canonical UTF-8 JSON bytes (**OCTS-CANON-1** style: sorted keys, NFC strings)."""
    canon = _octs_canonical_json_obj_v1(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _manifest_digest_v1(manifest: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(octs_canonical_json_bytes_v1(dict(manifest))).hexdigest()


def _inner_payload_digest_v1(
    *,
    gate_results_bytes: bytes,
    vectors_manifest_b: bytes,
    vec_parts: list[tuple[str, bytes]],
) -> str:
    """SHA-256 of ``gate_results`` bytes + ``vectors/manifest`` bytes + vector bodies (UTF-8 path order).

    ``gate_results_bytes`` must be the **OCTS-CANON-1** encoding of the gate-results object **without**
    ``manifest_digest`` (that field is derived from ``manifest.json`` including this digest — excluding
    it avoids a non-converging fixed point).
    """
    parts: list[bytes] = [gate_results_bytes, vectors_manifest_b]
    for _, blob in sorted(vec_parts, key=lambda t: t[0].encode("utf-8")):
        parts.append(blob)
    return "sha256:" + hashlib.sha256(b"".join(parts)).hexdigest()


def _octs_gate_results_bytes_for_inner_digest_v1(gate_results: Mapping[str, Any]) -> bytes:
    pruned = {k: v for k, v in dict(gate_results).items() if k != "manifest_digest"}
    return octs_canonical_json_bytes_v1(pruned)


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
    """Members sorted by ``arcname`` ascending UTF-8 (caller must pre-sort)."""
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
class OctsCertPackVerifyResultV1:
    passed: bool
    errors: tuple[str, ...]


def build_oct_cert_pack_v1(
    *,
    gate_results: Mapping[str, Any],
    vector_files: Mapping[str, bytes],
) -> bytes:
    """Build **OCTS-CERT-PACK-1** outer gzip bytes from pre-built ``gate_results`` + vector map.

    ``vector_files`` keys are tar paths under ``vectors/`` (e.g. ``vectors/walk_request_minimal_v1.json``).
    """
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
            }
        )
        vec_members.append((rel, data))

    vectors_manifest_obj = {"vectors": vec_manifest_rows}
    vectors_manifest_bytes = octs_canonical_json_bytes_v1(vectors_manifest_obj)

    vec_parts = list(vec_members)

    schema_hash = compute_octs_schema_bundle_hash_v1()
    manifest_core: dict[str, Any] = {
        "engine_build_id": OCTS_STUB_ENGINE_BUILD_ID,
        "octs_cert_pack_format": OCTS_CERT_PACK_FORMAT_LITERAL,
        "octs_ci_arch_version": OCTS_CI_ARCH_VERSION_STRING,
        "octs_program_freeze_version": PHASE05_PROGRAM_FREEZE_VERSION,
        "octs_schema_bundle_hash": schema_hash,
        "vector_bundle_version": "v1",
    }

    # ``payload_inner_sha256`` (format §4) — SHA-256 of canonical **gate_results** (excluding
    # ``manifest_digest``, which is bound from ``manifest.json`` and would create a digest cycle)
    # + ``vectors/manifest.json`` + vector bodies in sorted UTF-8 path order.
    inner_use = _inner_payload_digest_v1(
        gate_results_bytes=_octs_gate_results_bytes_for_inner_digest_v1(gate_results),
        vectors_manifest_b=vectors_manifest_bytes,
        vec_parts=vec_parts,
    )
    manifest = dict(sorted({**manifest_core, "payload_inner_sha256": inner_use}.items()))
    manifest_bytes = octs_canonical_json_bytes_v1(manifest)
    mdigest = _manifest_digest_v1(manifest)
    gr_final = {**dict(gate_results), "manifest_digest": mdigest}
    gate_results_bytes_final = octs_canonical_json_bytes_v1(gr_final)
    inner_check = _inner_payload_digest_v1(
        gate_results_bytes=_octs_gate_results_bytes_for_inner_digest_v1(gr_final),
        vectors_manifest_b=vectors_manifest_bytes,
        vec_parts=vec_parts,
    )
    if inner_check != inner_use:
        msg = "inner digest mismatch after manifest_digest bind"
        raise RuntimeError(msg)

    inner_members: list[tuple[str, bytes]] = [
        ("gate_results.json", gate_results_bytes_final),
        ("manifest.json", manifest_bytes),
        ("vectors/manifest.json", vectors_manifest_bytes),
    ]
    inner_members.extend(vec_members)
    inner_members.sort(key=lambda t: t[0])
    tar_plain = _build_ustar_bytes(inner_members, mtime=OCTS_CERT_PACK_TAR_MTIME)
    return _gzip_bytes(tar_plain)


def verify_oct_cert_pack_v1(pack_gzip: bytes) -> OctsCertPackVerifyResultV1:
    """Verify **OCTS-CERT-PACK-1** per ``phase-05-certification-pack-format.md`` §11."""
    errs: list[str] = []
    try:
        raw = gzip.decompress(pack_gzip)
    except OSError as exc:
        return OctsCertPackVerifyResultV1(False, (f"gunzip_failed:{exc}",))

    buf = io.BytesIO(raw)
    with tarfile.open(fileobj=buf, mode="r:") as tf:
        raw_names = [n for n in tf.getnames() if tf.getmember(n).isreg()]
        sorted_names = sorted(raw_names, key=lambda n: n.encode("utf-8"))
        if raw_names != sorted_names:
            errs.append("tar_members_not_utf8_sorted")
        members = {n: tf.extractfile(n).read() for n in raw_names}
    required = ("manifest.json", "gate_results.json", "vectors/manifest.json")
    for r in required:
        if r not in members:
            errs.append(f"missing_member:{r}")

    if errs:
        return OctsCertPackVerifyResultV1(False, tuple(errs))

    manifest = json.loads(members["manifest.json"].decode("utf-8"))
    gate_results = json.loads(members["gate_results.json"].decode("utf-8"))
    if not isinstance(manifest, dict) or not isinstance(gate_results, dict):
        return OctsCertPackVerifyResultV1(False, ("manifest_or_gate_results_not_object",))

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
            gate_results_bytes=_octs_gate_results_bytes_for_inner_digest_v1(gate_results),
            vectors_manifest_b=members["vectors/manifest.json"],
            vec_parts=vec_parts_inner,
        )
        if inner_hex != inner_exp:
            errs.append("payload_inner_sha256_mismatch")

    if manifest.get("octs_cert_pack_format") != OCTS_CERT_PACK_FORMAT_LITERAL:
        errs.append("octs_cert_pack_format_mismatch")

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

    return OctsCertPackVerifyResultV1(len(errs) == 0, tuple(errs))


def default_oct_cert_pack_vector_files_v1() -> dict[str, bytes]:
    root = octs_golden_vectors_v1_root()
    p = root / "walks" / "walk_request_minimal_v1.json"
    data = p.read_bytes()
    return {"vectors/walk_request_minimal_v1.json": data}


def verify_gp05_close01_oct_cert_pack_static() -> dict[str, Any]:
    """**G-P05-CLOSE-01** — PR **A–D** + **E** + **Z** (except self) green; **OCTS-CERT-PACK-1** round-trip."""
    from vector.domains.cortex.traversal.verification_gates_catalog import (
        default_severity_for_gate_v1,
        run_octs_pr_blocking_static_stages_v1,
        run_octs_wired_verification_stages_v1,
    )

    pr = run_octs_pr_blocking_static_stages_v1()
    if not pr.get("passed"):
        return _close01_gate(False, {"pr_blocking": pr})

    e_body = run_octs_wired_verification_stages_v1(("E",))
    if not e_body.get("passed"):
        return _close01_gate(False, {"stage_e": e_body})

    z_body = run_octs_wired_verification_stages_v1(
        ("Z",),
        skip_gate_ids=frozenset({"G-P05-CLOSE-01"}),
    )
    if not z_body.get("passed"):
        return _close01_gate(False, {"stage_z_preclose": z_body})

    rows: list[dict[str, Any]] = []
    for block in (pr, e_body, z_body):
        for item in block.get("results", []) or []:
            gid = str(item.get("gate_id") or "")
            res = item.get("result") or {}
            passed = res.get("passed") is True
            sev = str(res.get("severity") or default_severity_for_gate_v1(gid))
            status = "pass" if passed else ("skipped" if sev == "warn" else "fail")
            rows.append(
                dict(
                    sorted(
                        {
                            "duration_ms": 0,
                            "gate_id": gid,
                            "status": status,
                        }.items()
                    )
                )
            )

    rows.sort(key=lambda r: r["gate_id"])
    for r in rows:
        if r["status"] != "pass":
            return _close01_gate(
                False,
                {
                    "non_pass_gate": r,
                    "pr_results_len": len(pr.get("results", [])),
                },
            )

    gate_results_obj = {
        "gates": rows,
        "manifest_digest": "",
        "stages_completed": ["A", "B", "C", "D", "E", "Z"],
    }
    pack = build_oct_cert_pack_v1(
        gate_results=gate_results_obj,
        vector_files=default_oct_cert_pack_vector_files_v1(),
    )
    vr = verify_oct_cert_pack_v1(pack)
    if not vr.passed:
        return _close01_gate(False, {"pack_verify_errors": list(vr.errors), "pack_bytes": len(pack)})

    return _close01_gate(True, {"pack_bytes": len(pack), "octs_cert_pack_format": OCTS_CERT_PACK_FORMAT_LITERAL})


def _close01_gate(passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.traversal.verification_gates_catalog import default_severity_for_gate_v1

    return {
        "id": "G-P05-CLOSE-01",
        "name": "octs_cert_pack_closure",
        "passed": passed,
        "severity": default_severity_for_gate_v1("G-P05-CLOSE-01"),
        "detail": dict(detail),
    }
