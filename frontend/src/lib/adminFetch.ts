import { adminBasicAuthorizationHeader, getAdminPassword } from "./adminCredentials";
import { resolveAdminRequestUrl } from "./adminApiUrl";
import { readErrorDetail } from "./canonicalApi";

const ADMIN_FETCH_TIMEOUT_MS = 45_000;

export async function adminFetch(
  path: string,
  init?: RequestInit,
  options?: { timeoutMs?: number },
): Promise<Response> {
  const pw = getAdminPassword();
  if (!pw) {
    throw new Error("Admin password not set");
  }
  const headers = new Headers(init?.headers);
  headers.set("Authorization", adminBasicAuthorizationHeader(pw));
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? ADMIN_FETCH_TIMEOUT_MS;
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(resolveAdminRequestUrl(path), {
      ...init,
      headers,
      signal: init?.signal ?? controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Admin request timed out after ${timeoutMs / 1000}s (${path})`);
    }
    throw err;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function adminJson<T>(
  path: string,
  init?: RequestInit,
  options?: { timeoutMs?: number },
): Promise<T> {
  const res = await adminFetch(path, init, options);
  if (res.status === 401) {
    throw new Error("Invalid admin password");
  }
  if (res.status === 504) {
    throw new Error("Server timed out — try again in a moment.");
  }
  if (res.status === 503) {
    const detail = await readErrorDetail(res);
    throw new Error(detail);
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<T>;
}
