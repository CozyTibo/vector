import { adminBasicAuthorizationHeader, getAdminPassword } from "./adminCredentials";
import { getApiBase, readErrorDetail } from "./canonicalApi";

const ADMIN_FETCH_TIMEOUT_MS = 45_000;

export async function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const pw = getAdminPassword();
  if (!pw) {
    throw new Error("Admin password not set");
  }
  const headers = new Headers(init?.headers);
  headers.set("Authorization", adminBasicAuthorizationHeader(pw));
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), ADMIN_FETCH_TIMEOUT_MS);
  try {
    return await fetch(`${getApiBase()}${path}`, {
      ...init,
      headers,
      signal: init?.signal ?? controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Admin request timed out after ${ADMIN_FETCH_TIMEOUT_MS / 1000}s (${path})`);
    }
    throw err;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function adminJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await adminFetch(path, init);
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
