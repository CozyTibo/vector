/** Final website onboarding wrap-up (ADMIN_ACCESS) — Vector copy. */

export const ONBOARDING_WRAP_UP_THANKS =
  "We've got everything—thanks! I'll ping you on Slack when I'm up and running. Talk soon.";

export function wrapUpManagerIntroQuestion(managerHandlesJoined: string): string {
  return (
    `Oh, and before you go: may I introduce myself in Slack to the managers you listed (${managerHandlesJoined})?`
  );
}
