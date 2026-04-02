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
  return (
    <div className="max-h-[min(52vh,420px)] overflow-y-auto overflow-x-hidden px-4 py-4 sm:px-5">
      <div className="mx-auto w-full max-w-full space-y-6">
        <p className="text-center text-[13px] font-medium leading-relaxed text-zinc-600">
          Pick what your team uses: one choice per row (tap again to clear).
        </p>
        {groups.map((g) => (
          <div key={g.key}>
            <h3 className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-zinc-400">{g.label}</h3>
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
                      disabled ? "cursor-not-allowed opacity-45" : "",
                    ].join(" ")}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <div className="flex justify-center pt-1">
          <button
            type="button"
            disabled={disabled}
            onClick={onConfirm}
            className={
              "rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-9 py-2.5 text-sm font-semibold text-white " +
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
