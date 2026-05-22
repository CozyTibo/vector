import { describe, expect, it, vi } from "vitest";

import * as canonicalApi from "./canonicalApi";
import {
  adminApiPath,
  normalizeApiBase,
  resolveAdminRequestUrl,
  tenantIdFromApiBase,
} from "./adminApiUrl";

const TID = "c08ef32b-f89a-40f6-9566-e19b5329436f";

describe("adminApiUrl", () => {
  it("rewrites SPA-relative cortex overview paths to pipeline overview", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue("https://api.myvector.co");
    expect(adminApiPath(TID, "/cortex/overview")).toBe(
      `/admin/tenants/${TID}/cortex/pipeline/overview`,
    );
    expect(adminApiPath(TID, "/cortex/overview/phases")).toBe(
      `/admin/tenants/${TID}/cortex/pipeline/overview/phases`,
    );
  });

  it("rewrites full legacy cortex overview admin paths", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue("https://api.myvector.co");
    expect(adminApiPath(TID, `/admin/tenants/${TID}/cortex/overview`)).toBe(
      `/admin/tenants/${TID}/cortex/pipeline/overview`,
    );
  });

  it("strips per-tenant cortex suffix from misconfigured API base", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue(
      `https://api.myvector.co/admin/tenants/${TID}/cortex`,
    );
    expect(normalizeApiBase()).toBe("https://api.myvector.co");
    expect(tenantIdFromApiBase()).toBe(TID);
    expect(resolveAdminRequestUrl("/overview")).toBe(
      `https://api.myvector.co/admin/tenants/${TID}/cortex/pipeline/overview`,
    );
    expect(
      resolveAdminRequestUrl(adminApiPath(TID, "/cortex/pipeline/overview/phases")),
    ).toBe(
      `https://api.myvector.co/admin/tenants/${TID}/cortex/pipeline/overview/phases`,
    );
  });
});
