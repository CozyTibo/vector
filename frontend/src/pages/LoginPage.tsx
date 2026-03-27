import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import { readErrorDetail } from "../lib/canonicalApi";
import { fetchMe, productApiBase } from "../lib/meApi";

export default function LoginPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const from = loc.state?.from ?? "/app";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const already = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });

  const login = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: async () => {
      setNotice(null);
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate(from, { replace: true });
    },
    onError: (e: Error) => {
      setNotice(e.message);
    },
  });

  if (already.data) {
    return <Navigate to="/app" replace />;
  }

  return (
    <MarketingLayout>
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-md flex-col justify-center px-5 py-12 sm:px-8">
        <div className="rounded-3xl border border-zinc-200/80 bg-white/85 p-8 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.12),inset_0_0_0_1px_rgba(139,92,246,0.06)] backdrop-blur-2xl sm:p-9">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900">Sign in</h1>
          <p className="mt-2 text-sm text-zinc-600">
            New here?{" "}
            <Link to="/signup" className="font-medium text-teal-600 no-underline hover:text-teal-700">
              Create an account
            </Link>
          </p>
          {notice ? (
            <p className="mt-5 rounded-xl border border-rose-200/80 bg-rose-50 px-4 py-3 text-sm text-rose-900">
              {notice}
            </p>
          ) : null}
          <label className="mt-6 block text-sm font-medium text-zinc-700">
            Email
            <input
              type="email"
              autoComplete="email"
              className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50/80 px-4 py-3 text-zinc-900 outline-none placeholder:text-zinc-400 focus:border-teal-400/80 focus:bg-white focus:shadow-[0_0_0_3px_rgba(45,212,191,0.18)]"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="mt-4 block text-sm font-medium text-zinc-700">
            Password
            <input
              type="password"
              autoComplete="current-password"
              className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50/80 px-4 py-3 text-zinc-900 outline-none placeholder:text-zinc-400 focus:border-teal-400/80 focus:bg-white focus:shadow-[0_0_0_3px_rgba(45,212,191,0.18)]"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={login.isPending}
            className="mt-8 w-full rounded-full bg-zinc-900 py-3.5 text-sm font-semibold text-white shadow-[0_6px_28px_-8px_rgba(20,184,166,0.32),0_2px_10px_-6px_rgba(124,58,237,0.16)] transition-transform hover:scale-[1.01] disabled:opacity-50"
            onClick={() => login.mutate()}
          >
            {login.isPending ? "Signing in…" : "Sign in"}
          </button>
          <p className="mt-6 text-center text-xs text-zinc-500">
            <a
              className="font-medium text-teal-600 no-underline hover:text-teal-700"
              href={`${apiBase}/auth/google/start`}
            >
              Continue with Google
            </a>
          </p>
        </div>
        <p className="mt-8 text-center text-sm text-zinc-500">
          <Link to="/" className="text-zinc-600 no-underline hover:text-zinc-900">
            Back to home
          </Link>
        </p>
      </main>
    </MarketingLayout>
  );
}
