"""§6 Step 15 — ExecutionGraph contract round-trip."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
)


def test_execution_graph_model_round_trip() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    g = ExecutionGraph(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        nodes=[
            ExecutionNode(id="a:1", kind="thread", execution_state="in_progress"),
            ExecutionNode(id="b:2", kind="issue", execution_state="done", owner_hint="@x"),
        ],
        edges=[
            ExecutionEdge(
                id="exec_edge:abc",
                from_id="a:1",
                to_id="b:2",
                relation="references",
            )
        ],
        unresolved_dependency_refs=["wi|waits_on|legal"],
    )
    dumped = g.model_dump(mode="json")
    again = ExecutionGraph.model_validate(dumped)
    assert again == g
