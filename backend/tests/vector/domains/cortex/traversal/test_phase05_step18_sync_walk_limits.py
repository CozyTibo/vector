"""P05-18 — sync walk limits (**FS-API-01**); **G-P05-API-03** asserted in `test_phase05_step17_walk_api_contracts.py`."""

from __future__ import annotations

import uuid

from vector.domains.cortex.traversal.walk_api_contract import (
    canonical_octs_walk_api_json_utf8_len_v1,
    completed_sync_walk_api_public_document_v1,
    list_fs_api01_sync_request_json_cap_violations_v1,
    list_fs_api01_sync_response_json_cap_violations_v1,
)
from vector.domains.cortex.traversal.walk_policy import (
    SYNC_MAX_REQUEST_JSON_BYTES,
    SYNC_MAX_RESPONSE_JSON_BYTES,
)


def test_canonical_octs_walk_api_json_utf8_len_sorted_keys() -> None:
    a = canonical_octs_walk_api_json_utf8_len_v1({"z": 1, "a": 2})
    b = canonical_octs_walk_api_json_utf8_len_v1({"a": 2, "z": 1})
    assert a == b


def test_list_fs_api01_sync_request_json_cap_violations_over_limit() -> None:
    pad = "x" * (SYNC_MAX_REQUEST_JSON_BYTES + 10)
    body = {"walk_policy": {}, "start_node_ids": [pad]}
    v = list_fs_api01_sync_request_json_cap_violations_v1(body)
    assert len(v) == 1
    assert v[0].startswith("sync_request_json_bytes:")


def test_list_fs_api01_sync_response_json_cap_violations_over_limit() -> None:
    wid = uuid.UUID("00000000-0000-4000-8000-0000000000b2")
    huge = {
        "walk_result": {
            "walk_result_hash": "sha256:" + "aa" * 32,
            "hash_body": {"pad": "y" * (SYNC_MAX_RESPONSE_JSON_BYTES + 50)},
        },
        "telemetry": {},
    }
    doc = completed_sync_walk_api_public_document_v1(wid, huge)
    v = list_fs_api01_sync_response_json_cap_violations_v1(doc)
    assert len(v) == 1
    assert v[0].startswith("sync_response_json_bytes:")
