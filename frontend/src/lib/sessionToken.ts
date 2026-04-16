/** Product session JWT for cross-origin SPA + API when HttpOnly cookies are blocked (e.g. mobile Safari). */

const STORAGE_KEY = "vector_session_token";

const listeners = new Set<() => void>();

export function subscribeSessionToken(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange);
  return () => listeners.delete(onStoreChange);
}

function emitSessionToken(): void {
  for (const cb of listeners) {
    cb();
  }
}

/** Used in React Query keys so `me` refetches when a bearer token is saved or cleared. */
export function getSessionAuthSlot(): "t" | "n" {
  return getStoredSessionToken() ? "t" : "n";
}

export function getStoredSessionToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredSessionToken(token: string | null): void {
  try {
    if (token == null || token === "") {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, token);
    }
  } catch {
    /* storage blocked */
  }
  emitSessionToken();
}

/** Merge `Authorization: Bearer` when a token is stored (cookie may still be sent). */
export function mergeProductSessionAuth(init: RequestInit = {}): RequestInit {
  const token = getStoredSessionToken();
  const next: RequestInit = { ...init, credentials: "include" };
  if (!token) {
    return next;
  }
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return { ...next, headers };
}

/**
 * Google OAuth callback redirects with `#st=<url-encoded-jwt>` so the SPA can persist the session
 * when the API cookie is third-party / partitioned.
 */
export function consumeSessionTokenFromOAuthRedirect(): void {
  const hash = window.location.hash.replace(/^#/, "");
  const prefix = "st=";
  if (!hash.startsWith(prefix)) {
    return;
  }
  const raw = hash.slice(prefix.length);
  try {
    const token = decodeURIComponent(raw);
    if (token) {
      setStoredSessionToken(token);
    }
  } catch {
    /* ignore malformed */
  }
}
