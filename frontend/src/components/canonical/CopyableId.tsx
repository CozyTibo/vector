import { useState, type KeyboardEvent, type MouseEvent } from "react";

/** Muted, copy-on-click internal id (full value in tooltip). */
export function CopyableId({ id, shortLen = 8 }: { id: string; shortLen?: number }) {
  const [copied, setCopied] = useState(false);
  const short = id.length > shortLen ? `${id.slice(0, shortLen)}…` : id;

  async function copy(ev: MouseEvent) {
    ev.preventDefault();
    ev.stopPropagation();
    try {
      await navigator.clipboard.writeText(id);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  }

  return (
    <span className="debug-copy-id" title={id}>
      <code
        className="debug-copy-id__code"
        onClick={copy}
        onKeyDown={(ev: KeyboardEvent) => {
          if (ev.key === "Enter" || ev.key === " ") {
            void copy(ev as unknown as MouseEvent);
          }
        }}
        role="button"
        tabIndex={0}
      >
        {short}
      </code>
      {copied ? <span className="cell-muted"> copied</span> : null}
    </span>
  );
}
