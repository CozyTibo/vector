import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

type MeResponse = {
  user_id: string;
  email: string;
  full_name: string | null;
  tenant_id: string;
  company_name: string;
  tenant_slug: string;
  role: string;
};

type GithubConnectorDetails = {
  installation_id: number | null;
  account_login: string | null;
  account_type: string | null;
};

type GithubConnectorStatusItem = {
  provider: "github";
  display_name: string;
  connector_configured: boolean;
  connected: boolean;
  details: GithubConnectorDetails | null;
};

type LinearConnectorDetails = {
  organization_id: string | null;
  organization_name: string | null;
};

type LinearConnectorStatusItem = {
  provider: "linear";
  display_name: string;
  connector_configured: boolean;
  connected: boolean;
  details: LinearConnectorDetails | null;
};

type ConnectorStatusItem = GithubConnectorStatusItem | LinearConnectorStatusItem;

type ConnectorsResponse = {
  items: ConnectorStatusItem[];
};

type GithubSyncResponse = {
  run_id: string;
  status: string;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
};

async function fetchHealthLive(base: string): Promise<{ status: string }> {
  const res = await fetch(`${base}/health/live`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<{ status: string }>;
}

async function fetchMe(base: string): Promise<MeResponse | null> {
  const res = await fetch(`${base}/me`, { credentials: "include" });
  if (res.status === 401) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<MeResponse>;
}

async function fetchConnectors(base: string): Promise<ConnectorsResponse> {
  const res = await fetch(`${base}/connectors`, { credentials: "include" });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<ConnectorsResponse>;
}

function githubConnectorRow(
  data: ConnectorsResponse | undefined,
): GithubConnectorStatusItem | undefined {
  const row = data?.items.find((i) => i.provider === "github");
  return row?.provider === "github" ? row : undefined;
}

function linearConnectorRow(
  data: ConnectorsResponse | undefined,
): LinearConnectorStatusItem | undefined {
  const row = data?.items.find((i) => i.provider === "linear");
  return row?.provider === "linear" ? row : undefined;
}

async function disconnectGithub(base: string): Promise<void> {
  const res = await fetch(`${base}/connectors/github`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(await readErrorDetail(res));
  }
}

async function disconnectLinear(base: string): Promise<void> {
  const res = await fetch(`${base}/connectors/linear`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(await readErrorDetail(res));
  }
}

async function syncGithub(base: string): Promise<GithubSyncResponse> {
  const res = await fetch(`${base}/connectors/github/sync`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<GithubSyncResponse>;
}

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

export default function App() {
  const apiBase = useMemo(
    () => import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ""),
    [],
  );
  const queryClient = useQueryClient();
  const [oauthNotice, setOauthNotice] = useState<string | null>(null);
  const [localNotice, setLocalNotice] = useState<string | null>(null);
  const [githubNotice, setGithubNotice] = useState<string | null>(null);
  const [githubSyncMessage, setGithubSyncMessage] = useState<string | null>(null);
  const [linearNotice, setLinearNotice] = useState<string | null>(null);

  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regName, setRegName] = useState("");
  const [regCompany, setRegCompany] = useState("");
  const [logEmail, setLogEmail] = useState("");
  const [logPassword, setLogPassword] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get("oauth_error");
    if (err === "state") {
      setOauthNotice("Sign-in failed (invalid or expired state). Try again.");
    } else if (err === "token") {
      setOauthNotice("Sign-in failed (could not validate account with Google).");
    } else if (params.get("oauth_ok") === "1") {
      setOauthNotice(null);
    }
    if (err || params.get("oauth_ok")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
    const gh = params.get("github_connected");
    const ghErr = params.get("github_error");
    const lin = params.get("linear_connected");
    const linErr = params.get("linear_error");
    if (gh === "1") {
      setGithubNotice(null);
      void queryClient.invalidateQueries({ queryKey: ["connectors", apiBase] });
    } else if (ghErr === "state") {
      setGithubNotice("GitHub connect failed (invalid or expired state). Try again.");
    } else if (ghErr === "oauth") {
      setGithubNotice("GitHub OAuth failed (could not exchange code). Check app credentials.");
    } else if (ghErr === "api") {
      setGithubNotice("GitHub API error while reading installation. Check app private key / id.");
    } else if (ghErr === "conflict") {
      setGithubNotice(
        "This GitHub installation is already linked to another Vector workspace.",
      );
    } else if (ghErr === "no_installation") {
      setGithubNotice("GitHub did not return installation_id. Try install + user OAuth again.");
    } else if (ghErr === "forbidden") {
      setGithubNotice("Session not valid for GitHub callback.");
    } else if (ghErr === "config") {
      setGithubNotice("GitHub connector is not configured on the server.");
    } else if (ghErr === "server") {
      setGithubNotice(
        "GitHub connect failed unexpectedly. Check API logs and .env (PEM, client secret).",
      );
    }
    if (lin === "1") {
      setLinearNotice(null);
      void queryClient.invalidateQueries({ queryKey: ["connectors", apiBase] });
    } else if (linErr === "state") {
      setLinearNotice("Linear connect failed (invalid or expired state). Try again.");
    } else if (linErr === "oauth") {
      setLinearNotice(
        "Linear OAuth failed. Check LINEAR_CLIENT_* and that the redirect URI matches Linear’s app settings.",
      );
    } else if (linErr === "forbidden") {
      setLinearNotice("Linear callback: user is not a member of this tenant.");
    } else if (linErr === "config") {
      setLinearNotice("Linear connector is not configured on the server.");
    } else if (linErr === "server") {
      setLinearNotice("Linear connect failed unexpectedly. Check API logs.");
    }
    if (gh || ghErr || lin || linErr) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [apiBase, queryClient]);

  const health = useQuery({
    queryKey: ["health", "live", apiBase],
    queryFn: () => fetchHealthLive(apiBase),
  });

  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });

  const connectors = useQuery({
    queryKey: ["connectors", apiBase],
    queryFn: () => fetchConnectors(apiBase),
    enabled: Boolean(me.data),
  });

  const githubRow = githubConnectorRow(connectors.data);
  const linearRow = linearConnectorRow(connectors.data);

  const githubDisconnect = useMutation({
    mutationFn: () => disconnectGithub(apiBase),
    onSuccess: () => {
      setGithubNotice(null);
      setGithubSyncMessage(null);
      void queryClient.invalidateQueries({ queryKey: ["connectors", apiBase] });
    },
    onError: (e: Error) => {
      setGithubNotice(e.message);
    },
  });

  const githubSync = useMutation({
    mutationFn: () => syncGithub(apiBase),
    onSuccess: (data) => {
      setGithubNotice(null);
      const rows =
        data.stats && typeof data.stats.records_written === "number"
          ? String(data.stats.records_written)
          : null;
      setGithubSyncMessage(
        `Ingestion ${data.status} — run ${data.run_id}` +
          (rows !== null ? ` — ${rows} rows written (this run).` : "."),
      );
      void queryClient.invalidateQueries({ queryKey: ["github-ingestion-runs", apiBase] });
    },
    onError: (e: Error) => {
      setGithubSyncMessage(null);
      setGithubNotice(e.message);
    },
  });

  const linearDisconnect = useMutation({
    mutationFn: () => disconnectLinear(apiBase),
    onSuccess: () => {
      setLinearNotice(null);
      void queryClient.invalidateQueries({ queryKey: ["connectors", apiBase] });
    },
    onError: (e: Error) => {
      setLinearNotice(e.message);
    },
  });

  const registerPw = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: regEmail,
          password: regPassword,
          full_name: regName.trim() || null,
          company_name: regCompany.trim() || null,
        }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: () => {
      setLocalNotice(null);
      void queryClient.invalidateQueries({ queryKey: ["me", apiBase] });
    },
    onError: (e: Error) => {
      setLocalNotice(e.message);
    },
  });

  const loginPw = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: logEmail,
          password: logPassword,
        }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: () => {
      setLocalNotice(null);
      void queryClient.invalidateQueries({ queryKey: ["me", apiBase] });
    },
    onError: (e: Error) => {
      setLocalNotice(e.message);
    },
  });

  const logout = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok && res.status !== 204) {
        throw new Error(`HTTP ${res.status}`);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["me", apiBase] });
    },
  });

  return (
    <div className="app">
      <header className="header">
        <h1>Vector</h1>
        <p className="subtitle">Admin harness — API + session</p>
      </header>

      {oauthNotice ? <p className="banner error">{oauthNotice}</p> : null}
      {localNotice ? <p className="banner error">{localNotice}</p> : null}
      {githubNotice ? <p className="banner error">{githubNotice}</p> : null}
      {githubSyncMessage ? <p className="banner ok">{githubSyncMessage}</p> : null}
      {linearNotice ? <p className="banner error">{linearNotice}</p> : null}

      <section className="card">
        <h2>Backend health</h2>
        <p className="meta">
          API: <code>{apiBase}</code>
        </p>
        {health.isPending ? (
          <p className="status loading">Checking…</p>
        ) : health.isError ? (
          <p className="status error">
            Cannot reach backend:{" "}
            {health.error instanceof Error ? health.error.message : "Unknown error"}
          </p>
        ) : (
          <p className="status ok">
            Connected — <code>/health/live</code>{" "}
            <code>{JSON.stringify(health.data)}</code>
          </p>
        )}
      </section>

      <section className="card">
        <h2>Session / tenant</h2>
        <p className="meta">Product auth uses an HTTP-only cookie on the API origin.</p>
        {me.isPending ? (
          <p className="status loading">Loading session…</p>
        ) : me.isError ? (
          <p className="status error">Failed to load /me</p>
        ) : me.data ? (
          <div>
            <p className="status ok">
              Signed in as <code>{me.data.email}</code> ({me.data.role} @{" "}
              <code>{me.data.tenant_slug}</code>)
            </p>
            <p className="meta">
              {me.data.company_name} — tenant <code>{me.data.tenant_id}</code>
            </p>
            <button type="button" className="btn secondary" onClick={() => logout.mutate()}>
              Sign out
            </button>
            <section className="card nested">
              <h3>GitHub</h3>
              <p className="meta">
                Connect your GitHub org or account, then run a poll sync to append raw ingestion rows
                (repos, PRs, issues, commits).
              </p>
              {connectors.isPending ? (
                <p className="status loading">Loading connectors…</p>
              ) : connectors.isError ? (
                <p className="status error">Could not load connectors.</p>
              ) : !githubRow ? (
                <p className="status error">GitHub connector not listed by API.</p>
              ) : githubRow.connector_configured === false ? (
                <p className="status loading">
                  GitHub App env is not set on the API (
                  <code>GITHUB_APP_*</code> / <code>GITHUB_CLIENT_*</code>).
                </p>
              ) : githubRow?.connected && githubRow.details ? (
                <div>
                  <p className="status ok">
                    Connected as{" "}
                    <code>
                      {githubRow.details.account_login} ({githubRow.details.account_type})
                    </code>{" "}
                    — installation <code>{String(githubRow.details.installation_id)}</code>
                  </p>
                  <p className="meta">
                    Disconnect stops Vector from using this installation. The GitHub App may
                    still be installed on the org until someone removes it in GitHub settings.
                  </p>
                  <p className="meta">
                    <Link to="/github/ingestion">Browse synced raw rows by run →</Link>
                  </p>
                  <div className="btn-row">
                    <button
                      type="button"
                      className="btn"
                      disabled={githubSync.isPending || githubDisconnect.isPending}
                      onClick={() => githubSync.mutate()}
                    >
                      {githubSync.isPending ? "Syncing…" : "Sync from GitHub"}
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={githubDisconnect.isPending || githubSync.isPending}
                      onClick={() => githubDisconnect.mutate()}
                    >
                      Disconnect GitHub
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="status loading">Not connected.</p>
                  <a className="btn" href={`${apiBase}/connectors/github/install`}>
                    Connect GitHub
                  </a>
                </div>
              )}
            </section>
            <section className="card nested">
              <h3>Linear</h3>
              <p className="meta">OAuth (read scope). Connect your Linear workspace.</p>
              {connectors.isPending ? (
                <p className="status loading">Loading connectors…</p>
              ) : connectors.isError ? (
                <p className="status error">Could not load connectors.</p>
              ) : !linearRow ? (
                <p className="status error">Linear connector not listed by API.</p>
              ) : linearRow.connector_configured === false ? (
                <p className="status loading">
                  Linear OAuth env is not set on the API (<code>LINEAR_CLIENT_ID</code>,{" "}
                  <code>LINEAR_CLIENT_SECRET</code>
                  ).
                </p>
              ) : linearRow.connected && linearRow.details ? (
                <div>
                  <p className="status ok">
                    Connected —{" "}
                    <code>
                      {linearRow.details.organization_name ?? linearRow.details.organization_id ?? "workspace"}
                    </code>
                  </p>
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={linearDisconnect.isPending}
                    onClick={() => linearDisconnect.mutate()}
                  >
                    Disconnect Linear
                  </button>
                </div>
              ) : (
                <div>
                  <p className="status loading">Not connected.</p>
                  <a className="btn" href={`${apiBase}/connectors/linear/install`}>
                    Connect Linear
                  </a>
                </div>
              )}
            </section>
          </div>
        ) : (
          <div className="signin-options">
            <p className="status loading">Not signed in.</p>
            <a className="btn" href={`${apiBase}/auth/google/start`}>
              Sign in with Google
            </a>
            <p className="hint">
              Or use email + password (min 8 characters).{" "}
              <code>make seed-basic-tenant</code> creates <code>dev@vector.local</code> /{" "}
              <code>changeme</code> if configured.
            </p>

            <div className="form-grid">
              <h3 className="form-title">Register</h3>
              <label className="field">
                Email
                <input
                  type="email"
                  autoComplete="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                />
              </label>
              <label className="field">
                Password
                <input
                  type="password"
                  autoComplete="new-password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                />
              </label>
              <label className="field">
                Full name <span className="optional">optional</span>
                <input
                  type="text"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                />
              </label>
              <label className="field">
                Company name <span className="optional">optional</span>
                <input
                  type="text"
                  value={regCompany}
                  onChange={(e) => setRegCompany(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn secondary"
                disabled={registerPw.isPending}
                onClick={() => registerPw.mutate()}
              >
                Create account
              </button>
            </div>

            <div className="form-grid">
              <h3 className="form-title">Log in</h3>
              <label className="field">
                Email
                <input
                  type="email"
                  autoComplete="email"
                  value={logEmail}
                  onChange={(e) => setLogEmail(e.target.value)}
                />
              </label>
              <label className="field">
                Password
                <input
                  type="password"
                  autoComplete="current-password"
                  value={logPassword}
                  onChange={(e) => setLogPassword(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn secondary"
                disabled={loginPw.isPending}
                onClick={() => loginPw.mutate()}
              >
                Log in
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
