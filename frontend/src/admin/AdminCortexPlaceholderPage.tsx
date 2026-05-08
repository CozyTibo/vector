export default function AdminCortexPlaceholderPage({ title }: { title: string }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">{title}</h2>
      <p className="mt-2 text-sm text-stone-600">
        This Cortex section is reserved for upcoming phases and is intentionally disabled for now.
      </p>
    </section>
  );
}
