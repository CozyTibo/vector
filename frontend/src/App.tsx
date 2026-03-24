import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

type MeResponse = {
  user_id: string;
  email: string;
  full_name: string | null;
  tenant_id: string;
  company_name: string;
  tenant_slug: string;
  role: string;
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
  }, []);

  const health = useQuery({
    queryKey: ["health", "live", apiBase],
    queryFn: () => fetchHealthLive(apiBase),
  });

  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
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
