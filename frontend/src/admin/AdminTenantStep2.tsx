import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

/** Must match ``STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE`` in ``step2_step3_reset.py`` (case-sensitive). */
const STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE = "DELETE ALL STEP2 PROJECTION DATA";

type Conn = { id: string; provider: string; status: string; created_at: string };

const GITHUB_ENTITIES = ["repositories", "pull_requests", "commits", "issues", "users"] as const;
const LINEAR_ENTITIES = ["teams", "projects", "issues", "users", "issue_comments"] as const;

type GithubEntity = (typeof GITHUB_ENTITIES)[number];
type LinearEntity = (typeof LINEAR_ENTITIES)[number];

export default function AdminTenantStep2() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [vendor, setVendor] = useState<"github" | "linear">("github");
  const [githubEntity, setGithubEntity] = useState<GithubEntity>("repositories");
  const [linearEntity, setLinearEntity] = useState<LinearEntity>("teams");
  const [page, setPage] = useState(0);
  const limit = 50;

  const [resetOpen, setResetOpen] = useState(false);
  const [resetPhrase, setResetPhrase] = useState("");
  const [resetPending, setResetPending] = useState(false);
  const [resetErr, setResetErr] = useState<string | null>(null);
  const [resetOk, setResetOk] = useState<string | null>(null);
  const resetPhraseOk = resetPhrase === STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE;

  const runStep2Reset = async () => {
    if (!resetPhraseOk) return;
    setResetPending(true);
    setResetErr(null);
    setResetOk(null);
    try {
      const res = await adminFetch(`/admin/tenants/${tenantId}/projections/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE }),
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      const body = (await res.json()) as {
        deleted_github_projection_rows: number;
        deleted_linear_projection_rows: number;
        deleted_connector_projection_progress_rows: number;
      };
      setResetOk(
        `Removed GitHub projection rows: ${body.deleted_github_projection_rows}; Linear: ${body.deleted_linear_projection_rows}; projection progress: ${body.deleted_connector_projection_progress_rows}.`,
      );
      setResetOpen(false);
      setResetPhrase("");
      void qc.invalidateQueries({ queryKey: ["admin-projections", tenantId] });
    } catch (e) {
      setResetErr((e as Error).message);
    } finally {
      setResetPending(false);
    }
  };

  const conns = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  const githubConnId = useMemo(() => {
    const g = conns.data?.items.find((c) => c.provider === "github");
    return g?.id ?? "";
  }, [conns.data?.items]);

  const linearConnId = useMemo(() => {
    const g = conns.data?.items.find((c) => c.provider === "linear");
    return g?.id ?? "";
  }, [conns.data?.items]);

  useEffect(() => {
    if (!conns.data?.items) return;
    if (linearConnId && !githubConnId) {
      setVendor("linear");
    } else if (githubConnId && !linearConnId) {
      setVendor("github");
    }
  }, [conns.data?.items, githubConnId, linearConnId]);

  const activeConnId = vendor === "github" ? githubConnId : linearConnId;
  const entity = vendor === "github" ? githubEntity : linearEntity;

  const rows = useQuery({
    queryKey: ["admin-projections", tenantId, vendor, activeConnId, entity, page],
    queryFn: () =>
      adminJson<{ items: Record<string, unknown>[]; total: number }>(
        `/admin/tenants/${tenantId}/projections/${vendor}/${activeConnId}/rows?entity=${entity}&limit=${limit}&offset=${page * limit}`,
      ),
    enabled: Boolean(tenantId && activeConnId),
  });

  const resetStrip = (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50/50 px-3 py-2">
        <button
          type="button"
          className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-900 hover:bg-red-100 disabled:opacity-40"
          disabled={resetPending}
          onClick={() => {
            setResetOpen(true);
            setResetPhrase("");
            setResetErr(null);
            setResetOk(null);
          }}
        >
          Reset Step 2 projection data…
        </button>
        {resetOk ? <span className="text-sm text-emerald-800">{resetOk}</span> : null}
        {resetErr ? <span className="text-sm text-red-700">{resetErr}</span> : null}
      </div>
      {resetOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="step2-reset-title"
        >
          <div className="max-w-lg rounded-lg border border-stone-200 bg-white p-5 shadow-lg">
            <h2 id="step2-reset-title" className="text-lg font-semibold text-stone-900">
              Reset all Step 2 projection data for this tenant?
            </h2>
            <p className="mt-2 text-sm text-stone-700">
              This removes every <strong>GitHub</strong> and <strong>Linear</strong> projection row and
              all <strong>connector_projection_progress</strong> cursors for this workspace. Step 1
              raw envelopes and Step 3 canonical data are <strong>not</strong> deleted.
            </p>
            <p className="mt-3 text-sm font-medium text-stone-800">
              Type the phrase below exactly (case-sensitive) to enable reset:
            </p>
            <code className="mt-1 block rounded bg-stone-100 px-2 py-1.5 text-xs text-stone-800">
              {STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE}
            </code>
            <input
              type="text"
              className="mt-3 w-full rounded border border-stone-300 px-2 py-1.5 text-sm"
              placeholder="Type confirmation phrase…"
              value={resetPhrase}
              onChange={(e) => setResetPhrase(e.target.value)}
              autoComplete="off"
              autoFocus
            />
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm hover:bg-stone-50"
                disabled={resetPending}
                onClick={() => {
                  setResetOpen(false);
                  setResetPhrase("");
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded border border-red-600 bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-40"
                disabled={!resetPhraseOk || resetPending}
                onClick={() => void runStep2Reset()}
              >
                {resetPending ? "Resetting…" : "Reset Step 2 data"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );

  if (conns.isPending) {
    return (
      <div>
        {resetStrip}
        <p className="text-sm text-stone-600">Loading connections…</p>
      </div>
    );
  }
  if (conns.isError) {
    return (
      <div>
        {resetStrip}
        <p className="text-sm text-red-700">{(conns.error as Error).message}</p>
      </div>
    );
  }

  if (!githubConnId && !linearConnId) {
    return (
      <div>
        {resetStrip}
        <p className="text-sm text-stone-600">
          No GitHub or Linear connection for this tenant — connect a connector in the product UI first.
        </p>
      </div>
    );
  }

  const entityList = vendor === "github" ? GITHUB_ENTITIES : LINEAR_ENTITIES;
  const table = entityList.map((e) => (
    <button
      key={e}
      type="button"
      className={`rounded px-2 py-1 text-xs font-medium ${
        entity === e ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-800"
      }`}
      onClick={() => {
        if (vendor === "github") {
          setGithubEntity(e as GithubEntity);
        } else {
          setLinearEntity(e as LinearEntity);
        }
        setPage(0);
      }}
    >
      {e}
    </button>
  ));

  return (
    <div>
      {resetStrip}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm text-stone-600">Connector:</span>
        <button
          type="button"
          className={`rounded px-2 py-1 text-xs font-medium ${
            vendor === "github" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-800"
          } disabled:opacity-40`}
          disabled={!githubConnId}
          onClick={() => {
            setVendor("github");
            setPage(0);
          }}
        >
          GitHub
        </button>
        <button
          type="button"
          className={`rounded px-2 py-1 text-xs font-medium ${
            vendor === "linear" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-800"
          } disabled:opacity-40`}
          disabled={!linearConnId}
          onClick={() => {
            setVendor("linear");
            setPage(0);
          }}
        >
          Linear
        </button>
      </div>
      {activeConnId ? (
        <p className="mb-2 font-mono text-xs text-stone-600">connection_id: {activeConnId}</p>
      ) : (
        <p className="mb-2 text-sm text-amber-800">
          Connect {vendor === "github" ? "GitHub" : "Linear"} to browse projection rows for this
          connector.
        </p>
      )}
      <div className="mb-4 flex flex-wrap gap-2">{table}</div>
      {rows.isPending ? <p className="text-sm text-stone-600">Loading rows…</p> : null}
      {rows.isError ? (
        <p className="text-sm text-red-700">{(rows.error as Error).message}</p>
      ) : null}
      {rows.data && activeConnId ? (
        <>
          <div className="mb-2 flex gap-2 text-sm">
            <button
              type="button"
              className="rounded border border-stone-300 px-2 py-1 disabled:opacity-40"
              disabled={page <= 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Prev
            </button>
            <button
              type="button"
              className="rounded border border-stone-300 px-2 py-1 disabled:opacity-40"
              disabled={(page + 1) * limit >= rows.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
            <span className="text-stone-600">
              {rows.data.total} rows total — page {page + 1}
            </span>
          </div>
          <ProjectionTable items={rows.data.items} />
        </>
      ) : null}
    </div>
  );
}

function ProjectionTable({ items }: { items: Record<string, unknown>[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-stone-500">No rows</p>;
  }
  const keys = Object.keys(items[0] ?? {}).slice(0, 14);
  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
      <table className="data-table text-xs">
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((row, i) => (
            <tr key={i}>
              {keys.map((k) => (
                <td key={k} className="max-w-[12rem] truncate">
                  {formatCell(row[k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) {
    return "—";
  }
  if (typeof v === "object") {
    return JSON.stringify(v).slice(0, 80);
  }
  return String(v);
}
