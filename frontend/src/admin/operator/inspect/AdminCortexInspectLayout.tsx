import { NavLink, Outlet, useParams } from "react-router-dom";

const INSPECT_LENSES = [
  { key: "", label: "Hub" },
  { key: "identity", label: "Identity" },
  { key: "graph", label: "Graph" },
  { key: "islands", label: "Islands" },
  { key: "retrieval", label: "Retrieval" },
  { key: "synthesis", label: "Synthesis" },
  { key: "execution", label: "Execution" },
] as const;

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexInspectLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  return (
    <div className="space-y-5">
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {INSPECT_LENSES.map((lens) => {
          const path =
            lens.key === ""
              ? `/admin/tenants/${tenantId}/cortex/inspect`
              : `/admin/tenants/${tenantId}/cortex/inspect/${lens.key}`;
          return (
            <NavLink key={lens.key || "hub"} to={path} end={lens.key === ""} className={({ isActive }) => tabCls(isActive)}>
              {lens.label}
            </NavLink>
          );
        })}
      </nav>
      <Outlet />
    </div>
  );
}
