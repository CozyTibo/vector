import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import {
  marketingAccentLink,
  marketingBody,
  marketingBtnPrimaryPink,
  marketingCard,
  marketingField,
  marketingKicker,
  marketingLabel,
  marketingLabelTight,
  marketingMutedLink,
  marketingSectionTitle,
} from "../components/marketing/marketingStyles";
import { SHOW_GOOGLE_OAUTH } from "../lib/authUi";
import { readErrorDetail } from "../lib/canonicalApi";
import { fetchMe, productApiBase, signedInDestination } from "../lib/meApi";

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
      navigate("/signup/waitlist", { replace: true });
    },
    onError: (e: Error) => {
      setNotice(e.message);
    },
  });

  if (already.data) {
    return <Navigate to={signedInDestination(already.data)} replace />;
  }

  return (
    <MarketingLayout accentJoinListCta>
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-lg flex-col justify-center px-5 py-12 sm:px-8">
        <div className={marketingCard}>
          <p className={marketingKicker}>Early access waitlist</p>
          <h1 className={`${marketingSectionTitle} mt-3`}>Join the list</h1>
          <p className={`${marketingBody} mt-3`}>
            Sign up for an early-stage access to Vector.
            <br />
            We currently onboard companies in batches as we finalize the product roll out.
          </p>
          <p className={`${marketingBody} mt-4`}>
            Already have one?{" "}
            <Link to="/login" className={marketingAccentLink}>
              Sign in
            </Link>
          </p>
          {notice ? (
            <p className="mt-5 rounded-2xl border border-rose-200/80 bg-rose-50 px-4 py-3 text-sm text-rose-900">
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
                autoComplete="new-password"
                className={marketingField}
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <button type="submit" disabled={register.isPending} className={`mt-8 ${marketingBtnPrimaryPink}`}>
              {register.isPending ? "Joining…" : "Join the list"}
            </button>
          </form>
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
