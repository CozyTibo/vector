"""Golden replay: canonical drain receipt hash is stable for fixed inputs."""

from __future__ import annotations

import uuid

from vector.domains.cortex.canonical.forward_progress.canonical_drain_receipt import (
    build_canonical_drain_receipt_hash_v1,
)


def test_canonical_drain_receipt_hash_golden_v1() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    batch_ids = [12, 34, 56]
    h1 = build_canonical_drain_receipt_hash_v1(
        tenant_id=tenant_id,
        bundle_id="bundle-golden",
        canonical_outcome="topology_wait",
        total_succeeded=0,
        total_failed_rows=0,
        batches_run=1,
        batch_ids=batch_ids,
        deferral_snapshot_id="def-snap-abc",
    )
    h2 = build_canonical_drain_receipt_hash_v1(
        tenant_id=tenant_id,
        bundle_id="bundle-golden",
        canonical_outcome="topology_wait",
        total_succeeded=0,
        total_failed_rows=0,
        batches_run=1,
        batch_ids=list(reversed(batch_ids)),
        deferral_snapshot_id="def-snap-abc",
    )
    assert h1 == h2
    assert len(h1) == 64
    assert h1 != build_canonical_drain_receipt_hash_v1(
        tenant_id=tenant_id,
        bundle_id="bundle-other",
        canonical_outcome="topology_wait",
        total_succeeded=0,
        total_failed_rows=0,
        batches_run=1,
        batch_ids=batch_ids,
        deferral_snapshot_id="def-snap-abc",
    )
