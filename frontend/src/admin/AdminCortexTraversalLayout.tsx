import { Link, NavLink, Outlet, useParams } from "react-router-dom";

const SECTIONS = [
  { key: "", label: "Overview", end: true },
  { key: "control-plane", label: "Control plane", end: true },
] as const;

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexTraversalLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/traversal`;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        OCTS bounded graph walks — replay identity, traversal receipts, and structural queue visibility. Not
        semantic search or LLM retrieval.{" "}
        <Link to={`/admin/tenants/${tenantId}/cortex/graph`} className="text-indigo-700 underline">
          Graph console
        </Link>{" "}
        has walk-derived projections and replay proofs.
      </p>
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {SECTIONS.map((s) => (
          <NavLink
            key={s.key || "overview"}
            to={s.key ? `${base}/${s.key}` : base}
            end={s.end}
            className={({ isActive }) => tabCls(isActive)}
          >
            {s.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
