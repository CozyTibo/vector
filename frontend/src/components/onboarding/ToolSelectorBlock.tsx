import { landingAccentText } from "../landing/landingBrandPalette";

export type ToolGroupDef = {
  key: string;
  label: string;
  items: { id: string; label: string }[];
};

type ToolSelectorBlockProps = {
  groups: ToolGroupDef[];
  value: Record<string, string[]>;
  onToggle: (categoryKey: string, toolId: string) => void;
  onConfirm: () => void;
  disabled?: boolean;
};

export default function ToolSelectorBlock({ groups, value, onToggle, onConfirm, disabled = false }: ToolSelectorBlockProps) {
  const comm = value.communication ?? [];
  const pm = value.pm ?? [];
  const eng = value.engineering ?? [];
  const confirmDisabled = disabled || comm.length === 0 || pm.length === 0 || eng.length === 0;

  const confirmTitle = (() => {
    if (disabled) {
      return undefined;
    }
    if (comm.length === 0) {
      return "Choose Slack, Teams, or Discord first.";
    }
    if (pm.length === 0) {
      return "Pick at least one project management tool.";
    }
    if (eng.length === 0) {
      return "Pick at least one engineering tool.";
    }
    return undefined;
  })();

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-4 pt-2 sm:px-5 sm:pt-2.5">
      <p className="shrink-0 text-center text-[12px] font-medium leading-snug text-zinc-600 sm:text-[13px] sm:leading-relaxed">
        Pick at least one tool in <strong>Communication</strong>, <strong>Project management</strong>, and{" "}
        <strong>Engineering</strong>. Add more anywhere you like; other sections stay optional.
      </p>
      <div className="mx-auto mt-1.5 min-h-0 w-full max-w-full flex-1 overflow-x-hidden overflow-y-auto overscroll-contain pb-1 sm:mt-2 sm:pb-1.5">
        <div className="space-y-4 sm:space-y-5">
          {groups.map((g) => {
            const required = g.key === "communication" || g.key === "pm" || g.key === "engineering";
            return (
              <div
                key={g.key}
                className={required ? "border-l-2 border-[#E878BE] pl-2.5" : undefined}
              >
                <h3
                  className={
                    "mb-1 flex flex-wrap items-center gap-x-1 text-[10.5px] font-bold uppercase tracking-[0.12em] sm:text-[11px] " +
                    (required ? "text-zinc-700" : "text-zinc-400")
                  }
                >
                  <span>{g.label}</span>
                  {required ? (
                    <>
                      <span className="font-semibold normal-case tracking-normal text-[#BE5E94]" aria-hidden>
                        *
                      </span>
                      <span className="sr-only"> (required)</span>
                    </>
                  ) : null}
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {g.items.map((item) => {
                    const selected = (value[g.key] ?? []).includes(item.id);
                    return (
                      <button
                        key={item.id}
                        type="button"
                        disabled={disabled}
                        onClick={() => onToggle(g.key, item.id)}
                        className={[
                          "rounded-full border px-2.5 py-[5px] text-[13px] font-semibold transition duration-150 ease-out sm:px-3 sm:py-1 sm:text-sm",
                          selected
                            ? `border-[#E878BE]/50 bg-[#E878BE]/12 ${landingAccentText} shadow-[0_8px_24px_-14px_rgba(232,120,190,0.45)]`
                            : "border-zinc-200/95 bg-white text-zinc-800 shadow-sm hover:border-[#E878BE]/30 hover:bg-zinc-50/90 active:scale-[0.99]",
                          disabled ? "cursor-not-allowed opacity-45" : "cursor-pointer",
                        ].join(" ")}
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="shrink-0 border-t border-zinc-100/90 bg-white/95 py-2 pt-2 sm:py-2.5">
        <div className="flex justify-center">
          <button
            type="button"
            disabled={confirmDisabled}
            title={confirmTitle}
            onClick={onConfirm}
            className={
              "cursor-pointer rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-9 py-2 text-sm font-semibold text-white sm:py-2.5 " +
              "shadow-[0_14px_36px_-18px_rgba(232,120,190,0.75)] transition hover:brightness-[1.03] active:scale-[0.99] " +
              "disabled:cursor-not-allowed disabled:opacity-40"
            }
          >
            Confirm selection
          </button>
        </div>
      </div>
    </div>
  );
}
