type Variant = "strip" | "attention" | "actions" | "table" | "footer";

export function SectionSkeleton({ variant }: { variant: Variant }) {
  const pulse = "animate-pulse rounded bg-stone-200";
  if (variant === "strip") {
    return (
      <div className="flex flex-wrap gap-2" aria-busy="true" aria-label="Loading pipeline phases">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className={`min-w-[6.5rem] flex-1 h-[5.5rem] ${pulse}`} />
        ))}
      </div>
    );
  }
  if (variant === "attention") {
    return (
      <div className={`h-24 w-full ${pulse}`} aria-busy="true" aria-label="Loading attention items" />
    );
  }
  if (variant === "actions") {
    return (
      <div className={`h-28 w-full ${pulse}`} aria-busy="true" aria-label="Loading pipeline actions" />
    );
  }
  if (variant === "table") {
    return (
      <div className="space-y-2" aria-busy="true" aria-label="Loading ingestion runs">
        <div className={`h-16 w-full ${pulse}`} />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className={`h-10 w-full ${pulse}`} />
        ))}
      </div>
    );
  }
  return (
    <div className={`h-12 w-full ${pulse}`} aria-busy="true" aria-label="Loading scheduler status" />
  );
}
