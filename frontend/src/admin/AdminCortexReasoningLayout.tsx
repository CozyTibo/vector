import { NavLink, Outlet, useParams } from "react-router-dom";

const REASONING_SECTIONS = [
  { key: "", label: "Overview", end: true },
  { key: "jobs", label: "Jobs", end: false },
  { key: "legality", label: "Runtime legality", end: true },
  { key: "certification-pack", label: "Certification pack", end: true },
] as const;

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-violet-100 text-violet-900 ring-1 ring-inset ring-violet-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexReasoningLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/reasoning`;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        Live TCRE reconstruction — chronology, causal chains, receipts, and replay equivalence on tenant
        canonical materializations.
      </p>
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {REASONING_SECTIONS.map((s) => (
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
