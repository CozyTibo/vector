import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import ChatMessageList from "../components/onboarding/ChatMessageList";
import MarketingLayout from "../components/marketing/MarketingLayout";
import OnboardingChatLayout from "../components/onboarding/OnboardingChatLayout";
import {
  ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS,
  ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS,
} from "../components/onboarding/onboardingUiConstants";
import type { ChatMessage } from "../components/onboarding/types";
import { WAITLIST_VECTOR_OPENING_MESSAGE } from "../components/onboarding/waitlistChatCopy";
import { marketingBody } from "../components/marketing/marketingStyles";
import { productApiBase, signedInDestination, useProductMeQuery } from "../lib/meApi";
import { mergeProductSessionAuth, setStoredSessionToken } from "../lib/sessionToken";

async function logoutRequest(base: string): Promise<void> {
  const res = await fetch(`${base}/auth/logout`, mergeProductSessionAuth({ method: "POST" }));
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export default function SignupWaitlistPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const me = useProductMeQuery(apiBase, {
    refetchInterval: (q) => {
      const d = q.state.data;
      return d && d.workspace_access_enabled === false ? 30_000 : false;
    },
  });

  const messages = useMemo<ChatMessage[]>(
    () => [
      {
        id: "waitlist-vector-intro",
        role: "vector",
        content: WAITLIST_VECTOR_OPENING_MESSAGE,
        timestamp: Date.now(),
      },
    ],
    [],
  );

  const lo = useMutation({
    mutationFn: () => logoutRequest(apiBase),
    onSuccess: async () => {
      setStoredSessionToken(null);
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate("/", { replace: true });
    },
  });

  const waitlistFooter = (
    <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
      <div className={ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS}>
        <div className="mt-2 flex flex-col items-center gap-3">
          <Link to="/" className={ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS}>
            Back to home
          </Link>
        </div>
      </div>
    </div>
  );

  // After signup, `me` can still be stale `null` while the post-cookie refetch runs; `isPending` is
  // false in that case (query already resolved unauthenticated once). Treat fetching + no payload
  // as loading so we do not redirect to login on slower networks (common on mobile).
  const meStillResolving = me.isPending || (me.isFetching && !me.data);

  if (meStillResolving) {
    return (
      <MarketingLayout accentJoinListCta signedSession="pending">
        <main className="mx-auto flex min-h-[calc(100dvh-5.5rem)] max-w-4xl flex-col justify-center px-5 py-12 sm:px-8">
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
      <main className="mx-auto flex h-[calc(100dvh-5.5rem)] min-h-0 w-full max-w-[96rem] flex-col overflow-hidden px-0">
        <OnboardingChatLayout
          backdropTopClassName="top-[5.5rem]"
          backdropStyle="solid"
          channelLabel="#onboarding"
          footer={waitlistFooter}
        >
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList
              messages={messages}
              userDisplayName="You"
              isTyping={false}
              autoScrollToBottom={false}
            />
          </div>
        </OnboardingChatLayout>
      </main>
    </MarketingLayout>
  );
}
