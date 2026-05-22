import { mergeProductSessionAuth } from "./sessionToken";

export function getApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL;
  // Empty in dev → same-origin requests; Vite proxies API paths to the backend (no CORS).
  if (typeof raw === "string" && raw.trim() === "" && import.meta.env.DEV) {
    return "";
  }
  if (typeof raw !== "string" || !raw.trim()) {
    if (import.meta.env.DEV) {
      return "";
    }
    return "http://localhost:8000";
  }
  return raw.replace(/\/$/, "");
}

type FastApiValidationItem = {
  loc?: unknown[];
  msg?: string;
  type?: string;
};

function lastLocField(loc: unknown[] | undefined): string {
  if (!loc?.length) {
    return "field";
  }
  const last = loc[loc.length - 1];
  return typeof last === "string" ? last : "field";
}

function fieldHeading(key: string): string {
  switch (key) {
    case "email":
      return "Email";
    case "password":
      return "Password";
    case "full_name":
      return "Full name";
    case "company_name":
      return "Company";
    default:
      return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

function formatValidationErrors(items: FastApiValidationItem[]): string {
  const parts: string[] = [];
  for (const item of items) {
    const key = lastLocField(item.loc);
    const t = item.type ?? "";
    const m = (item.msg ?? "").toLowerCase();

    if (key === "email" && (t.includes("email") || m.includes("email") || m.includes("@"))) {
      parts.push("Use a valid email with a domain (e.g. you@company.com).");
      continue;
    }
    if (key === "password") {
      if (t === "string_too_short" || m.includes("at least")) {
        parts.push("Password must be at least 8 characters.");
        continue;
      }
      if (t === "string_too_long" || m.includes("at most")) {
        parts.push("Password is too long.");
        continue;
      }
    }
    if ((key === "full_name" || key === "company_name") && (t === "string_too_long" || m.includes("at most"))) {
      parts.push(`${fieldHeading(key)} is too long.`);
      continue;
    }

    const raw = item.msg?.trim();
    if (raw) {
      const short = raw.replace(/^value error,\s*/i, "").replace(/^string\s+/i, "");
      parts.push(`${fieldHeading(key)}: ${short}`);
    }
  }

  const unique = [...new Set(parts)];
  return unique.length > 0 ? unique.join(" ") : "Please check your input and try again.";
}

export async function readErrorDetail(res: Response): Promise<string> {
  const fallback = `Something went wrong (HTTP ${res.status}). Try again.`;
  try {
    const data = (await res.json()) as {
      detail?: string | FastApiValidationItem[] | Record<string, unknown>;
    };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (first && typeof first === "object" && ("loc" in first || "msg" in first)) {
        return formatValidationErrors(data.detail as FastApiValidationItem[]);
      }
    }
  } catch {
    // ignore parse errors and use fallback text
  }
  return res.status === 422 ? formatValidationErrors([]) : fallback;
}

export function withProductAuth(init?: RequestInit): RequestInit {
  return mergeProductSessionAuth(init);
}
