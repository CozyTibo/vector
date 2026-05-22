export function CortexPageSkeleton({ label }: { label: string }) {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-label={label}>
      <p className="text-sm text-stone-500">{label}</p>
      <div className="h-24 rounded-xl border border-stone-200 bg-stone-100" />
      <div className="h-40 rounded-xl border border-stone-200 bg-stone-100" />
      <div className="h-32 rounded-xl border border-stone-200 bg-stone-100" />
    </div>
  );
}
