import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { AdminSlackStyleThread, adminSlackRowsToChatMessages } from "./adminChatTranscript";
import {
  MANAGER_COLLECTED_STEPS,
  collectedAnswerStatus,
  managerStatusBusinessLabel,
  statusIndicatorClass,
  statusIndicatorEmoji,
} from "./managerOnboardingDisplay";
import { CollapsibleDebug, OperatorIntro, OperatorSection } from "./ui/OperatorSections";

function slackMapLookup(map: Record<string, string>, key: string | null | undefined): string | undefined {
  const t = (key ?? "").trim();
  if (!t) return undefined;
  const u = t.toUpperCase();
  return map[t] ?? map[u];
}

type Summary = {
  tenant_id: string;
  slack_vector_paused: boolean;
  session_count: number;
  managers_with_sessions?: number;
  managers_completed?: number;
  managers_in_progress?: number;
  managers_needs_attention?: number;
  invitation_count: number;
  sessions: {
    id: string;
    slack_user_id: string;
    slack_display_name?: string | null;
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

type SessionDetail = {
  id: string;
  tenant_id?: string;
  slack_team_id?: string;
  slack_user_id?: string;
  status?: string;
  current_step?: string;
  muted?: boolean;
  answers_json: Record<string, unknown>;
  context_json?: Record<string, unknown>;
  completed_at?: string | null;
  error_code?: string | null;
  error_detail?: string | null;
  slack_user_labels?: Record<string, string>;
  slack_channel_labels?: Record<string, string>;
  /** Present on POST …/admin-wipe-restart: whether the intro was posted to Slack. */
  slack?: { ok: boolean; error?: string };
};

type ParseArtifact = {
  id: string;
  trigger: string;
  input_text: string;
  structured_output_json: Record<string, unknown> | null;
  confidence: number | null;
  model: string | null;
  error: string | null;
  created_at: string | null;
};

type Msg = {
  id: string;
  direction: string;
  role: string;
  text: string;
  created_at: string | null;
  slack_ts?: string | null;
};

export default function AdminTenantManagerOnboarding() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

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

  const sum = summaryQ.data;

  useEffect(() => {
    const sessions = sum?.sessions ?? [];
    if (sessions.length === 0) {
      setSelectedSessionId(null);
      return;
    }
    setSelectedSessionId((prev) => {
      if (prev && sessions.some((x) => x.id === prev)) {
        return prev;
      }
      return sessions[0]!.id;
    });
  }, [sum?.sessions]);

  const sessionDetailQ = useQuery({
    queryKey: ["admin-mo-session", selectedSessionId],
    queryFn: () => adminJson<SessionDetail>(`/admin/manager-onboarding/sessions/${selectedSessionId}`),
    enabled: Boolean(tenantId && selectedSessionId && summaryQ.isSuccess),
  });

  const messagesQ = useQuery({
    queryKey: ["admin-mo-messages-preview", selectedSessionId],
    queryFn: () =>
      adminJson<{ items: Msg[] }>(`/admin/manager-onboarding/sessions/${selectedSessionId}/messages`),
    enabled: Boolean(selectedSessionId && summaryQ.isSuccess),
  });

  const artifactsQ = useQuery({
    queryKey: ["admin-mo-artifacts-tab", selectedSessionId],
    queryFn: () =>
      adminJson<{ items: ParseArtifact[] }>(
        `/admin/manager-onboarding/sessions/${selectedSessionId}/parse-artifacts`,
      ),
    enabled: Boolean(selectedSessionId && summaryQ.isSuccess),
  });

  const wipeMut = useMutation({
    mutationFn: async (sessionId: string) => {
      const res = await adminFetch(`/admin/manager-onboarding/sessions/${sessionId}/admin-wipe-restart`, {
        method: "POST",
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<SessionDetail>;
    },
    onSuccess: async (_, sessionId) => {
      void qc.invalidateQueries({ queryKey: ["admin-mo-tenant-summary", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-session", sessionId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-messages-preview", sessionId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-artifacts-tab", sessionId] });
      await qc.invalidateQueries({ queryKey: ["admin-mo-tenant-channels", tenantId] });
    },
  });

  const recomputeMut = useMutation({
    mutationFn: async (sessionId: string) => {
      const res = await adminFetch(`/admin/manager-onboarding/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recompute_current_step: true }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<SessionDetail>;
    },
    onSuccess: async (_, sessionId) => {
      void qc.invalidateQueries({ queryKey: ["admin-mo-session", sessionId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-messages-preview", sessionId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-artifacts-tab", sessionId] });
      void qc.invalidateQueries({ queryKey: ["admin-mo-tenant-summary", tenantId] });
    },
  });

  const titleSuffix = " · Managers · Vector";
  const summaryData = summaryQ.data;
  const selectedMeta =
    selectedSessionId && summaryData
      ? summaryData.sessions.find((x) => x.id === selectedSessionId)
      : undefined;
  const answers = sessionDetailQ.data?.answers_json ?? {};
  const userLabels = sessionDetailQ.data?.slack_user_labels ?? {};
  const channelLabels = sessionDetailQ.data?.slack_channel_labels ?? {};
  const answerLabels = useMemo(
    () => ({ users: userLabels, channels: channelLabels }),
    [userLabels, channelLabels],
  );

  const slackChatMessages = useMemo(
    () => adminSlackRowsToChatMessages(messagesQ.data?.items ?? []),
    [messagesQ.data?.items],
  );

  useEffect(() => {
    const fromLabels = selectedMeta?.slack_user_id
      ? slackMapLookup(userLabels, selectedMeta.slack_user_id)?.trim()
      : "";
    const head =
      selectedMeta?.slack_display_name?.trim() ||
      fromLabels ||
      (selectedMeta?.slack_user_id ? `Slack ${selectedMeta.slack_user_id}` : "Slack onboarding");
    document.title = `${head}${titleSuffix}`;
  }, [
    selectedMeta?.slack_display_name,
    selectedMeta?.slack_user_id,
    userLabels,
    selectedSessionId,
    titleSuffix,
  ]);

  useEffect(() => {
    return () => {
      document.title = "Vector";
    };
  }, []);

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (summaryQ.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (summaryQ.isError) {
    return <p className="text-sm text-red-700">{(summaryQ.error as Error).message}</p>;
  }

  const s = summaryQ.data;
  const btn =
    "rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50";

  const total = s.managers_with_sessions ?? s.session_count;
  const managerThreadLabel =
    selectedMeta?.slack_display_name?.trim() ||
    slackMapLookup(userLabels, selectedMeta?.slack_user_id) ||
    (selectedMeta?.slack_user_id ? selectedMeta.slack_user_id : "Manager");

  const sessionRow = sessionDetailQ.data;
  const contextJson = sessionRow?.context_json ?? {};

  return (
    <div className="space-y-8">
      <OperatorIntro title="Manager onboarding (Slack)">
        Each manager completes a private Slack conversation with Vector: team scope, people,
        channels, and reporting. Use this page to see rollout numbers, then review what each person
        already shared and the full DM timeline. Technical session fields and raw JSON live in the
        debug sections under each manager tab.
      </OperatorIntro>

      <OperatorSection
        title="Rollout overview"
        description="Headline counts for this company. One row in the system = one manager in a Slack DM thread."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">
              In Slack onboarding
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-stone-900">{total}</p>
            <p className="mt-1 text-xs text-stone-600">Managers with a live DM thread</p>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">Finished</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-800">
              {s.managers_completed ?? 0}
            </p>
            <p className="mt-1 text-xs text-stone-600">Completed the full flow</p>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">
              In progress
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-stone-900">
              {s.managers_in_progress ?? 0}
            </p>
            <p className="mt-1 text-xs text-stone-600">Still answering in Slack</p>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">
              Needs follow-up
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-900">
              {s.managers_needs_attention ?? 0}
            </p>
            <p className="mt-1 text-xs text-stone-600">System states, not idle time</p>
          </div>
        </div>
        <p className="mt-4 rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-xs text-stone-600">
          <span className="font-medium text-stone-800">How these buckets work:</span>{" "}
          <strong>In progress</strong> means the session is <em>active</em> or <em>waiting on the manager</em>{" "}
          (the conversation is still running). <strong>Needs follow-up</strong> means the row was marked{" "}
          <em>needs review</em>, <em>paused</em>, or <em>failed</em> — that comes from workflow rules or
          operator flags, <strong>not</strong> from “how long since they replied”. To pause all Slack for
          this company, use the <strong>Workspace</strong> tab.
        </p>
        {s.invitation_count > 0 ? (
          <p className="mt-3 text-sm text-stone-600">
            <span className="font-medium text-stone-800">{s.invitation_count}</span> invitation
            {s.invitation_count === 1 ? "" : "s"} outstanding — invited in the product but no Slack
            thread yet.
          </p>
        ) : null}
      </OperatorSection>

      {s.sessions.length === 0 ? (
        <OperatorSection
          title="Managers"
          description="No Slack threads yet for this company."
        >
          <p className="text-sm text-stone-600">
            When the first manager starts after website handoff, they will appear here as a tab.
          </p>
        </OperatorSection>
      ) : (
        <OperatorSection
          title="By manager"
          description="Pick a manager to see captured answers in flow order, then the DM transcript."
        >
          <div
            role="tablist"
            aria-label="Managers in Slack onboarding"
            className="flex flex-wrap gap-2 border-b border-stone-200 pb-2"
          >
            {s.sessions.map((sess, idx) => {
              const active = sess.id === selectedSessionId;
              return (
                <button
                  key={sess.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={[
                    "rounded-t-md border px-3 py-2 text-left text-sm transition",
                    active
                      ? "border-stone-300 border-b-white bg-white font-semibold text-stone-900"
                      : "border-transparent bg-stone-50/80 text-stone-600 hover:bg-stone-100 hover:text-stone-900",
                  ].join(" ")}
                  onClick={() => setSelectedSessionId(sess.id)}
                >
                  <span className="block text-sm font-semibold text-stone-900">
                    {(sess.id === selectedSessionId
                      ? slackMapLookup(userLabels, sess.slack_user_id)?.trim()
                      : "") ||
                      sess.slack_display_name?.trim() ||
                      (sess.slack_user_id ? `Slack ${sess.slack_user_id}` : `Manager ${idx + 1}`)}
                  </span>
                  {sess.slack_display_name?.trim() ||
                  (sess.id === selectedSessionId && slackMapLookup(userLabels, sess.slack_user_id)?.trim()) ? (
                    <span className="block font-mono text-[10px] text-stone-400">{sess.slack_user_id}</span>
                  ) : null}
                  <span className="block text-[11px] font-normal text-stone-500">
                    {managerStatusBusinessLabel(sess.status)} · {sess.current_step}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="mt-6 space-y-8 border border-t-0 border-stone-200 bg-white p-4 sm:p-6">
            {selectedMeta ? (
              <div className="text-xs text-stone-600">
                <p>
                  <span className="font-medium text-stone-700">Slack:</span>{" "}
                  <span className="font-semibold text-stone-900">{managerThreadLabel}</span>
                  {selectedMeta.slack_user_id ? (
                    <span className="ml-2 font-mono text-stone-500">({selectedMeta.slack_user_id})</span>
                  ) : null}
                </p>
                {selectedMeta.muted ? (
                  <p className="mt-1 text-amber-800">Notifications muted for this thread.</p>
                ) : null}
              </div>
            ) : null}

            <div>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-stone-900">Collected answers</h3>
                  <p className="mt-1 text-xs text-stone-600">
                    Same order as the live flow. Icons: answered (green), not yet (gray), needs attention
                    (red).
                  </p>
                </div>
                {selectedSessionId ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className={btn}
                      disabled={recomputeMut.isPending || sessionDetailQ.isPending}
                      onClick={() => recomputeMut.mutate(selectedSessionId)}
                    >
                      {recomputeMut.isPending ? "Working…" : "Recompute step & resume"}
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-900 hover:bg-red-100 disabled:opacity-50"
                      disabled={wipeMut.isPending}
                      onClick={() => {
                        if (
                          !window.confirm(
                            "Clear all answers and DM history for this manager, restart from the first question, and send the opening Slack message again? This cannot be undone.",
                          )
                        ) {
                          return;
                        }
                        wipeMut.mutate(selectedSessionId);
                      }}
                    >
                      {wipeMut.isPending ? "Clearing…" : "Clear & restart"}
                    </button>
                  </div>
                ) : null}
              </div>
              {recomputeMut.isError ? (
                <p className="mt-2 text-sm text-red-700">{(recomputeMut.error as Error).message}</p>
              ) : null}
              {wipeMut.isError ? (
                <p className="mt-2 text-sm text-red-700">{(wipeMut.error as Error).message}</p>
              ) : null}
              {wipeMut.isSuccess &&
              wipeMut.data?.id === selectedSessionId &&
              wipeMut.data?.slack &&
              !wipeMut.data.slack.ok ? (
                <p className="mt-2 text-sm text-amber-800">
                  Session was cleared, but the first Slack message was not sent:{" "}
                  {wipeMut.data.slack.error ?? "unknown error"}. Check Slack connection and workspace
                  pause settings, then use &quot;Recompute step & resume&quot; if needed.
                </p>
              ) : null}
              {sessionDetailQ.isPending ? (
                <p className="mt-4 text-sm text-stone-500">Loading answers…</p>
              ) : sessionDetailQ.isError ? (
                <p className="mt-4 text-sm text-red-700">{(sessionDetailQ.error as Error).message}</p>
              ) : (
                <ol className="mt-4 space-y-4">
                  {MANAGER_COLLECTED_STEPS.map((row) => {
                    const hasVal = row.hasValue(answers);
                    const ast = collectedAnswerStatus({
                      sessionStatus: selectedMeta?.status ?? "",
                      currentStep: selectedMeta?.current_step ?? "",
                      backendStep: row.backendStep,
                      hasValue: hasVal,
                    });
                    return (
                      <li
                        key={row.order}
                        className="rounded-lg border border-stone-200 bg-stone-50/60 px-4 py-3"
                      >
                        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                          <span
                            className={`text-base leading-none ${statusIndicatorClass(ast)}`}
                            title={ast}
                            aria-hidden
                          >
                            {statusIndicatorEmoji(ast)}
                          </span>
                          <span className="text-xs font-semibold tabular-nums text-stone-400">
                            {row.order}.
                          </span>
                          <span className="text-sm font-semibold text-stone-900">{row.title}</span>
                        </div>
                        <p className="mt-0.5 pl-8 text-xs text-stone-500">{row.hint}</p>
                        <p className="mt-2 pl-8 whitespace-pre-wrap text-sm text-stone-800">
                          {row.formatDisplay(answers, answerLabels)}
                        </p>
                      </li>
                    );
                  })}
                </ol>
              )}
            </div>

            <div>
              <h3 className="text-sm font-semibold text-stone-900">Slack conversation</h3>
              <p className="mt-1 text-xs text-stone-600">
                Oldest at the top, newest at the bottom — same timeline as in Slack (Vector left,
                manager right).
              </p>
              {!selectedSessionId ? null : messagesQ.isPending ? (
                <p className="mt-4 text-sm text-stone-500">Loading messages…</p>
              ) : messagesQ.isError ? (
                <p className="mt-4 text-sm text-red-700">{(messagesQ.error as Error).message}</p>
              ) : (
                <div className="mt-4">
                  <AdminSlackStyleThread messages={slackChatMessages} managerLabel={managerThreadLabel} />
                </div>
              )}
            </div>

            {selectedSessionId && sessionRow ? (
              <div className="space-y-4 border-t border-stone-200 pt-6">
                <CollapsibleDebug title="Debug: session state & raw JSON">
                  <p className="mb-3 text-xs text-stone-500">
                    Session id (internal): <span className="font-mono text-stone-700">{sessionRow.id}</span>
                  </p>
                  <dl className="mb-4 grid max-w-xl grid-cols-[auto_1fr] gap-2 text-sm">
                    <dt className="text-stone-500">Status</dt>
                    <dd>{sessionRow.status ?? "—"}</dd>
                    <dt className="text-stone-500">Current step</dt>
                    <dd>{sessionRow.current_step ?? "—"}</dd>
                    <dt className="text-stone-500">Muted</dt>
                    <dd>{sessionRow.muted ? "yes" : "no"}</dd>
                    <dt className="text-stone-500">Completed</dt>
                    <dd>
                      {sessionRow.completed_at
                        ? new Date(sessionRow.completed_at).toLocaleString()
                        : "—"}
                    </dd>
                    <dt className="text-stone-500">Error code</dt>
                    <dd>{sessionRow.error_code ?? "—"}</dd>
                    {sessionRow.error_detail ? (
                      <>
                        <dt className="text-stone-500">Error detail</dt>
                        <dd className="text-red-800">{sessionRow.error_detail}</dd>
                      </>
                    ) : null}
                  </dl>
                  <h3 className="mb-2 text-xs font-semibold text-stone-700">answers_json</h3>
                  <pre className="max-h-64 overflow-auto rounded bg-stone-50 p-3 text-xs text-stone-800">
                    {JSON.stringify(sessionRow.answers_json ?? {}, null, 2)}
                  </pre>
                  <h3 className="mb-2 mt-4 text-xs font-semibold text-stone-700">context_json</h3>
                  <pre className="max-h-48 overflow-auto rounded bg-stone-50 p-3 text-xs text-stone-800">
                    {JSON.stringify(contextJson, null, 2)}
                  </pre>
                </CollapsibleDebug>

                <CollapsibleDebug title="Debug: parse artifacts">
                  {artifactsQ.isPending ? (
                    <p className="text-sm text-stone-600">Loading…</p>
                  ) : artifactsQ.isError ? (
                    <p className="text-sm text-red-700">{(artifactsQ.error as Error).message}</p>
                  ) : (artifactsQ.data?.items ?? []).length === 0 ? (
                    <p className="text-sm text-stone-500">None</p>
                  ) : (
                    <ul className="space-y-3 text-sm">
                      {(artifactsQ.data?.items ?? []).map((a) => (
                        <li key={a.id} className="rounded-md border border-stone-200 p-3">
                          <div className="text-xs text-stone-500">
                            {a.trigger}
                            {a.created_at ? ` · ${new Date(a.created_at).toLocaleString()}` : ""}
                            {a.model ? ` · ${a.model}` : ""}
                            {a.confidence != null ? ` · conf ${a.confidence}` : ""}
                          </div>
                          {a.error ? <p className="mt-1 text-xs text-red-700">{a.error}</p> : null}
                          <p className="mt-2 whitespace-pre-wrap font-mono text-xs text-stone-700">
                            {a.input_text}
                          </p>
                          {a.structured_output_json ? (
                            <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-50 p-2 text-xs">
                              {JSON.stringify(a.structured_output_json, null, 2)}
                            </pre>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </CollapsibleDebug>
              </div>
            ) : null}
          </div>
        </OperatorSection>
      )}

      <CollapsibleDebug title="Debug: channel observations table">
        {channelsQ.isPending ? (
          <p className="text-sm text-stone-600">Loading channels…</p>
        ) : channelsQ.isError ? (
          <p className="text-sm text-red-700">{(channelsQ.error as Error).message}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table text-sm">
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
                      <td className="font-mono text-xs text-stone-600" title={c.session_id}>
                        {c.session_id.slice(0, 8)}…
                      </td>
                      <td>{c.access_status}</td>
                      <td>{c.bot_is_member ? "yes" : "no"}</td>
                      <td className="max-w-xs truncate text-xs text-red-700">
                        {c.validation_error ?? "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </CollapsibleDebug>
    </div>
  );
}
