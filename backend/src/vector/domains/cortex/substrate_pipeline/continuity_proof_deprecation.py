"""Phase C3 — deprecation notices for per-phase continuity proof scripts."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Final

CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1: Final[str] = "continuity_audit_snapshot.py"
CANONICAL_AUDIT_SNAPSHOT_MODULE_V1: Final[str] = (
    "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot"
)

DEPRECATED_CONTINUITY_PROOF_SCRIPTS_V1: Final[tuple[str, ...]] = (
    "continuity_p0_phase_a1_synthesis_job_reconcile_proof.py",
    "continuity_p0_phase_a2_ecs_deploy_align_proof.py",
    "continuity_p0_phase_a3_tcre_queued_drain_proof.py",
    "continuity_p0_phase_a4_aa_panel_strict_proof.py",
    "continuity_p0_phase_a5_trace_only_ban_proof.py",
    "continuity_p0_phase_a6_synthesis_terminal_transitions_proof.py",
    "continuity_p0_phase_b1_retrieval_publish_contract_proof.py",
    "continuity_p0_phase_b2_retrieval_epoch_scope_alignment_proof.py",
    "continuity_p0_phase_b3_retrieval_registry_epoch_proof.py",
    "continuity_p0_phase_b4_phase05_walks_persisted_proof.py",
    "continuity_p0_phase_b5_graph_hash_autonomous_chain_proof.py",
    "continuity_p0_phase_b6_post_ingestion_fresh_pipeline_run_proof.py",
    "continuity_p0_phase_c1_phase08_empty_scope_truth_proof.py",
    "continuity_p0_phase_c2_synthesis_scope_caps_proof.py",
    "continuity_proof_panel.py",
    "prod_substrate_proof_queries.py",
)


def deprecation_message_for_script_v1(script_path: str | Path) -> str:
    name = Path(script_path).name
    return (
        f"{name} is deprecated (Phase C3). Use backend/scripts/"
        f"{CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1} for unified JSON + AA panel + SQL snapshot. "
        "Per-phase proof scripts remain for CI step gates only."
    )


def warn_deprecated_continuity_proof_script_v1(script_path: str | Path) -> None:
    """Emit ``DeprecationWarning`` when a legacy proof script is executed."""
    warnings.warn(
        deprecation_message_for_script_v1(script_path),
        DeprecationWarning,
        stacklevel=3,
    )
