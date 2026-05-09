import { NavLink, Outlet, useParams } from "react-router-dom";

const SECONDARY: Array<{ to: string; label: string }> = [
  { to: "runtime", label: "Materialize" },
  { to: "replay", label: "Replay" },
  { to: "verification", label: "Verification" },
  { to: "ambiguities", label: "Ambiguities" },
  { to: "registry", label: "Registry" },
  { to: "doctrine", label: "Doctrine" },
  { to: "debug", label: "Debug" },
  { to: "legacy-tools", label: "Legacy tools" },
  { to: "inspector", label: "Raw inspector" },
  { to: "stabilization", label: "Stabilization" },
  { to: "certification", label: "Certification" },
];

function subCls(active: boolean) {
  return [
    "whitespace-nowrap rounded-md px-2.5 py-1 text-xs no-underline",
    active ? "bg-indigo-600 font-semibold text-white" : "bg-stone-100 font-medium text-stone-700 hover:bg-stone-200",
  ].join(" ");
}

export default function AdminCortexCanonicalAdvancedLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/canonical/advanced`;
  const canonicalBase = `/admin/tenants/${tenantId}/cortex/canonical`;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-950">
        <span className="font-semibold">Advanced</span> — internal surfaces for deep inspection. For day-to-day
        operations use{" "}
        <NavLink className="font-medium text-indigo-800 underline-offset-2 hover:underline" to={`${canonicalBase}/health`}>
          Health
        </NavLink>
        ,{" "}
        <NavLink className="font-medium text-indigo-800 underline-offset-2 hover:underline" to={`${canonicalBase}/coverage`}>
          Coverage
        </NavLink>
        , or{" "}
        <NavLink className="font-medium text-indigo-800 underline-offset-2 hover:underline" to={`${canonicalBase}/failures`}>
          Failures
        </NavLink>
        .
      </div>
      <div className="-mx-1 overflow-x-auto pb-1">
        <nav className="flex min-w-min flex-wrap gap-1 rounded-lg border border-stone-200 bg-stone-50/90 p-2">
          {SECONDARY.map((t) => (
            <NavLink key={t.to} to={`${base}/${t.to}`} className={({ isActive }) => subCls(isActive)}>
              {t.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </div>
  );
}
