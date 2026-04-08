import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { AdminOnboardingStyleThread, adminOnboardingRowsToChatMessages } from "./adminChatTranscript";
import { CollapsibleDebug, OperatorIntro, OperatorSection } from "./ui/OperatorSections";

type ChatMsg = {
  id: string;
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
  member_full_name: string | null;
  onboarding: OnboardingSnap | null;
};

export default function AdminTenantOnboardingPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminJson<TenantDetail>(`/admin/tenants/${tenantId}`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading onboarding…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const t = q.data;
  const ob = t.onboarding;
  const userLabel = t.member_full_name?.trim() || "User";
  const chatMessages = ob ? adminOnboardingRowsToChatMessages(ob.chat_messages) : [];

  return (
    <div className="space-y-8">
      <OperatorIntro title="Website onboarding">
        Structured answers first, then the in-app chat transcript (same order as the product flow:
        what we stored, then how we got there).
      </OperatorIntro>

      {!ob ? (
        <OperatorSection title="Status" description="No onboarding session in the database.">
          <p className="text-sm text-stone-600">
            This workspace has not opened product onboarding yet, or data was never created.
          </p>
        </OperatorSection>
      ) : (
        <>
          <OperatorSection
            title="Collected data"
            description="Structured fields captured during onboarding (answers and profile)."
          >
            <dl className="grid max-w-2xl grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-stone-500">Status</dt>
              <dd className="text-stone-900">{ob.status}</dd>
              <dt className="text-stone-500">Current step</dt>
              <dd className="text-stone-900">{ob.current_step}</dd>
              <dt className="text-stone-500">Profile phase</dt>
              <dd>{ob.profile_phase ?? "—"}</dd>
              <dt className="text-stone-500">Started</dt>
              <dd>{ob.started_at ? new Date(ob.started_at).toLocaleString() : "—"}</dd>
              <dt className="text-stone-500">Completed</dt>
              <dd>{ob.completed_at ? new Date(ob.completed_at).toLocaleString() : "—"}</dd>
              <dt className="text-stone-500">Abandoned</dt>
              <dd>{ob.abandoned_at ? new Date(ob.abandoned_at).toLocaleString() : "—"}</dd>
              <dt className="text-stone-500">User role</dt>
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
              <dt className="text-stone-500">CRM &amp; support</dt>
              <dd>{ob.tools_crm.length ? ob.tools_crm.join(", ") : "—"}</dd>
            </dl>

            <div className="mt-6 space-y-4">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-400">Slack handoff</h3>
                {ob.slack_stakeholders &&
                (ob.slack_stakeholders.raw_text || (ob.slack_stakeholders.slack_user_ids?.length ?? 0) > 0) ? (
                  <div className="mt-2 space-y-2 rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm text-stone-800">
                    {ob.slack_stakeholders.raw_text ? (
                      <p className="whitespace-pre-wrap break-words">{ob.slack_stakeholders.raw_text}</p>
                    ) : null}
                    {(ob.slack_stakeholders.slack_user_ids?.length ?? 0) > 0 ? (
                      <p className="font-mono text-xs text-stone-600">
                        Slack user IDs: {ob.slack_stakeholders.slack_user_ids.join(", ")}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-stone-500">—</p>
                )}
              </div>
              {ob.tools_stack && Object.keys(ob.tools_stack).length > 0 ? (
                <details className="rounded-lg border border-stone-200 bg-white">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-stone-700">
                    Tools stack (legacy JSON)
                  </summary>
                  <pre className="max-h-72 overflow-auto border-t border-stone-100 p-4 text-xs text-stone-800">
                    {JSON.stringify(ob.tools_stack, null, 2)}
                  </pre>
                </details>
              ) : null}
            </div>
          </OperatorSection>

          <OperatorSection
            title="Conversation"
            description="Chronological transcript: Vector on the left, signed-in user on the right (same layout as the product)."
          >
            <AdminOnboardingStyleThread
              messages={chatMessages}
              userDisplayName={userLabel}
              maxHeightClass="max-h-[min(44rem,85vh)]"
            />
          </OperatorSection>
        </>
      )}

      <CollapsibleDebug title="Debug: raw tenant JSON (API response)">
        <pre className="max-h-64 overflow-auto text-xs text-stone-700">{JSON.stringify(t, null, 2)}</pre>
      </CollapsibleDebug>
    </div>
  );
}
