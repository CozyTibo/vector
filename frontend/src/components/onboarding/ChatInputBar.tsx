import { landingAccentText } from "../landing/landingBrandPalette";

type ChatInputBarProps = {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
};

export default function ChatInputBar({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = "Message Vector…",
}: ChatInputBarProps) {
  return (
    <div className="px-4 py-3 sm:px-5">
      <div
        className={
          "flex min-h-[52px] items-stretch gap-1 rounded-[1.15rem] border border-zinc-200/90 bg-zinc-50/90 pl-4 pr-1.5 py-1.5 " +
          "shadow-[0_14px_40px_-28px_rgba(15,23,42,0.35)] ring-1 ring-zinc-950/[0.03] focus-within:border-[#E878BE]/35 " +
          "focus-within:ring-2 focus-within:ring-[#E878BE]/20"
        }
      >
        <input
          type="text"
          className="min-h-10 min-w-0 flex-1 border-0 bg-transparent py-2 text-[15px] text-zinc-900 outline-none placeholder:text-zinc-400 disabled:opacity-50"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          aria-label="Message"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!disabled && value.trim()) {
                onSend();
              }
            }
          }}
        />
        <button
          type="button"
          disabled={disabled || !value.trim()}
          onClick={onSend}
          className={
            `shrink-0 self-center rounded-xl px-4 py-2 text-sm font-semibold transition ` +
            `disabled:cursor-not-allowed disabled:opacity-35 ${landingAccentText} ` +
            `hover:bg-[#E878BE]/10 active:scale-[0.98] disabled:hover:bg-transparent`
          }
        >
          Send
        </button>
      </div>
    </div>
  );
}
