#!/usr/bin/env python3
"""Merge GitHub ingest cap env vars (10/16/120) into ECS task definition JSON (D2)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_CAPS_MODULE_PATH = (
    REPO_ROOT
    / "backend/src/vector/domains/cortex/ingestion/github_ingest_caps_ecs.py"
)


def _load_caps_module():
    """Load ECS cap merge without importing ``vector.domains.cortex.ingestion`` package."""
    spec = importlib.util.spec_from_file_location("github_ingest_caps_ecs", _CAPS_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_CAPS_MODULE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Align ECS task def GitHub ingest caps to code defaults")
    parser.add_argument("input", type=Path, help="Input ECS task definition JSON")
    parser.add_argument("output", type=Path, help="Output ECS task definition JSON")
    args = parser.parse_args()

    caps = _load_caps_module()
    task_def = json.loads(args.input.read_text(encoding="utf-8"))
    merged = caps.merge_github_caps_into_ecs_task_definition_v1(task_def)
    args.output.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
