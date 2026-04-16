import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { OperatorIntro, OperatorSection } from "./ui/OperatorSections";
import { StatusBadge } from "./ui/StatusBadge";

type TenantRow = {
  id: string;
  company_name: string;
  created_at: string;
  workspace_access_enabled: boolean;
  onboarding_status: string | null;
  onboarding_current_step: string | null;
  connected_connectors: string[];
};

export default function AdminWorkspacesPage() {
  const q = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => adminJson<{ items: TenantRow[] }>("/admin/tenants"),
  });

  if (q.isPending) {
    return <p className="mx-auto max-w-6xl px-4 py-8 text-sm text-stone-600">Loading workspaces…</p>;
  }
  if (q.isError) {
    return (
      <p className="mx-auto max-w-6xl px-4 py-8 text-sm text-red-700">{(q.error as Error).message}</p>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <OperatorIntro title="Workspaces">
        Each workspace is one company using Vector. Open a card to see health, onboarding, and pipeline
        state — this is the main operator entry point after you pick who you are helping.
      </OperatorIntro>

      <OperatorSection title="All workspaces" description="Open a workspace to manage onboarding, integrations, and data.">
        <div className="grid gap-4 sm:grid-cols-2">
          {q.data.items.length === 0 ? (
            <p className="text-sm text-stone-500">No workspaces yet.</p>
          ) : (
            q.data.items.map((t) => (
              <Link
                key={t.id}
                to={`/admin/tenants/${t.id}/workspace`}
                className="group rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition hover:border-stone-300 hover:shadow"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-lg font-semibold text-stone-900 group-hover:text-blue-800">
                    {t.company_name}
                  </h3>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <StatusBadge tone={t.workspace_access_enabled ? "ok" : "warn"}>
                      {t.workspace_access_enabled ? "Active" : "Waitlist"}
                    </StatusBadge>
                    <StatusBadge tone={t.connected_connectors.length ? "ok" : "neutral"}>
                      {t.connected_connectors.length ? "Connected" : "No connectors"}
                    </StatusBadge>
                  </div>
                </div>
                <p className="mt-2 text-sm text-stone-600">
                  Onboarding: {t.onboarding_status ?? "—"}
                  {t.onboarding_current_step ? (
                    <span className="block text-xs text-stone-500">{t.onboarding_current_step}</span>
                  ) : null}
                </p>
                <p className="mt-2 text-xs text-stone-500">
                  Connectors:{" "}
                  {t.connected_connectors.length ? t.connected_connectors.join(", ") : "none"}
                </p>
              </Link>
            ))
          )}
        </div>
      </OperatorSection>
    </main>
  );
}
