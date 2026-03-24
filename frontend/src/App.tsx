import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

async function fetchHealthLive(): Promise<{ status: string }> {
  const base = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, "");
  const res = await fetch(`${base}/health/live`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<{ status: string }>;
}

export default function App() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_BASE_URL, []);

  const health = useQuery({
    queryKey: ["health", "live", apiBase],
    queryFn: fetchHealthLive,
  });

  return (
    <div className="app">
      <header className="header">
        <h1>Vector</h1>
        <p className="subtitle">Admin / flow harness — backend connectivity</p>
      </header>

      <section className="card">
        <h2>Backend health</h2>
        <p className="meta">
          API: <code>{apiBase}</code>
        </p>

        {health.isPending ? (
          <p className="status loading">Checking…</p>
        ) : health.isError ? (
          <p className="status error">
            Cannot reach backend: {health.error instanceof Error ? health.error.message : "Unknown error"}
          </p>
        ) : (
          <p className="status ok">
            Connected — <code>/health/live</code> returned{" "}
            <code>{JSON.stringify(health.data)}</code>
          </p>
        )}
      </section>
    </div>
  );
}
