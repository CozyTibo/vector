import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { MANAGER_ONBOARDING_STEPS } from "./managerOnboardingSteps";

type SessionDetail = {
  id: string;
  tenant_id: string;
  slack_team_id: string;
  slack_user_id: string;
  status: string;
  current_step: string;
  muted: boolean;
  answers_json: Record<string, unknown>;
  context_json: Record<string, unknown>;
  completed_at: string | null;
  error_code: string | null;
  error_detail: string | null;
};

type Msg = {
  id: string;
  direction: string;
  role: string;
  text: string;
  slack_ts: string | null;
  created_at: string | null;
};

type Artifact = {
  id: string;
  trigger: string;
  input_text: string;
  structured_output_json: Record<string, unknown> | null;
  confidence: number | null;
  model: string | null;
  error: string | null;
  created_at: string | null;
};

export default function AdminManagerOnboardingSessionPage() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const qc = useQueryClient();
  const [restartStep, setRestartStep] = useState<string>(MANAGER_ONBOARDING_STEPS[0]);
  const [mergeJson, setMergeJson] = useState("{}");
  const [actionErr, setActionErr] = useState<string | null>(null);

  const sessionQ = useQuery({
    queryKey: ["admin-mo-session", sessionId],
    queryFn: () => adminJson<SessionDetail>(`/admin/manager-onboarding/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
  });

  const messagesQ = useQuery({
    queryKey: ["admin-mo-messages", sessionId],
    queryFn: () => adminJson<{ items: Msg[] }>(`/admin/manager-onboarding/sessions/${sessionId}/messages`),
    enabled: Boolean(sessionId),
  });

  const artifactsQ = useQuery({
    queryKey: ["admin-mo-artifacts", sessionId],
    queryFn: () =>
      adminJson<{ items: Artifact[] }>(
        `/admin/manager-onboarding/sessions/${sessionId}/parse-artifacts`,
      ),
    enabled: Boolean(sessionId),
  });

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["admin-mo-session", sessionId] });
    void qc.invalidateQueries({ queryKey: ["admin-mo-messages", sessionId] });
    void qc.invalidateQueries({ queryKey: ["admin-mo-artifacts", sessionId] });
    void qc.invalidateQueries({ queryKey: ["admin-mo-sessions"] });
  };

  const runPost = async (path: string, body?: Record<string, unknown>) => {
    setActionErr(null);
    const headers: Record<string, string> = {};
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    const res = await adminFetch(`/admin/manager-onboarding/sessions/${sessionId}${path}`, {
      method: "POST",
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      throw new Error(await readErrorDetail(res));
    }
    return res.json() as Promise<unknown>;
  };

  const restartMut = useMutation({
    mutationFn: () => runPost("/restart-step", { step: restartStep }),
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  const completeMut = useMutation({
    mutationFn: () => runPost("/force-complete"),
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  const reviewMut = useMutation({
    mutationFn: () => runPost("/needs-review"),
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  const retryMut = useMutation({
    mutationFn: () => runPost("/retry-slack-prompt", {}),
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  const muteMut = useMutation({
    mutationFn: async (muted: boolean) => {
      setActionErr(null);
      await adminJson(`/admin/manager-onboarding/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ muted }),
      });
    },
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  const mergeMut = useMutation({
    mutationFn: async () => {
      setActionErr(null);
      let patch: Record<string, unknown>;
      try {
        patch = JSON.parse(mergeJson) as Record<string, unknown>;
      } catch {
        throw new Error("Answers patch must be valid JSON.");
      }
      await adminJson(`/admin/manager-onboarding/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers_patch: patch }),
      });
    },
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  const recomputeMut = useMutation({
    mutationFn: async () => {
      setActionErr(null);
      await adminJson(`/admin/manager-onboarding/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recompute_current_step: true }),
      });
    },
    onSuccess: () => invalidate(),
    onError: (e: Error) => setActionErr(e.message),
  });

  if (!sessionId) {
    return <p className="px-4 py-6 text-sm text-red-700">Missing session id.</p>;
  }
  if (sessionQ.isPending) {
    return <p className="px-4 py-6 text-sm text-stone-600">Loading…</p>;
  }
  if (sessionQ.isError) {
    return <p className="px-4 py-6 text-sm text-red-700">{(sessionQ.error as Error).message}</p>;
  }

  const s = sessionQ.data;
  const btn =
    "rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50";
  const danger = "rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-900 hover:bg-red-100 disabled:opacity-50";

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/admin/manager-onboarding" className="text-sm text-blue-700 underline">
            ← All sessions
          </Link>
          <h1 className="mt-2 text-lg font-semibold text-stone-900">Manager onboarding session</h1>
          <p className="mt-1 font-mono text-xs text-stone-600">{s.id}</p>
          <p className="mt-2 text-sm text-stone-600">
            Tenant{" "}
            <Link
              to={`/admin/tenants/${s.tenant_id}/manager-onboarding`}
              className="font-mono text-blue-700 underline"
            >
              {s.tenant_id}
            </Link>
            {" · "}
            Slack <span className="font-mono">{s.slack_user_id}</span>
          </p>
        </div>
      </div>

      {actionErr ? (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">{actionErr}</p>
      ) : null}

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">State</h2>
        <dl className="grid max-w-xl grid-cols-[auto_1fr] gap-2 text-sm">
          <dt className="text-stone-500">Status</dt>
          <dd>{s.status}</dd>
          <dt className="text-stone-500">Current step</dt>
          <dd className="font-mono text-xs">{s.current_step}</dd>
          <dt className="text-stone-500">Muted</dt>
          <dd>{s.muted ? "yes" : "no"}</dd>
          <dt className="text-stone-500">Completed</dt>
          <dd>{s.completed_at ? new Date(s.completed_at).toLocaleString() : "—"}</dd>
          <dt className="text-stone-500">Error</dt>
          <dd>{s.error_code ?? "—"}</dd>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className={btn}
            disabled={muteMut.isPending}
            onClick={() => muteMut.mutate(!s.muted)}
          >
            {s.muted ? "Unmute session" : "Mute session"}
          </button>
          <button type="button" className={btn} disabled={recomputeMut.isPending} onClick={() => recomputeMut.mutate()}>
            Recompute step from answers
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Operator actions</h2>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={restartStep}
              onChange={(e) => setRestartStep(e.target.value)}
            >
              {MANAGER_ONBOARDING_STEPS.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
            <button type="button" className={btn} disabled={restartMut.isPending} onClick={() => restartMut.mutate()}>
              Restart at step
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={danger} disabled={completeMut.isPending} onClick={() => completeMut.mutate()}>
              Force complete
            </button>
            <button type="button" className={btn} disabled={reviewMut.isPending} onClick={() => reviewMut.mutate()}>
              Mark needs review
            </button>
            <button type="button" className={btn} disabled={retryMut.isPending} onClick={() => retryMut.mutate()}>
              Retry Slack prompt
            </button>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-stone-600">Merge answers (JSON object)</label>
            <textarea
              className="mb-2 w-full min-h-[100px] rounded-md border border-stone-300 px-3 py-2 font-mono text-xs"
              value={mergeJson}
              onChange={(e) => setMergeJson(e.target.value)}
            />
            <button type="button" className={btn} disabled={mergeMut.isPending} onClick={() => mergeMut.mutate()}>
              PATCH merge
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">answers_json</h2>
        <pre className="max-h-64 overflow-auto rounded bg-stone-50 p-3 text-xs text-stone-800">
          {JSON.stringify(s.answers_json, null, 2)}
        </pre>
        <h3 className="mb-2 mt-4 text-xs font-semibold text-stone-700">context_json</h3>
        <pre className="max-h-48 overflow-auto rounded bg-stone-50 p-3 text-xs text-stone-800">
          {JSON.stringify(s.context_json, null, 2)}
        </pre>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Messages</h2>
        {messagesQ.isPending ? (
          <p className="text-sm text-stone-600">Loading…</p>
        ) : messagesQ.isError ? (
          <p className="text-sm text-red-700">{(messagesQ.error as Error).message}</p>
        ) : (
          <ul className="max-h-96 space-y-2 overflow-y-auto text-sm">
            {messagesQ.data.items.map((m) => (
              <li
                key={m.id}
                className={`rounded-md border px-3 py-2 ${
                  m.direction === "outbound" ? "border-blue-200 bg-blue-50/60" : "border-stone-200 bg-stone-50"
                }`}
              >
                <span className="text-xs text-stone-500">
                  {m.direction} · {m.role}
                  {m.created_at ? ` · ${new Date(m.created_at).toLocaleString()}` : ""}
                </span>
                <p className="mt-1 whitespace-pre-wrap text-stone-800">{m.text}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Parse artifacts</h2>
        {artifactsQ.isPending ? (
          <p className="text-sm text-stone-600">Loading…</p>
        ) : artifactsQ.isError ? (
          <p className="text-sm text-red-700">{(artifactsQ.error as Error).message}</p>
        ) : artifactsQ.data.items.length === 0 ? (
          <p className="text-sm text-stone-500">None</p>
        ) : (
          <ul className="space-y-3 text-sm">
            {artifactsQ.data.items.map((a) => (
              <li key={a.id} className="rounded-md border border-stone-200 p-3">
                <div className="text-xs text-stone-500">
                  {a.trigger}
                  {a.created_at ? ` · ${new Date(a.created_at).toLocaleString()}` : ""}
                  {a.model ? ` · ${a.model}` : ""}
                  {a.confidence != null ? ` · conf ${a.confidence}` : ""}
                </div>
                {a.error ? <p className="mt-1 text-xs text-red-700">{a.error}</p> : null}
                <p className="mt-2 whitespace-pre-wrap font-mono text-xs text-stone-700">{a.input_text}</p>
                {a.structured_output_json ? (
                  <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-50 p-2 text-xs">
                    {JSON.stringify(a.structured_output_json, null, 2)}
                  </pre>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
