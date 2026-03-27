const STORAGE_KEY = "vector_admin_password";

export function getAdminPassword(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAdminPassword(password: string): void {
  sessionStorage.setItem(STORAGE_KEY, password);
}

export function clearAdminPassword(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function adminBasicAuthorizationHeader(password: string, username = "admin"): string {
  return `Basic ${btoa(`${username}:${password}`)}`;
}
