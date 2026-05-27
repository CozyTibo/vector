"""ECS worker task image alignment updates every container (worker + celery-beat)."""

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCRIPT = _REPO_ROOT / "backend/scripts/ecs_set_worker_task_images.py"


def _load_apply():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ecs_set_worker_task_images", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.apply_worker_image_to_all_containers


def test_apply_worker_image_updates_all_containers() -> None:
    apply = _load_apply()
    task_def = {
        "containerDefinitions": [
            {"name": "worker", "image": "old/worker:aaa", "environment": []},
            {"name": "celery-beat", "image": "old/worker:bbb", "environment": []},
        ],
    }
    out = apply(
        task_def,
        image="884953290372.dkr.ecr.eu-west-1.amazonaws.com/vector-worker:deadbeef",
        git_sha="deadbeef",
    )
    images = [c["image"] for c in out["containerDefinitions"]]
    assert images == [
        "884953290372.dkr.ecr.eu-west-1.amazonaws.com/vector-worker:deadbeef",
        "884953290372.dkr.ecr.eu-west-1.amazonaws.com/vector-worker:deadbeef",
    ]
    for container in out["containerDefinitions"]:
        sha_env = [e for e in container["environment"] if e["name"] == "VECTOR_GIT_SHA"]
        assert sha_env == [{"name": "VECTOR_GIT_SHA", "value": "deadbeef"}]


def test_apply_worker_image_requires_containers() -> None:
    apply = _load_apply()
    with pytest.raises(ValueError, match="no containerDefinitions"):
        apply({}, image="x:y", git_sha="y")
