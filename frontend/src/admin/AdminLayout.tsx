import { useState } from "react";
import { Link, Outlet } from "react-router-dom";

import { getApiBase, readErrorDetail } from "../lib/canonicalApi";
import { getAdminPassword, setAdminPassword } from "../lib/adminCredentials";

function AdminTopNav() {
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center px-4 py-3">
        <Link to="/admin" className="text-sm font-semibold text-red-800 no-underline">
          Vector Admin
        </Link>
      </div>
    </header>
  );
}

export default function AdminLayout() {
  const apiBase = getApiBase();
  const [authed, setAuthed] = useState(() => Boolean(getAdminPassword()));

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setChecking(true);
    try {
      const res = await fetch(`${apiBase}/admin/tenants`, {
        headers: {
          Authorization: `Basic ${btoa(`admin:${password}`)}`,
        },
      });
      if (res.status === 401) {
        setError("Invalid password.");
        return;
      }
      if (res.status === 503) {
        setError(await readErrorDetail(res));
        return;
      }
      if (!res.ok) {
        setError(await readErrorDetail(res));
        return;
      }
      setAdminPassword(password);
      setAuthed(true);
    } finally {
      setChecking(false);
    }
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-stone-100 px-4 py-16">
        <div className="mx-auto max-w-sm rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
          <h1 className="mb-1 text-lg font-semibold text-stone-900">Admin sign-in</h1>
          <p className="mb-4 text-sm text-stone-600">HTTP Basic — password from ADMIN_PASSWORD.</p>
          {error ? (
            <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
          ) : null}
          <form onSubmit={submit}>
            <label className="mb-3 block text-sm text-stone-700">
              Password
              <input
                type="password"
                autoComplete="current-password"
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={checking}
              className="w-full rounded-lg bg-red-900 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {checking ? "Checking…" : "Continue"}
            </button>
          </form>
          <p className="mt-4 text-center text-sm">
            <Link to="/" className="text-stone-600 underline">
              ← Product home
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <AdminTopNav />
      <Outlet />
    </div>
  );
}
