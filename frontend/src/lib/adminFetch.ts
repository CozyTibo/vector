import { adminBasicAuthorizationHeader, getAdminPassword } from "./adminCredentials";
import { getApiBase, readErrorDetail } from "./canonicalApi";

export async function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const pw = getAdminPassword();
  if (!pw) {
    throw new Error("Admin password not set");
  }
  const headers = new Headers(init?.headers);
  headers.set("Authorization", adminBasicAuthorizationHeader(pw));
  return fetch(`${getApiBase()}${path}`, { ...init, headers });
}

export async function adminJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await adminFetch(path, init);
  if (res.status === 401) {
    throw new Error("Invalid admin password");
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
