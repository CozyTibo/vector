import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import { SHOW_GOOGLE_OAUTH } from "../lib/authUi";
import { readErrorDetail } from "../lib/canonicalApi";
import { fetchMe, productApiBase } from "../lib/meApi";

export default function SignupPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const already = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });

  const register = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: null,
          company_name: null,
        }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: async () => {
      setNotice(null);
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate("/app/onboarding", { replace: true });
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
        <div className="rounded-3xl border border-zinc-200/80 bg-white/85 p-8 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.12),inset_0_0_0_1px_rgba(139,92,246,0.07)] backdrop-blur-2xl sm:p-9">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-teal-700">
            Early access waitlist
          </p>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-zinc-900">Join the list</h1>
          <p className="mt-2 text-sm leading-relaxed text-zinc-600">
            Sign up for an early-stage access to Vector.
            <br />
            We currently onboard companies in batches as we finalize the product roll out.
          </p>
          <p className="mt-4 text-sm text-zinc-600">
            Already have one?{" "}
            <Link to="/login" className="font-medium text-teal-600 no-underline hover:text-teal-700">
              Sign in
            </Link>
          </p>
          {notice ? (
            <p className="mt-5 rounded-xl border border-rose-200/80 bg-rose-50 px-4 py-3 text-sm text-rose-900">
              {notice}
            </p>
          ) : null}
          <form
            className="contents"
            onSubmit={(e) => {
              e.preventDefault();
              if (!register.isPending) register.mutate();
            }}
          >
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
                autoComplete="new-password"
                className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50/80 px-4 py-3 text-zinc-900 outline-none placeholder:text-zinc-400 focus:border-teal-400/80 focus:bg-white focus:shadow-[0_0_0_3px_rgba(45,212,191,0.18)]"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={register.isPending}
              className="mt-8 w-full rounded-full bg-zinc-900 py-3.5 text-sm font-semibold text-white shadow-[0_6px_28px_-8px_rgba(20,184,166,0.32),0_2px_10px_-6px_rgba(124,58,237,0.16)] transition-transform hover:scale-[1.01] disabled:opacity-50"
            >
              {register.isPending ? "Joining…" : "Join the list"}
            </button>
          </form>
          {SHOW_GOOGLE_OAUTH ? (
            <p className="mt-6 text-center text-xs text-zinc-500">
              <a
                className="font-medium text-teal-600 no-underline hover:text-teal-700"
                href={`${apiBase}/auth/google/start`}
              >
                Continue with Google
              </a>
            </p>
          ) : null}
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
