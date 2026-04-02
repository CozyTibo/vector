import { readErrorDetail } from "./canonicalApi";

export type OnboardingStep =
  | "CHAT_PROFILE"
  | "CONNECT_COMMUNICATION"
  | "CONNECT_GITHUB"
  | "CONNECT_LINEAR"
  | "SCANNING"
  | "THANK_YOU";

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
  const res = await fetch(`${base}/onboarding`, { credentials: "include" });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<OnboardingStatePayload>;
}

export async function patchOnboarding(
  base: string,
  body: { current_step?: string; answers?: Record<string, unknown> },
): Promise<OnboardingStatePayload> {
  const res = await fetch(`${base}/onboarding`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
  const res = await fetch(`${base}/onboarding/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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

export async function completeOnboarding(base: string): Promise<{ status: string; current_step: string; completed_at: string }> {
  const res = await fetch(`${base}/onboarding/complete`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<{ status: string; current_step: string; completed_at: string }>;
}

export async function triggerGithubSync(base: string): Promise<{
  run_id: string;
  status: string;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
}> {
  const res = await fetch(`${base}/connectors/github/sync`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<{
    run_id: string;
    status: string;
    error_summary: string | null;
    stats: Record<string, unknown> | null;
  }>;
}

export async function triggerLinearSync(base: string): Promise<{
  run_id: string;
  status: string;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
}> {
  const res = await fetch(`${base}/connectors/linear/sync`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<{
    run_id: string;
    status: string;
    error_summary: string | null;
    stats: Record<string, unknown> | null;
  }>;
}
