import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useNavigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import {
  marketingAccentLink,
  marketingBody,
  marketingBodyLarge,
  marketingCardLg,
  marketingKicker,
} from "../components/marketing/marketingStyles";
import { fetchMe, productApiBase, signedInDestination } from "../lib/meApi";

async function logoutRequest(base: string): Promise<void> {
  const res = await fetch(`${base}/auth/logout`, { method: "POST", credentials: "include" });
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export default function SignupWaitlistPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
    refetchInterval: (q) => {
      const d = q.state.data;
      return d && d.workspace_access_enabled === false ? 30_000 : false;
    },
  });

  const lo = useMutation({
    mutationFn: () => logoutRequest(apiBase),
    onSuccess: async () => {
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate("/", { replace: true });
    },
  });

  if (me.isPending) {
    return (
      <MarketingLayout accentJoinListCta signedSession="pending">
        <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-4xl flex-col justify-center px-5 py-12 sm:px-8">
          <p className={`${marketingBody} text-center text-lg`}>Loading…</p>
        </main>
      </MarketingLayout>
    );
  }

  if (!me.data) {
    return <Navigate to="/login" replace state={{ from: "/signup/waitlist" }} />;
  }

  if (me.data.workspace_access_enabled !== false) {
    return <Navigate to={signedInDestination(me.data)} replace />;
  }

  return (
    <MarketingLayout
      accentJoinListCta
      signedSession={{
        email: me.data.email,
        onSignOut: () => lo.mutate(),
        signOutPending: lo.isPending,
      }}
    >
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem)] max-w-4xl flex-col justify-center px-5 py-12 sm:px-8 lg:max-w-5xl">
        <div className={marketingCardLg}>
          <p className={marketingKicker}>You&apos;re on the list</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.02em] text-[#0F0F12] sm:mt-5 sm:text-5xl lg:text-6xl">
            Thank you
          </h1>
          <p className={`${marketingBodyLarge} mt-6 max-w-3xl`}>
            Thanks for signing up! We&apos;re onboarding companies in batches as we finish the rollout.
          </p>
          <p className={`${marketingBodyLarge} mt-6 max-w-3xl sm:mt-8`}>
            You&apos;ll receive an email shortly containing the next steps. When your workspace is
            activated, you&apos;ll be invited to start your own onboarding.
          </p>
          <p
            className={`${marketingBodyLarge} mt-6 max-w-3xl font-medium text-[#3f3f46] sm:mt-8`}
          >
            The good news is it only takes five minutes!
          </p>
          <p className="mt-10 text-center sm:mt-12">
            <Link to="/" className={`${marketingAccentLink} text-base sm:text-lg`}>
              Back to home
            </Link>
          </p>
        </div>
      </main>
    </MarketingLayout>
  );
}
