#!/usr/bin/env python3
"""Write ingestion, substrate, canon, and identity ECS worker task defs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_ROLES_MODULE_PATH = (
    REPO_ROOT
    / "backend/src/vector/domains/cortex/ingestion/worker_queue_roles_v1.py"
)


def _load_roles_module():
    """Load queue role helpers without importing ``vector.domains.cortex.ingestion`` package."""
    spec = importlib.util.spec_from_file_location("worker_queue_roles_v1", _ROLES_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_ROLES_MODULE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Split ECS worker Celery queue bindings")
    parser.add_argument("input", type=Path, help="Source ECS task definition JSON (worker)")
    parser.add_argument("ingestion_out", type=Path, help="Ingestion worker task def output")
    parser.add_argument("substrate_out", type=Path, help="Substrate worker task def output")
    parser.add_argument("canon_out", type=Path, help="Canon-only worker task def output")
    parser.add_argument("identity_out", type=Path, help="Identity-only worker task def output")
    parser.add_argument("--ingestion-family", default="", help="Optional task family override")
    parser.add_argument("--substrate-family", default="vector-substrate-worker")
    parser.add_argument("--canon-family", default="vector-canon-worker")
    parser.add_argument("--identity-family", default="vector-identity-worker")
    args = parser.parse_args()

    roles = _load_roles_module()
    task_def = json.loads(args.input.read_text(encoding="utf-8"))
    ingestion = roles.apply_worker_role_to_task_definition_v1(task_def, role="ingestion")
    substrate = roles.apply_worker_role_to_task_definition_v1(task_def, role="substrate")
    canon = roles.apply_canon_worker_task_definition_v1(task_def)
    identity = roles.apply_worker_role_to_task_definition_v1(task_def, role="identity")
    if args.ingestion_family:
        ingestion["family"] = args.ingestion_family
    if args.substrate_family:
        substrate["family"] = args.substrate_family
    if args.canon_family:
        canon["family"] = args.canon_family
    if args.identity_family:
        identity["family"] = args.identity_family

    args.ingestion_out.write_text(json.dumps(ingestion, indent=2) + "\n", encoding="utf-8")
    args.substrate_out.write_text(json.dumps(substrate, indent=2) + "\n", encoding="utf-8")
    args.canon_out.write_text(json.dumps(canon, indent=2) + "\n", encoding="utf-8")
    args.identity_out.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
