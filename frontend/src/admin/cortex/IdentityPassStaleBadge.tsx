/** Red pill shown when no identity pass started in the last 10 minutes (scheduler active). */
export function IdentityPassStaleBadge() {
  return (
    <span
      className="ml-1.5 inline-flex shrink-0 items-center rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
      title="No identity pass started in the last 10 minutes"
    >
      Stale
    </span>
  );
}
