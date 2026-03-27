import { readErrorDetail } from "./canonicalApi";

export type OnboardingStep =
  | "WELCOME"
  | "COMPANY_INFO"
  | "TOOL_STACK_DISCOVERY"
  | "TOOLS_SELECTION"
  | "CONNECT_GITHUB"
  | "CONNECT_LINEAR"
  | "SCANNING"
  | "THANK_YOU";

export type OnboardingStatePayload = {
  id: string;
  status: string;
  current_step: string;
  answers: Record<string, unknown>;
  version: number;
  started_at: string | null;
  completed_at: string | null;
  abandoned_at: string | null;
  github_connected: boolean;
  linear_connected: boolean;
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
  body: { current_step?: OnboardingStep; answers?: Record<string, unknown> },
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
