import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

async function readErrorDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string | unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    /* ignore */
  }
  return `HTTP ${res.status}`;
}

type RawRecordResponse = {
  item: Record<string, unknown>;
};

/** Deep link: /debug/ingestion/raw/:recordId?connector=github&connection_id=UUID */
export default function RawIngestionDebugPage() {
  const { recordId = "" } = useParams<{ recordId: string }>();
  const [searchParams] = useSearchParams();
  const connector = searchParams.get("connector") ?? "github";
  const connectionId = searchParams.get("connection_id") ?? "";
  const apiBase = useMemo(() => import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ""), []);
  const idNum = Number.parseInt(recordId, 10);

  const rawQuery = useQuery({
    queryKey: ["debug-raw", apiBase, connector, connectionId, recordId],
    queryFn: async () => {
      const res = await fetch(
        `${apiBase}/debug/connectors/${encodeURIComponent(connector)}/connections/${encodeURIComponent(connectionId)}/raw-records/${encodeURIComponent(recordId)}`,
        { credentials: "include" },
      );
      if (res.status === 401) {
        throw new Error("Not signed in");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<RawRecordResponse>;
    },
    enabled: Boolean(connectionId && recordId && Number.isFinite(idNum)),
  });

  const backToProjections =
    connectionId !== ""
      ? `/debug/connectors/${encodeURIComponent(connector)}/${encodeURIComponent(connectionId)}/projections`
      : "/";

  return (
    <div className="app">
      <header className="header">
        <h1>Debug — raw ingestion record</h1>
        <p className="subtitle">
          <code className="cell-muted">{recordId}</code>
          {connectionId ? (
            <>
              {" "}
              / connection <code className="cell-muted">{connectionId}</code>
            </>
          ) : null}
        </p>
        <p className="meta">
          <Link to={backToProjections}>← Projections</Link>
          {" · "}
          <Link to="/github/ingestion">GitHub ingestion</Link>
          {" · "}
          <Link to="/">Dashboard</Link>
        </p>
      </header>

      {!connectionId ? (
        <section className="card">
          <p className="banner error">
            Missing <code>connection_id</code> query parameter. Open this page from a projection row
            link, or add{" "}
            <code>?connector=github&amp;connection_id=YOUR_UUID</code> to the URL.
          </p>
        </section>
      ) : null}

      {rawQuery.isError ? (
        <p className="banner error">{(rawQuery.error as Error).message}</p>
      ) : null}
      {rawQuery.isPending && connectionId ? (
        <p className="status loading">Loading…</p>
      ) : null}
      {rawQuery.data ? (
        <section className="card">
          <pre className="payload-preview" style={{ maxHeight: "85vh", overflow: "auto" }}>
            {JSON.stringify(rawQuery.data.item, null, 2)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}
