import cytoscape, { type Core } from "cytoscape";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import type { SubgraphResponse } from "../../lib/canonicalApi";
import { graphEdgeLabelRaw, graphNodeDisplayLabel } from "../../lib/executionModelDisplay";

type GraphPanelProps = {
  data: SubgraphResponse | null;
  error: string | null;
  loading: boolean;
};

export default function GraphPanel({ data, error, loading }: GraphPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!data) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }
    if (data.nodes.length === 0) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }
    if (!containerRef.current) {
      return;
    }

    const elements: cytoscape.ElementsDefinition = {
      nodes: data.nodes.map((n) => ({
        data: {
          id: n.id,
          label: graphNodeDisplayLabel(n),
          nt: n.node_type,
          ak: n.artifact_kind ?? "",
          fullId: n.id,
        },
      })),
      edges: data.edges.map((e) => {
        const tid = String(e.target_id);
        const edgeLabel = graphEdgeLabelRaw(e.relation_kind);
        return {
          data: {
            id: String(e.id),
            source: String(e.source_id),
            target: tid,
            label: edgeLabel,
          },
        };
      }),
    };

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "10px",
            color: "#e8eaed",
            "background-color": "#2c5282",
            width: "120px",
            height: "44px",
            shape: "roundrectangle",
            "text-wrap": "wrap",
            "text-max-width": "120px",
          },
        },
        {
          selector: 'node[nt = "actor"]',
          style: {
            "background-color": "#6b4a7a",
            shape: "ellipse",
          },
        },
        {
          selector: 'node[ak = "repository"]',
          style: {
            "background-color": "#1a365d",
          },
        },
        {
          selector: 'node[ak = "revision"]',
          style: {
            "background-color": "#4a5568",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#6e7681",
            "target-arrow-color": "#6e7681",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "9px",
            color: "#a0aec0",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        spacingFactor: 1.35,
        padding: 24,
      },
      wheelSensitivity: 0.35,
    });

    cy.on("tap", "node", (ev) => {
      const id = ev.target.id();
      const n = data.nodes.find((x) => x.id === id);
      if (!n) {
        return;
      }
      if (n.node_type === "artifact") {
        navigate(`/debug/canonical/artifacts/${id}`);
      } else {
        navigate(`/debug/canonical/actors/${id}`);
      }
    });

    const container = containerRef.current;
    cy.on("mouseover", "node", (ev) => {
      const id = ev.target.data("fullId") as string | undefined;
      if (id) {
        container.setAttribute("title", id);
      }
    });
    cy.on("mouseout", "node", () => {
      container.removeAttribute("title");
    });

    cy.fit(undefined, 32);
    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [data, navigate]);

  if (loading) {
    return <p className="status loading">Loading subgraph…</p>;
  }
  if (error) {
    return <p className="banner error">{error}</p>;
  }
  if (!data) {
    return <p className="meta">Enter a work object or person id and load.</p>;
  }

  if (data.nodes.length === 0) {
    return <p className="meta">Subgraph has no nodes (anchor may be isolated).</p>;
  }

  const anchorKind = data.anchor.type === "artifact" ? "Work object" : "Person";

  return (
    <div>
      {data.truncated ? (
        <p className="banner" style={{ marginBottom: "0.5rem" }}>
          Truncated: {data.truncation_reason ?? "limit reached"}
        </p>
      ) : null}
      <p className="meta" style={{ marginBottom: "0.5rem" }}>
        Anchor: {anchorKind} · depth {data.depth} · {data.nodes.length} nodes, {data.edges.length}{" "}
        connections
      </p>
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: 420,
          border: "1px solid #333",
          borderRadius: 8,
          background: "#0d1117",
        }}
      />
      <p className="meta" style={{ marginTop: "0.35rem" }}>
        Hover a node for internal id. Click to open the detail page.
      </p>
    </div>
  );
}
