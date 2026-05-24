"""S5.2 — archived proof scripts and simplify contract."""

from vector.domains.cortex.substrate_pipeline.wave_s5_simplify_v1 import (
    verify_s5_2_simplify_contract_v1,
)


def test_s5_2_archived_proofs_and_canonical_scripts() -> None:
    out = verify_s5_2_simplify_contract_v1()
    assert out["s5_2_ok"] is True, out["errors"]
    assert out["archived_proof_count"] >= 30
