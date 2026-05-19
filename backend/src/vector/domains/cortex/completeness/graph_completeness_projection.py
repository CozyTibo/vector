"""Graph construction completeness (org graph linkage accounting).

Step 13 delegates propagation law to ``operational_runtime.graph_completeness_propagation``.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session


def _derive_graph_substrate_state_v1(
    *,
    entity_count: int,
    linked_entities: int,
    orphan_count: int,
    link_count: int,
    candidate_count: int,
) -> str:
    from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
        derive_graph_completeness_substrate_state_v1,
    )

    return derive_graph_completeness_substrate_state_v1(
        entity_count=entity_count,
        linked_entities=linked_entities,
        orphan_count=orphan_count,
        link_count=link_count,
        candidate_count=candidate_count,
        pending_candidates=0,
        graph_maturity_stage="G1",
        fake_green_blocked=False,
        orphan_disconnected_count=0,
        orphan_identity_unresolved_count=0,
    )


def project_graph_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Project graph stage envelope (**G-P085-GRAPH-PROP-01**)."""
    from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
        propagate_graph_completeness_stage_v1,
    )

    return propagate_graph_completeness_stage_v1(session, tenant_id=tenant_id)
