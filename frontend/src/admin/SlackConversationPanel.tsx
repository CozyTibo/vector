import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type SlackMessage = {
  id: string;
  direction: "inbound" | "outbound" | string;
  text: string;
  slack_user_id: string;
  slack_ts: string;
  created_at: string;
};

type SlackMessagesResponse = {
  messages: SlackMessage[];
};

type Props = {
  userId: string;
  tenantId: string;
  onClose: () => void;
};

const POLL_MS = 15_000;

function formatMessageTime(iso: string): string {
  const date = new Date(iso);
  const day = new Intl.DateTimeFormat("en-GB", { day: "2-digit" }).format(date);
  const month = new Intl.DateTimeFormat("en-GB", { month: "short" }).format(date);
  const time = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
  return `${day} ${month}, ${time}`;
}

async function readAdminError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { error?: unknown; detail?: unknown };
    if (typeof body.error === "string" && body.error.trim()) {
      return body.error;
    }
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
  } catch {
    /* fall through */
  }
  return readErrorDetail(res);
}

export default function SlackConversationPanel({ userId, tenantId, onClose }: Props) {
  const [messages, setMessages] = useState<SlackMessage[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const slackUserId = useMemo(
    () => (messages.length > 0 ? messages[messages.length - 1].slack_user_id : null),
    [messages],
  );

  const historyPath = useMemo(() => {
    const base = `/admin/tenants/${tenantId}/slack-messages`;
    if (slackUserId) {
      return `${base}?slack_user_id=${encodeURIComponent(slackUserId)}`;
    }
    return base;
  }, [tenantId, slackUserId]);

  const loadMessages = useCallback(
    async (silent: boolean) => {
      if (!silent) {
        setInitialLoading(true);
      }
      try {
        const data = await adminJson<SlackMessagesResponse>(historyPath, undefined, {
          tenantIdHint: tenantId,
        });
        setMessages(data.messages);
        setFetchError(null);
      } catch (err) {
        if (!silent) {
          setFetchError(err instanceof Error ? err.message : "Failed to load messages.");
        }
      } finally {
        if (!silent) {
          setInitialLoading(false);
        }
      }
    },
    [historyPath, tenantId],
  );

  useEffect(() => {
    void loadMessages(false);
  }, [loadMessages]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void loadMessages(true);
    }, POLL_MS);
    return () => {
      window.clearInterval(id);
    };
  }, [loadMessages]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  const canSend = messages.length > 0 && draft.trim().length > 0 && !sending;

  async function handleSend() {
    const text = draft.trim();
    if (!text || sending || messages.length === 0) {
      return;
    }
    setSending(true);
    setSendError(null);
    try {
      const res = await adminFetch(`/admin/users/${userId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readAdminError(res));
      }
      setDraft("");
      await loadMessages(true);
    } catch (err) {
      setSendError(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-[60] bg-stone-900/25"
        aria-label="Close Slack conversation panel"
        onClick={onClose}
      />
      <aside
        className="fixed right-0 top-0 z-[61] flex h-full w-full max-w-[480px] flex-col border-l border-stone-200 bg-white shadow-2xl"
        aria-label="Slack conversation"
      >
        <header className="flex shrink-0 items-center justify-between border-b border-stone-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-stone-900">Slack conversation</h2>
          <button
            type="button"
            className="rounded-md p-1.5 text-stone-500 hover:bg-stone-100 hover:text-stone-800"
            aria-label="Close"
            onClick={onClose}
          >
            <span aria-hidden="true" className="text-lg leading-none">
              ×
            </span>
          </button>
        </header>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {initialLoading ? (
            <p className="text-sm text-stone-500">Loading messages…</p>
          ) : fetchError ? (
            <p className="text-sm text-red-700" role="alert">
              {fetchError}
            </p>
          ) : messages.length === 0 ? (
            <p className="text-sm text-stone-500">
              No Slack conversation yet. The onboarding DM must be sent first.
            </p>
          ) : (
            <ul className="space-y-3">
              {messages.map((msg) => {
                const outbound = msg.direction === "outbound";
                return (
                  <li
                    key={msg.id}
                    className={`flex ${outbound ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                        outbound
                          ? "bg-rose-50 text-stone-900"
                          : "bg-stone-100 text-stone-900"
                      }`}
                    >
                      <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                      <p className="mt-1 text-[11px] text-stone-500">
                        {formatMessageTime(msg.created_at)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <footer className="shrink-0 border-t border-stone-200 bg-white px-4 py-3">
          {messages.length === 0 ? (
            <p className="mb-2 text-xs text-stone-500">
              No Slack conversation yet. The onboarding DM must be sent first.
            </p>
          ) : null}
          <textarea
            rows={3}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Message via Vector..."
            disabled={messages.length === 0 || sending}
            className="w-full resize-none rounded-md border border-stone-300 px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 disabled:cursor-not-allowed disabled:bg-stone-50"
          />
          {sendError ? (
            <p className="mt-2 text-xs text-red-700" role="alert">
              {sendError}
            </p>
          ) : null}
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              disabled={!canSend}
              onClick={() => void handleSend()}
              className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </footer>
      </aside>
    </>
  );
}
