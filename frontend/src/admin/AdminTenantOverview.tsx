import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type ChatMsg = {
  role: string;
  content: string;
  created_at: string;
};

type SlackStakeholdersSnap = {
  raw_text: string | null;
  slack_user_ids: string[];
};

type OnboardingSnap = {
  status: string;
  current_step: string;
  started_at: string | null;
  completed_at: string | null;
  abandoned_at: string | null;
  profile_phase: string | null;
  tools_interest: string[];
  company_domain: string | null;
  company_website: string | null;
  company_size: string | null;
  user_role: string | null;
  tools_engineering: string[];
  tools_pm: string[];
  tools_communication: string[];
  tools_docs: string[];
  tools_crm: string[];
  tools_stack: Record<string, unknown> | null;
  slack_stakeholders: SlackStakeholdersSnap | null;
  chat_messages: ChatMsg[];
};

type TenantDetail = {
  id: string;
  company_name: string;
  created_at: string;
  onboarding: OnboardingSnap | null;
  member_full_name: string | null;
  connected_connectors: string[];
};

export default function AdminTenantOverview() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminJson<TenantDetail>(`/admin/tenants/${tenantId}`),
    enabled: Boolean(tenantId),
  });

  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const t = q.data;
  const ob = t.onboarding;
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-stone-900">{t.company_name}</h2>
        <dl className="grid max-w-md grid-cols-[auto_1fr] gap-2 text-sm">
          <dt className="text-stone-500">Tenant ID</dt>
          <dd className="font-mono text-stone-800">{t.id}</dd>
          <dt className="text-stone-500">Created</dt>
          <dd>{new Date(t.created_at).toLocaleString()}</dd>
          <dt className="text-stone-500">Connectors</dt>
          <dd>{t.connected_connectors.length ? t.connected_connectors.join(", ") : "—"}</dd>
          <dt className="text-stone-500">Member (first)</dt>
          <dd>{t.member_full_name ?? "—"}</dd>
        </dl>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="mb-3 text-base font-semibold text-stone-900">Onboarding</h3>
        {ob ? (
          <div className="space-y-4 text-sm">
            <dl className="grid max-w-lg grid-cols-[auto_1fr] gap-2">
              <dt className="text-stone-500">Status</dt>
              <dd className="text-stone-800">{ob.status}</dd>
              <dt className="text-stone-500">Current step</dt>
              <dd className="text-stone-800">{ob.current_step}</dd>
              <dt className="text-stone-500">Profile phase</dt>
              <dd className="text-stone-800">{ob.profile_phase ?? "—"}</dd>
              <dt className="text-stone-500">Started</dt>
              <dd>{ob.started_at ? new Date(ob.started_at).toLocaleString() : "—"}</dd>
              <dt className="text-stone-500">Completed</dt>
              <dd>{ob.completed_at ? new Date(ob.completed_at).toLocaleString() : "—"}</dd>
              <dt className="text-stone-500">Abandoned</dt>
              <dd>{ob.abandoned_at ? new Date(ob.abandoned_at).toLocaleString() : "—"}</dd>
              <dt className="text-stone-500">User role (answers)</dt>
              <dd>{ob.user_role ?? "—"}</dd>
              <dt className="text-stone-500">Company website</dt>
              <dd>{ob.company_website ?? "—"}</dd>
              <dt className="text-stone-500">Company size</dt>
              <dd>{ob.company_size ?? "—"}</dd>
              <dt className="text-stone-500">Tools interest</dt>
              <dd>{ob.tools_interest.length ? ob.tools_interest.join(", ") : "—"}</dd>
              <dt className="text-stone-500">Company domain (legacy)</dt>
              <dd>{ob.company_domain ?? "—"}</dd>
              <dt className="text-stone-500">Engineering tools</dt>
              <dd>{ob.tools_engineering.length ? ob.tools_engineering.join(", ") : "—"}</dd>
              <dt className="text-stone-500">PM tools</dt>
              <dd>{ob.tools_pm.length ? ob.tools_pm.join(", ") : "—"}</dd>
              <dt className="text-stone-500">Communication</dt>
              <dd>{ob.tools_communication.length ? ob.tools_communication.join(", ") : "—"}</dd>
              <dt className="text-stone-500">Docs</dt>
              <dd>{ob.tools_docs.length ? ob.tools_docs.join(", ") : "—"}</dd>
              <dt className="text-stone-500">CRM &amp; customer support</dt>
              <dd>{ob.tools_crm.length ? ob.tools_crm.join(", ") : "—"}</dd>
              <dt className="text-stone-500">Tools stack (legacy)</dt>
              <dd className="min-w-0">
                {ob.tools_stack && Object.keys(ob.tools_stack).length > 0 ? (
                  <pre className="mt-1 max-h-64 overflow-auto rounded-md bg-stone-50 p-3 text-xs text-stone-800 whitespace-pre-wrap break-words">
                    {JSON.stringify(ob.tools_stack, null, 2)}
                  </pre>
                ) : (
                  "—"
                )}
              </dd>
              <dt className="text-stone-500">Slack handoff (your member)</dt>
              <dd className="min-w-0">
                {ob.slack_stakeholders &&
                (ob.slack_stakeholders.raw_text ||
                  (ob.slack_stakeholders.slack_user_ids?.length ?? 0) > 0) ? (
                  <div className="mt-1 space-y-2 rounded-md border border-stone-100 bg-stone-50 p-3 text-stone-800">
                    {ob.slack_stakeholders.raw_text ? (
                      <p className="whitespace-pre-wrap break-words text-xs">{ob.slack_stakeholders.raw_text}</p>
                    ) : null}
                    {(ob.slack_stakeholders.slack_user_ids?.length ?? 0) > 0 ? (
                      <p className="font-mono text-xs text-stone-600">
                        Slack user IDs: {ob.slack_stakeholders.slack_user_ids.join(", ")}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  "—"
                )}
              </dd>
            </dl>
            <div>
              <h4 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-stone-400">Chat log</h4>
              {ob.chat_messages.length === 0 ? (
                <p className="text-stone-500">No messages.</p>
              ) : (
                <ul className="max-h-80 space-y-2 overflow-auto rounded-md border border-stone-100 bg-stone-50 p-3 text-xs">
                  {ob.chat_messages.map((m, i) => (
                    <li key={`${m.created_at}-${i}`} className="whitespace-pre-wrap break-words">
                      <span className="font-medium text-stone-600">[{m.role}]</span>{" "}
                      <span className="text-stone-400">{new Date(m.created_at).toLocaleString()}</span>
                      <br />
                      {m.content}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-stone-600">No onboarding row yet (tenant never opened product onboarding).</p>
        )}
      </div>
    </div>
  );
}
