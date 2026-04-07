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
  const confirmDisabled = disabled || comm.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-4 pt-3 sm:px-5 sm:pt-4">
      <p className="shrink-0 text-center text-[13px] font-medium leading-relaxed text-zinc-600">
        Pick one communication tool and any others that apply.
      </p>
      <div className="mx-auto mt-4 min-h-0 w-full max-w-full flex-1 overflow-y-auto overflow-x-hidden overscroll-contain pb-3">
        <div className="space-y-5">
          {groups.map((g) => (
            <div key={g.key}>
              <h3 className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-zinc-400">
                {g.label}
                {g.key === "communication" ? (
                  <span className="ml-0.5 font-semibold normal-case text-[#BE5E94]" title="Required">
                    *
                  </span>
                ) : null}
                {g.key === "communication" ? (
                  <span className="sr-only"> (required)</span>
                ) : null}
              </h3>
              <div className="flex flex-wrap gap-2">
                {g.items.map((item) => {
                  const selected = (value[g.key] ?? []).includes(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      disabled={disabled}
                      onClick={() => onToggle(g.key, item.id)}
                      className={[
                        "rounded-full border px-3.5 py-1.5 text-sm font-semibold transition will-change-transform",
                        "duration-150 ease-out",
                        selected
                          ? `border-[#E878BE]/50 bg-[#E878BE]/12 ${landingAccentText} shadow-[0_8px_24px_-14px_rgba(232,120,190,0.65)] scale-[1.02]`
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
          ))}
        </div>
      </div>
      <div className="shrink-0 border-t border-zinc-100/90 bg-white/95 py-3 pt-3">
        <div className="flex justify-center">
          <button
            type="button"
            disabled={confirmDisabled}
            title={confirmDisabled && !disabled ? "Choose Slack, Teams, or Discord first." : undefined}
            onClick={onConfirm}
            className={
              "cursor-pointer rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-9 py-2.5 text-sm font-semibold text-white " +
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
