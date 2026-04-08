type Tone = "ok" | "warn" | "neutral" | "bad";

const toneCls: Record<Tone, string> = {
  ok: "border-emerald-200 bg-emerald-50 text-emerald-900",
  warn: "border-amber-200 bg-amber-50 text-amber-950",
  neutral: "border-stone-200 bg-stone-100 text-stone-800",
  bad: "border-red-200 bg-red-50 text-red-900",
};

export function StatusBadge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneCls[tone]}`}
    >
      {children}
    </span>
  );
}
