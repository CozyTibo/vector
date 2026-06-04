import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import AdminTenantsBulkHardDelete from "./AdminTenantsBulkHardDelete";
import { usePendingTenantDeletes } from "./usePendingTenantDeletes";
import AdminFeedbackBanner from "./ui/AdminFeedbackBanner";
import { OperatorIntro, OperatorSection } from "./ui/OperatorSections";
import { StatusBadge } from "./ui/StatusBadge";

type AdminFlash = { kind: "success" | "error"; text: string };

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
  const location = useLocation();
  const navigate = useNavigate();
  const q = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => adminJson<{ items: TenantRow[] }>("/admin/tenants"),
  });
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [bulkOpen, setBulkOpen] = useState(false);
  const [flash, setFlash] = useState<AdminFlash | null>(null);
  const { pending, jobError, enqueue, dismissJobError, visibleTenants, isDeleting } =
    usePendingTenantDeletes();
  const prevPendingCount = useRef(0);

  useEffect(() => {
    if (prevPendingCount.current > 0 && pending.length === 0 && !jobError) {
      setFlash({
        kind: "success",
        text:
          prevPendingCount.current === 1
            ? "Workspace deletion finished."
            : "All workspace deletions finished.",
      });
    }
    prevPendingCount.current = pending.length;
  }, [pending.length, jobError]);

  useEffect(() => {
    const st = location.state as { adminFlash?: AdminFlash } | null | undefined;
    if (!st?.adminFlash) {
      return;
    }
    setFlash(st.adminFlash);
    navigate(`${location.pathname}${location.search}`, { replace: true, state: {} });
  }, [location, navigate]);

  const selectedTenants = useMemo(() => {
    if (!q.data) {
      return [];
    }
    const map = new Map(q.data.items.map((t) => [t.id, t]));
    return [...selected].map((id) => map.get(id)).filter(Boolean) as TenantRow[];
  }, [q.data, selected]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    if (!q.data?.items.length) {
      return;
    }
    setSelected(new Set(q.data.items.map((t) => t.id)));
  };

  const clearSelection = () => setSelected(new Set());

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
      {flash ? (
        <AdminFeedbackBanner
          kind={flash.kind}
          message={flash.text}
          onDismiss={() => setFlash(null)}
        />
      ) : null}
      {isDeleting ? (
        <div
          className="flex items-start gap-3 rounded-lg border border-sky-300 bg-sky-50 px-4 py-3 text-sm text-sky-950 shadow-sm"
          role="status"
        >
          <p className="min-w-0 flex-1 leading-relaxed">
            {pending.length === 1
              ? `Deleting “${pending[0]?.company_name}” in the background… The card will disappear when finished.`
              : `Deleting ${pending.length} workspaces in the background (${pending.map((p) => p.company_name).join(", ")})… Cards disappear as each completes.`}
          </p>
        </div>
      ) : null}
      {jobError ? (
        <AdminFeedbackBanner
          kind="error"
          message={`Workspace delete job failed: ${jobError}`}
          onDismiss={dismissJobError}
        />
      ) : null}
      <OperatorIntro title="Workspaces">
        Each workspace is one company using Vector. Open a card to see health, onboarding, and pipeline
        state — this is the main operator entry point after you pick who you are helping.
      </OperatorIntro>

      <OperatorSection title="All workspaces" description="Open a workspace to manage onboarding, integrations, and data.">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
            disabled={!q.data.items.length}
            onClick={selectAll}
          >
            Select all
          </button>
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
            disabled={selected.size === 0}
            onClick={clearSelection}
          >
            Clear selection
          </button>
          <button
            type="button"
            className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-900 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={selected.size === 0}
            onClick={() => setBulkOpen(true)}
          >
            Delete selected… ({selected.size})
          </button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {q.data.items.length === 0 ? (
            <p className="text-sm text-stone-500">No workspaces yet.</p>
          ) : (
            visibleTenants(q.data.items).map((t) => (
              <div
                key={t.id}
                className="flex gap-2 rounded-xl border border-stone-200 bg-white shadow-sm transition hover:border-stone-300 hover:shadow"
              >
                <label className="flex shrink-0 cursor-pointer items-start pt-5 pl-3">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-stone-400 text-red-700 focus:ring-red-600"
                    checked={selected.has(t.id)}
                    onChange={() => toggle(t.id)}
                    aria-label={`Select ${t.company_name}`}
                  />
                </label>
                <Link
                  to={`/admin/tenants/${t.id}/workspace`}
                  className="group min-w-0 flex-1 p-5 pl-0"
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
              </div>
            ))
          )}
        </div>
      </OperatorSection>

      {bulkOpen && selectedTenants.length > 0 ? (
        <AdminTenantsBulkHardDelete
          tenants={selectedTenants.map((t) => ({ id: t.id, company_name: t.company_name }))}
          onCancel={() => setBulkOpen(false)}
          onAccepted={({ pending: rows }) => {
            setBulkOpen(false);
            clearSelection();
            enqueue(rows);
            setFlash({
              kind: "success",
              text:
                rows.length === 1
                  ? `Deletion started for “${rows[0]?.company_name}”.`
                  : `Deletion started for ${rows.length} workspaces.`,
            });
          }}
        />
      ) : null}
    </main>
  );
}
