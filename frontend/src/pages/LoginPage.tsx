import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import {
  marketingAccentLink,
  marketingBody,
  marketingBtnPrimaryPink,
  marketingCard,
  marketingField,
  marketingLabel,
  marketingLabelTight,
  marketingMutedLink,
  marketingPageTitle,
} from "../components/marketing/marketingStyles";
import { SHOW_GOOGLE_OAUTH } from "../lib/authUi";
import { readErrorDetail } from "../lib/canonicalApi";
import { productApiBase, signedInDestination, useProductMeQuery } from "../lib/meApi";
import { getStoredSessionToken, setStoredSessionToken } from "../lib/sessionToken";

export default function LoginPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const from = loc.state?.from ?? "/app";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const already = useProductMeQuery(apiBase);

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
      const body = (await res.json()) as { session_token?: string | null };
      if (body.session_token) {
        setStoredSessionToken(body.session_token);
        if (!getStoredSessionToken()) {
          throw new Error(
            "Your browser blocked saving the session. Allow site data for this site and try again.",
          );
        }
      }
    },
    onSuccess: async () => {
      setNotice(null);
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate(from, { replace: true });
    },
    onError: (e: Error) => {
      setNotice(e.message);
    },
  });

  if (already.data) {
    return <Navigate to={signedInDestination(already.data)} replace />;
  }

  return (
    <MarketingLayout>
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-lg flex-col justify-center px-5 py-12 sm:px-8">
        <div className={marketingCard}>
          <h1 className={marketingPageTitle}>Sign in</h1>
          <p className={`${marketingBody} mt-3`}>
            New here?{" "}
            <Link to="/signup" className={marketingAccentLink}>
              Join the list
            </Link>
          </p>
          {notice ? (
            <p className="mt-5 rounded-2xl border border-rose-200/80 bg-rose-50 px-4 py-3 text-sm text-rose-900">
              {notice}
            </p>
          ) : null}
          <label className={marketingLabel}>
            Email
            <input
              type="email"
              autoComplete="email"
              className={marketingField}
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className={marketingLabelTight}>
            Password
            <input
              type="password"
              autoComplete="current-password"
              className={marketingField}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <p className="mt-2 text-right text-sm">
            <Link to="/login/forgot-password" className={marketingAccentLink}>
              Forgot password?
            </Link>
          </p>
          <button
            type="button"
            disabled={login.isPending}
            className={`mt-8 ${marketingBtnPrimaryPink}`}
            onClick={() => login.mutate()}
          >
            {login.isPending ? "Signing in…" : "Sign in"}
          </button>
          {SHOW_GOOGLE_OAUTH ? (
            <p className="mt-6 text-center text-sm text-[#52525B]">
              <a className={marketingAccentLink} href={`${apiBase}/auth/google/start`}>
                Continue with Google
              </a>
            </p>
          ) : null}
        </div>
        <p className="mt-8 text-center">
          <Link to="/" className={marketingMutedLink}>
            Back to home
          </Link>
        </p>
      </main>
    </MarketingLayout>
  );
}
