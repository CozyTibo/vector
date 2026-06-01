import type { SurfaceOmission } from "./executionSurfacesTypes";

export function OmissionBanner({ omission }: { omission: SurfaceOmission | null | undefined }) {
  if (!omission) return null;
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
      <p className="font-medium">{omission.message}</p>
      {omission.remediation ? (
        <p className="mt-1 text-amber-900">
          <span className="font-medium">Reason: </span>
          {omission.remediation}
        </p>
      ) : null}
      <p className="mt-1 font-mono text-xs text-amber-800">{omission.code}</p>
    </div>
  );
}

export function ObservationFootnote({ text }: { text: string }) {
  return <p className="text-xs text-stone-500 italic">{text}</p>;
}

export function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h3 className="font-semibold text-stone-900">
        {title}
        <span className="ml-2 font-normal text-stone-500">{count}</span>
      </h3>
    </div>
  );
}
