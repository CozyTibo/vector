import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import AdminTenantHardDelete from "./AdminTenantHardDelete";
import { StatusBadge } from "./ui/StatusBadge";

type OnboardingBrief = {
  status: string;
  current_step: string;
} | null;

type TenantDetail = {
  id: string;
  company_name: string;
  created_at: string;
  workspace_access_enabled: boolean;
  onboarding: OnboardingBrief;
  member_full_name: string | null;
  member_email: string | null;
  connected_connectors: string[];
  slack_vector_paused: boolean;
};

type Conn = { id: string; provider: string; status: string; created_at: string };

type MoSummary = {
  session_count: number;
  invitation_count?: number;
  managers_with_sessions?: number;
  managers_completed?: number;
  managers_in_progress?: number;
  managers_needs_attention?: number;
  slack_vector_paused: boolean;
};

function Tile({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`flex min-h-0 flex-col rounded-lg border border-stone-200 bg-white p-3 shadow-sm ${className}`}
    >
      <h3 className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-stone-500">{title}</h3>
      <div className="mt-2 min-h-0 flex-1 text-sm leading-snug text-stone-800">{children}</div>
    </div>
  );
}

function TileLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="mt-2 inline-flex w-fit shrink-0 text-xs font-medium text-blue-700 underline decoration-blue-400 underline-offset-2 hover:text-blue-900"
    >
      {children}
    </Link>
  );
}

export default function AdminWorkspacePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const tenantQ = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminJson<TenantDetail>(`/admin/tenants/${tenantId}`),
    enabled: Boolean(tenantId),
  });

  const connQ = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  const moQ = useQuery({
    queryKey: ["admin-mo-tenant-summary", tenantId],
    queryFn: () => adminJson<MoSummary>(`/admin/tenants/${tenantId}/manager-onboarding/summary`),
    enabled: Boolean(tenantId),
  });

  const workspaceAccessMut = useMutation({
    mutationFn: async (workspace_access_enabled: boolean) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/workspace-access`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_access_enabled }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<unknown>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-tenants"] });
    },
  });

  const slackPauseMut = useMutation({
    mutationFn: async (slack_vector_paused: boolean) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/manager-onboarding/slack-policy`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slack_vector_paused }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<unknown>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-tenant-summary", tenantId] });
    },
  });

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (tenantQ.isPending || connQ.isPending) {
    return <p className="text-sm text-stone-600">Loading workspace…</p>;
  }
  if (tenantQ.isError) {
    return <p className="text-sm text-red-700">{(tenantQ.error as Error).message}</p>;
  }
  if (connQ.isError) {
    return <p className="text-sm text-red-700">{(connQ.error as Error).message}</p>;
  }

  const t = tenantQ.data;
  const mo = moQ.data;
  const slackBtn =
    "rounded-md border px-3 py-1.5 text-sm font-medium disabled:opacity-50 " +
    (t.slack_vector_paused
      ? "border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800"
      : "border-amber-700 bg-amber-600 text-white hover:bg-amber-700");

  const accessBtn =
    "rounded-md border px-3 py-1.5 text-sm font-medium disabled:opacity-50 " +
    (t.workspace_access_enabled
      ? "border-amber-700 bg-amber-600 text-white hover:bg-amber-700"
      : "border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800");

  const ob = t.onboarding;
  const websiteObBadge = !ob ? "Not started" : `${ob.status} · ${ob.current_step}`;

  const websiteObLine = !ob
    ? "Website signup chat not opened yet."
    : `${ob.status} · ${ob.current_step}`;

  const websiteObTone: "ok" | "warn" | "neutral" = !ob
    ? "neutral"
    : ob.status.toLowerCase() === "completed"
      ? "ok"
      : "warn";

  const moTotal = mo ? (mo.managers_with_sessions ?? mo.session_count) : 0;
  const moDone = mo?.managers_completed ?? 0;
  const moActive = mo?.managers_in_progress ?? 0;
  const moAttention = mo?.managers_needs_attention ?? 0;
  const moInvites = mo?.invitation_count ?? 0;

  const slackObTag = !moQ.isFetched
    ? "Loading…"
    : !mo
      ? "—"
      : mo.slack_vector_paused
        ? "Paused"
        : moTotal > 0
          ? `${moTotal} manager${moTotal === 1 ? "" : "s"} in Slack`
          : moInvites > 0
            ? `${moInvites} invite${moInvites === 1 ? "" : "s"} pending`
            : "No managers yet";

  const slackObTone: "ok" | "warn" | "neutral" =
    !moQ.isFetched || !mo
      ? "neutral"
      : mo.slack_vector_paused
        ? "warn"
        : moTotal > 0 || moInvites > 0
          ? "ok"
          : "neutral";

  const slackObLine = !moQ.isFetched
    ? "Loading…"
    : !mo
      ? "Unavailable."
      : mo.slack_vector_paused
        ? "Vector is not sending Slack DMs; managers may be waiting."
        : moTotal === 0 && moInvites === 0
            ? "No managers are in Slack onboarding yet."
            : moTotal === 0 && moInvites > 0
              ? `${moInvites} invitation${moInvites === 1 ? "" : "s"} sent or queued — no live Slack thread yet.`
              : (() => {
                  const parts: string[] = [];
                  if (moDone > 0) {
                    parts.push(`${moDone} finished`);
                  }
                  if (moActive > 0) {
                    parts.push(`${moActive} in progress`);
                  }
                  if (moAttention > 0) {
                    parts.push(`${moAttention} need review or blocked`);
                  }
                  if (parts.length > 0) {
                    return parts.join(" · ");
                  }
                  return `${moTotal} manager DM thread${moTotal === 1 ? "" : "s"} — open details for per-manager status.`;
                })();

  return (
    <div className="space-y-3">
      <header className="shrink-0 border-b border-stone-200/80 pb-2">
        <h1 className="text-lg font-semibold tracking-tight text-stone-900">{t.company_name}</h1>
        <p className="text-[11px] leading-snug text-stone-500">
          Company snapshot — open tabs above for integrations, data pipeline, execution graph, and debug.
        </p>
      </header>

      {/* Info tiles: 3 across on xl; connectors full width below */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3 xl:gap-2 xl:items-stretch">
        <Tile title="Product access">
          <div className="flex flex-wrap gap-1.5">
            <StatusBadge tone={t.workspace_access_enabled ? "ok" : "warn"}>
              {t.workspace_access_enabled ? "Active" : "Waitlist"}
            </StatusBadge>
          </div>
          <p className="mt-2 text-xs text-stone-600">
            {t.workspace_access_enabled
              ? "Members can use the app and website onboarding."
              : "Signed-in members only see the waitlist thank-you page until you activate this workspace."}
          </p>
          {workspaceAccessMut.isError ? (
            <p className="mt-2 text-xs text-red-700">{(workspaceAccessMut.error as Error).message}</p>
          ) : null}
          <button
            type="button"
            className={`mt-3 w-fit ${accessBtn}`}
            disabled={workspaceAccessMut.isPending}
            onClick={() => workspaceAccessMut.mutate(!t.workspace_access_enabled)}
          >
            {workspaceAccessMut.isPending
              ? "Updating…"
              : t.workspace_access_enabled
                ? "Move workspace to waitlist (deactivate)"
                : "Activate workspace for product access"}
          </button>
        </Tile>

        <Tile title="Company & contact">
          <p className="font-medium text-stone-900">{t.company_name}</p>
          <p className="mt-1 text-xs text-stone-600">
            Created {new Date(t.created_at).toLocaleString()}
          </p>
          <p className="mt-2 text-xs text-stone-500">
            Primary contact{" "}
            <span className="font-medium text-stone-800">{t.member_full_name ?? "—"}</span>
          </p>
          {t.member_email ? (
            <p className="mt-1 break-all text-xs text-stone-600">{t.member_email}</p>
          ) : (
            <p className="mt-1 text-xs text-stone-400">No email on file</p>
          )}
        </Tile>

        <Tile title="Website signup onboarding">
          <div className="flex flex-wrap gap-1.5">
            <StatusBadge tone={websiteObTone}>{websiteObBadge}</StatusBadge>
          </div>
          <p className="mt-2 line-clamp-2 text-xs text-stone-600">{websiteObLine}</p>
          <TileLink to={`/admin/tenants/${tenantId}/onboarding`}>Transcript &amp; answers →</TileLink>
        </Tile>

        <Tile title="Manager onboarding (Slack)">
          <div className="flex flex-wrap gap-1.5">
            <StatusBadge tone={slackObTone}>{slackObTag}</StatusBadge>
          </div>
          <p className="mt-2 line-clamp-2 text-xs text-stone-600">{slackObLine}</p>
          <TileLink to={`/admin/tenants/${tenantId}/slack-onboarding`}>Details &amp; conversations →</TileLink>
        </Tile>

        <Tile title="Connectors" className="xl:col-span-3">
          {t.connected_connectors.length === 0 ? (
            <p className="text-xs text-stone-600">None.</p>
          ) : (
            <ul className="flex flex-wrap gap-1">
              {t.connected_connectors.map((c) => (
                <li key={c}>
                  <span className="inline-flex rounded-full border border-stone-200 bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-800">
                    {c}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <TileLink to={`/admin/tenants/${tenantId}/integrations`}>Manage integrations →</TileLink>
        </Tile>

      </div>

      <details className="rounded border border-stone-200 bg-stone-50/80 text-xs">
        <summary className="cursor-pointer select-none px-2 py-1.5 font-medium text-stone-600">
          Debug: IDs
        </summary>
        <div className="border-t border-stone-200 bg-white px-2 py-2 font-mono text-[11px] text-stone-600">
          <p>tenant_id {t.id}</p>
          <ul className="mt-1 space-y-0.5">
            {connQ.data.items.map((c) => (
              <li key={c.id}>
                {c.provider}: {c.id}
              </li>
            ))}
          </ul>
        </div>
      </details>

      <section
        className="rounded-lg border border-stone-300/90 bg-stone-50/60 p-3 shadow-sm ring-1 ring-stone-950/[0.04]"
        aria-labelledby="workspace-sensitive-actions-heading"
      >
        <h2
          id="workspace-sensitive-actions-heading"
          className="text-[11px] font-semibold uppercase tracking-wide text-stone-600"
        >
          Sensitive workspace actions
        </h2>
        <p className="mt-1 text-xs text-stone-500">
          Pause Slack delivery or delete company data — use only when you intend to change production
          behavior for this workspace.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2 lg:items-stretch">
          <div
            className={[
              "flex min-h-0 flex-col rounded-md border p-3",
              t.slack_vector_paused
                ? "border-amber-600 bg-amber-50"
                : "border-stone-200 bg-white shadow-sm",
            ].join(" ")}
          >
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-stone-600">
              Slack delivery (whole workspace)
            </h3>
            <p className="mt-2 text-xs text-stone-600">
              When paused, Vector does not send <strong>any</strong> Slack messages for this company —
              not just manager onboarding. This is the main switch your team should use during incidents
              or customer requests.
            </p>
            {slackPauseMut.isError ? (
              <p className="mt-2 text-xs text-red-700">{(slackPauseMut.error as Error).message}</p>
            ) : null}
            <button
              type="button"
              className={`mt-3 w-fit ${slackBtn}`}
              disabled={slackPauseMut.isPending}
              onClick={() => slackPauseMut.mutate(!t.slack_vector_paused)}
            >
              {slackPauseMut.isPending
                ? "Updating…"
                : t.slack_vector_paused
                  ? "Resume Slack messages for this workspace"
                  : "Pause all Slack messages for this workspace"}
            </button>
          </div>
          <div className="min-h-0">
            <AdminTenantHardDelete tenantId={tenantId} companyName={t.company_name} compact />
          </div>
        </div>
      </section>
    </div>
  );
}
