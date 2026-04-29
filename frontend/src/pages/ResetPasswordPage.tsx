import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";

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
import { readErrorDetail } from "../lib/canonicalApi";
import { productApiBase, useProductMeQuery } from "../lib/meApi";

export default function ResetPasswordPage() {
  const apiBase = productApiBase();
  const already = useProductMeQuery(apiBase);
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token")?.trim() ?? "", [params]);

  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const submit = useMutation({
    mutationFn: async () => {
      if (password !== password2) {
        throw new Error("Passwords do not match.");
      }
      const res = await fetch(`${apiBase}/auth/reset-password`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
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

  if (!token) {
    return (
      <MarketingLayout>
        <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-lg flex-col justify-center px-5 py-12 sm:px-8">
          <div className={marketingCard}>
            <h1 className={marketingPageTitle}>Invalid link</h1>
            <p className={`${marketingBody} mt-3`}>
              This reset link is missing a token. Request a new link from the sign-in page.
            </p>
            <p className={`${marketingBody} mt-6`}>
              <Link to="/login/forgot-password" className={marketingAccentLink}>
                Forgot password
              </Link>
            </p>
          </div>
        </main>
      </MarketingLayout>
    );
  }

  return (
    <MarketingLayout>
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-lg flex-col justify-center px-5 py-12 sm:px-8">
        <div className={marketingCard}>
          <h1 className={marketingPageTitle}>Set a new password</h1>
          {done ? (
            <>
              <p className="mt-6 rounded-2xl border border-emerald-200/80 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
                Your password has been updated. You can sign in.
              </p>
              <p className={`${marketingBody} mt-8`}>
                <Link to="/login" className={marketingAccentLink}>
                  Sign in
                </Link>
              </p>
            </>
          ) : (
            <>
              <p className={`${marketingBody} mt-3`}>Choose a strong password (at least 8 characters).</p>
              {notice ? (
                <p className="mt-5 rounded-2xl border border-rose-200/80 bg-rose-50 px-4 py-3 text-sm text-rose-900">
                  {notice}
                </p>
              ) : null}
              <label className={marketingLabel}>
                New password
                <input
                  type="password"
                  autoComplete="new-password"
                  className={marketingField}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <label className={marketingLabelTight}>
                Confirm password
                <input
                  type="password"
                  autoComplete="new-password"
                  className={marketingField}
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                />
              </label>
              <button
                type="button"
                disabled={submit.isPending || password.length < 8}
                className={`mt-8 ${marketingBtnPrimaryPink}`}
                onClick={() => submit.mutate()}
              >
                {submit.isPending ? "Updating…" : "Update password"}
              </button>
            </>
          )}
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
