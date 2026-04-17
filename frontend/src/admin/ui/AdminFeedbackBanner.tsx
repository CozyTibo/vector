type Props = {
  kind: "success" | "error";
  message: string;
  onDismiss: () => void;
};

/** Inline admin feedback after destructive or important actions. */
export default function AdminFeedbackBanner({ kind, message, onDismiss }: Props) {
  const styles =
    kind === "success"
      ? "border-emerald-300 bg-emerald-50 text-emerald-950"
      : "border-red-300 bg-red-50 text-red-950";

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm shadow-sm ${styles}`}
      role={kind === "error" ? "alert" : "status"}
    >
      <p className="min-w-0 flex-1 leading-relaxed">{message}</p>
      <button
        type="button"
        className="shrink-0 rounded-md border border-current/20 bg-white/80 px-2 py-1 text-xs font-medium hover:bg-white"
        onClick={onDismiss}
      >
        Dismiss
      </button>
    </div>
  );
}
