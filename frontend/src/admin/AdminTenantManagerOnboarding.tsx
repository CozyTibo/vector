import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type Summary = {
  tenant_id: string;
  slack_vector_paused: boolean;
  manager_slack_onboarding_disabled: boolean;
  /** From website onboarding ``slack_stakeholders`` (API adds when available). */
  suggested_slack_user_id?: string | null;
  session_count: number;
  invitation_count: number;
  sessions: {
    id: string;
    slack_user_id: string;
    status: string;
    current_step: string;
    muted: boolean;
    updated_at: string | null;
  }[];
};

type ChannelRow = {
  session_id: string;
  slack_channel_id: string;
  channel_name: string | null;
  access_status: string;
  bot_is_member: boolean;
  history_readable: boolean | null;
  validation_error: string | null;
};

export default function AdminTenantManagerOnboarding() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [slackUserOverride, setSlackUserOverride] = useState("");

  const summaryQ = useQuery({
    queryKey: ["admin-mo-tenant-summary", tenantId],
    queryFn: () => adminJson<Summary>(`/admin/tenants/${tenantId}/manager-onboarding/summary`),
    enabled: Boolean(tenantId),
  });

  const channelsQ = useQuery({
    queryKey: ["admin-mo-tenant-channels", tenantId],
    queryFn: () =>
      adminJson<{ items: ChannelRow[] }>(`/admin/tenants/${tenantId}/manager-onboarding/channels`),
    enabled: Boolean(tenantId),
  });

  useEffect(() => {
    if (!summaryQ.data?.suggested_slack_user_id) {
      return;
    }
    setSlackUserOverride((prev) => prev || summaryQ.data!.suggested_slack_user_id!);
  }, [summaryQ.data?.suggested_slack_user_id]);

  const triggerIntroMut = useMutation({
    mutationFn: async () => {
      const trimmed = slackUserOverride.trim();
      const res = await adminFetch(`/admin/tenants/${tenantId}/manager-onboarding/trigger-intro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(trimmed ? { slack_user_id: trimmed } : {}),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<{ ok: boolean; slack_user_id: string }>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-mo-tenant-summary", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-sessions"] });
    },
  });

  const policyMut = useMutation({
    mutationFn: async (body: {
      slack_vector_paused?: boolean;
      manager_slack_onboarding_disabled?: boolean;
    }) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/manager-onboarding/slack-policy`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<unknown>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-mo-tenant-summary", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
    },
  });

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (summaryQ.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (summaryQ.isError) {
    return <p className="text-sm text-red-700">{(summaryQ.error as Error).message}</p>;
  }

  const sum = summaryQ.data;
  const btn =
    "rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">Manager Slack onboarding</h2>
          <p className="mt-1 text-sm text-stone-600">
            Tenant-level Slack policy, observed channels, and sessions for this workspace.
          </p>
        </div>
        <Link
          to={`/admin/manager-onboarding?tenant_id=${encodeURIComponent(tenantId)}`}
          className="text-sm font-medium text-blue-700 underline"
        >
          Filter global list →
        </Link>
      </div>

      {policyMut.isError ? (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
          {(policyMut.error as Error).message}
        </p>
      ) : null}

      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="mb-3 text-base font-semibold text-stone-900">Queue Slack intro (Celery)</h3>
        <p className="mb-3 text-sm text-stone-600">
          Enqueues the same task as after website handoff (<code className="text-xs">send_intro</code>).
          Uses the Slack user below, or the first id from onboarding{" "}
          <span className="font-mono text-xs">slack_stakeholders</span> when the field is empty. Requires{" "}
          <code className="text-xs">MANAGER_SLACK_ONBOARDING_ENABLED=true</code> on the API and a running
          worker.
        </p>
        <label className="mb-2 block text-xs font-medium text-stone-600">
          Slack user id (optional if set from onboarding)
        </label>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <input
            type="text"
            className="min-w-[220px] flex-1 rounded-md border border-stone-300 px-3 py-2 font-mono text-sm"
            placeholder="U0123456789"
            value={slackUserOverride}
            onChange={(e) => setSlackUserOverride(e.target.value)}
            aria-label="Slack user id"
          />
          <button
            type="button"
            className={btn}
            disabled={triggerIntroMut.isPending}
            onClick={() => triggerIntroMut.mutate()}
          >
            {triggerIntroMut.isPending ? "Queueing…" : "Queue manager intro"}
          </button>
        </div>
        {triggerIntroMut.isError ? (
          <p className="text-sm text-red-700">{(triggerIntroMut.error as Error).message}</p>
        ) : null}
        {triggerIntroMut.isSuccess ? (
          <p className="text-sm text-green-800">
            Queued for <span className="font-mono">{triggerIntroMut.data.slack_user_id}</span>. Refresh
            sessions in a few seconds.
          </p>
        ) : null}
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="mb-3 text-base font-semibold text-stone-900">Slack policy</h3>
        <p className="mb-4 text-sm text-stone-600">
          When paused or disabled, the product skips outbound manager-onboarding Slack (intros, prompts, DMs)
          for this tenant. Individual sessions can still be muted from the session screen.
        </p>
        <dl className="mb-4 grid max-w-md grid-cols-[auto_1fr] gap-2 text-sm">
          <dt className="text-stone-500">Slack Vector paused</dt>
          <dd>{sum.slack_vector_paused ? "yes" : "no"}</dd>
          <dt className="text-stone-500">Manager onboarding disabled</dt>
          <dd>{sum.manager_slack_onboarding_disabled ? "yes" : "no"}</dd>
          <dt className="text-stone-500">Sessions</dt>
          <dd>{sum.session_count}</dd>
          <dt className="text-stone-500">Invitations</dt>
          <dd>{sum.invitation_count}</dd>
        </dl>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={btn}
            disabled={policyMut.isPending}
            onClick={() => policyMut.mutate({ slack_vector_paused: !sum.slack_vector_paused })}
          >
            Toggle Slack Vector paused
          </button>
          <button
            type="button"
            className={btn}
            disabled={policyMut.isPending}
            onClick={() =>
              policyMut.mutate({
                manager_slack_onboarding_disabled: !sum.manager_slack_onboarding_disabled,
              })
            }
          >
            Toggle manager onboarding disabled
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="mb-3 text-base font-semibold text-stone-900">Sessions</h3>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Slack user</th>
                <th>Status</th>
                <th>Step</th>
                <th>Muted</th>
              </tr>
            </thead>
            <tbody>
              {sum.sessions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-stone-500">
                    No sessions
                  </td>
                </tr>
              ) : (
                sum.sessions.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <Link
                        to={`/admin/manager-onboarding/sessions/${s.id}`}
                        className="font-mono text-xs text-blue-700 underline"
                      >
                        {s.id.slice(0, 8)}…
                      </Link>
                    </td>
                    <td className="font-mono text-xs">{s.slack_user_id}</td>
                    <td>{s.status}</td>
                    <td className="text-xs">{s.current_step}</td>
                    <td>{s.muted ? "yes" : "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="mb-3 text-base font-semibold text-stone-900">Channel observations</h3>
        {channelsQ.isPending ? (
          <p className="text-sm text-stone-600">Loading channels…</p>
        ) : channelsQ.isError ? (
          <p className="text-sm text-red-700">{(channelsQ.error as Error).message}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Name</th>
                  <th>Session</th>
                  <th>Access</th>
                  <th>Bot member</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {channelsQ.data.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-stone-500">
                      None
                    </td>
                  </tr>
                ) : (
                  channelsQ.data.items.map((c) => (
                    <tr key={`${c.session_id}-${c.slack_channel_id}`}>
                      <td className="font-mono text-xs">{c.slack_channel_id}</td>
                      <td>{c.channel_name ?? "—"}</td>
                      <td>
                        <Link
                          to={`/admin/manager-onboarding/sessions/${c.session_id}`}
                          className="font-mono text-xs text-blue-700 underline"
                        >
                          {c.session_id.slice(0, 8)}…
                        </Link>
                      </td>
                      <td>{c.access_status}</td>
                      <td>{c.bot_is_member ? "yes" : "no"}</td>
                      <td className="max-w-xs truncate text-xs text-red-700">{c.validation_error ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
