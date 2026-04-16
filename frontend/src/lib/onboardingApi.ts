import { readErrorDetail } from "./canonicalApi";
import { mergeProductSessionAuth } from "./sessionToken";

export type OnboardingStep =
  | "CHAT_PROFILE"
  | "CONNECT_COMMUNICATION"
  | "SLACK_STAKEHOLDERS"
  | "ADMIN_ACCESS"
  | "SCANNING"
  | "THANK_YOU";

export type SlackWorkspaceMember = {
  id: string;
  label: string;
  /** Slack login name (without @); shown in confirmations and saved as @username in chat. */
  username: string;
  /** Lowercase email when the Slack app has users:read.email and the user exposes it. */
  email: string | null;
  image_48: string | null;
};

export type OnboardingMessagePayload = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

export type OnboardingStatePayload = {
  id: string;
  status: string;
  current_step: string;
  answers: Record<string, unknown>;
  version: number;
  started_at: string | null;
  completed_at: string | null;
  abandoned_at: string | null;
  /** Persisted chat turns from the API (chronological). Empty when the messages table is absent or new tenant. */
  messages?: OnboardingMessagePayload[];
  github_connected: boolean;
  linear_connected: boolean;
  slack_connected: boolean;
};

export async function fetchOnboarding(base: string): Promise<OnboardingStatePayload> {
  const res = await fetch(`${base}/onboarding`, mergeProductSessionAuth());
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<OnboardingStatePayload>;
}

/** Hard reset: clears persisted chat and answers; connectors stay connected. */
export async function postRestartOnboarding(base: string): Promise<OnboardingStatePayload> {
  const res = await fetch(`${base}/onboarding/restart`, mergeProductSessionAuth({ method: "POST" }));
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<OnboardingStatePayload>;
}

export async function patchOnboarding(
  base: string,
  body: { current_step?: string; answers?: Record<string, unknown> },
): Promise<OnboardingStatePayload> {
  const res = await fetch(
    `${base}/onboarding`,
    mergeProductSessionAuth({
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<OnboardingStatePayload>;
}

export async function postOnboardingChat(
  base: string,
  body: { message: string | null; structured_action?: Record<string, unknown> | null },
): Promise<{
  assistant_message: string;
  assistant_messages: string[];
  step: string;
  answers: Record<string, unknown>;
}> {
  const res = await fetch(
    `${base}/onboarding/chat`,
    mergeProductSessionAuth({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<{
    assistant_message: string;
    assistant_messages: string[];
    step: string;
    answers: Record<string, unknown>;
  }>;
}

export async function fetchSlackWorkspaceMembers(base: string): Promise<SlackWorkspaceMember[]> {
  const res = await fetch(`${base}/onboarding/slack-members`, mergeProductSessionAuth());
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  const data = (await res.json()) as { members: SlackWorkspaceMember[] };
  return data.members ?? [];
}

export async function completeOnboarding(base: string): Promise<{ status: string; current_step: string; completed_at: string }> {
  const res = await fetch(`${base}/onboarding/complete`, mergeProductSessionAuth({ method: "POST" }));
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<{ status: string; current_step: string; completed_at: string }>;
}
