export function OperatorIntro({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <header className="mb-8">
      <h1 className="text-2xl font-semibold tracking-tight text-stone-900">{title}</h1>
      <div className="mt-2 max-w-3xl text-sm leading-relaxed text-stone-600">{children}</div>
    </header>
  );
}

export function OperatorSection({
  title,
  description,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-stone-200 bg-white p-6 shadow-sm ${className}`}>
      <h2 className="text-base font-semibold text-stone-900">{title}</h2>
      {description ? <p className="mt-1 text-sm text-stone-600">{description}</p> : null}
      <div className={description ? "mt-4" : "mt-3"}>{children}</div>
    </section>
  );
}

export function CollapsibleDebug({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details
      className="rounded-lg border border-stone-200 bg-stone-50/80"
      open={defaultOpen}
    >
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-stone-700 hover:bg-stone-100/80">
        {title}
      </summary>
      <div className="border-t border-stone-200 bg-white px-4 py-4">{children}</div>
    </details>
  );
}
