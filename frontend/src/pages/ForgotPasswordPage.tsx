import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import {
  marketingAccentLink,
  marketingBody,
  marketingBtnPrimaryPink,
  marketingCard,
  marketingField,
  marketingLabel,
  marketingMutedLink,
  marketingPageTitle,
} from "../components/marketing/marketingStyles";
import { readErrorDetail } from "../lib/canonicalApi";
import { productApiBase, useProductMeQuery } from "../lib/meApi";

const FORGOT_OK =
  "If an account exists for that email, we sent password reset instructions. Check your inbox.";

export default function ForgotPasswordPage() {
  const apiBase = productApiBase();
  const already = useProductMeQuery(apiBase);
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/forgot-password`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: () => {
      setNotice(null);
      setDone(true);
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
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-lg flex-col justify-center px-5 py-12 sm:px-8">
        <div className={marketingCard}>
          <h1 className={marketingPageTitle}>Forgot password</h1>
          <p className={`${marketingBody} mt-3`}>
            Enter the email you use for Vector. We’ll send a reset link if an account exists.
          </p>
          {done ? (
            <p className="mt-6 rounded-2xl border border-emerald-200/80 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
              {FORGOT_OK}
            </p>
          ) : (
            <>
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
              <button
                type="button"
                disabled={submit.isPending || !email.trim()}
                className={`mt-8 ${marketingBtnPrimaryPink}`}
                onClick={() => submit.mutate()}
              >
                {submit.isPending ? "Sending…" : "Send reset link"}
              </button>
            </>
          )}
          <p className={`${marketingBody} mt-8`}>
            <Link to="/login" className={marketingAccentLink}>
              Back to sign in
            </Link>
          </p>
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
