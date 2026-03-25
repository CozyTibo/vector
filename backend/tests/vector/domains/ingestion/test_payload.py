from __future__ import annotations

import uuid

from vector.domains.ingestion.payload import canonical_payload_hash, idempotency_key


def test_canonical_payload_hash_stable() -> None:
    a = {"b": 1, "a": {"z": 2, "y": 3}}
    b = {"a": {"y": 3, "z": 2}, "b": 1}
    assert canonical_payload_hash(a) == canonical_payload_hash(b)


def test_idempotency_key_stable() -> None:
    run = uuid.uuid4()
    k1 = idempotency_key(
        run_id=run,
        resource_type="github.pull_request",
        external_id="acme/api#1",
        api_endpoint="GET /repos/{owner}/{repo}/pulls",
        query_params={"page": 1, "per_page": 100},
    )
    k2 = idempotency_key(
        run_id=run,
        resource_type="github.pull_request",
        external_id="acme/api#1",
        api_endpoint="GET /repos/{owner}/{repo}/pulls",
        query_params={"per_page": 100, "page": 1},
    )
    assert k1 == k2
