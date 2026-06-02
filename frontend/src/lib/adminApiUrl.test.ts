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

  it("strips deep tenant paths from misconfigured API base", () => {
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

  it("does not rewrite execution-surfaces API paths", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue("https://api.myvector.co");
    const path = `/admin/tenants/${TID}/cortex/execution-surfaces/overview`;
    expect(resolveAdminRequestUrl(path)).toBe(`https://api.myvector.co${path}`);
  });

  it("maps SPA execution-surfaces route query to overview API path", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue("https://api.myvector.co");
    const spaPath = `/admin/tenants/${TID}/cortex/execution-surfaces?tab=overview&sort=name&entity_type=deployment&hours=720`;
    expect(resolveAdminRequestUrl(spaPath, TID)).toBe(
      `https://api.myvector.co/admin/tenants/${TID}/cortex/execution-surfaces/overview`,
    );
  });

  it("builds execution-surfaces paths without pipeline rewrite", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue("https://api.myvector.co");
    expect(adminApiPath(TID, "/execution-surfaces/overview")).toBe(
      `/admin/tenants/${TID}/cortex/execution-surfaces/overview`,
    );
    expect(
      resolveAdminRequestUrl(
        `/admin/tenants/${TID}/cortex/execution-surfaces/overview`,
        TID,
      ),
    ).toBe(`https://api.myvector.co/admin/tenants/${TID}/cortex/execution-surfaces/overview`);
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue(
      `https://api.myvector.co/admin/tenants/${TID}/cortex/execution-surfaces`,
    );
    expect(
      resolveAdminRequestUrl(
        `/admin/tenants/${TID}/cortex/execution-surfaces?tab=overview&sort=name`,
        TID,
      ),
    ).toBe(`https://api.myvector.co/admin/tenants/${TID}/cortex/execution-surfaces/overview`);
  });

  it("repairs malformed /admin/surfaces paths from misconfigured tenant bases", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue("https://api.myvector.co/admin");
    expect(resolveAdminRequestUrl("/admin/surfaces/overview", TID)).toBe(
      `https://api.myvector.co/admin/tenants/${TID}/cortex/execution-surfaces/overview`,
    );
    expect(resolveAdminRequestUrl("/surfaces/overview", TID)).toBe(
      `https://api.myvector.co/admin/tenants/${TID}/cortex/execution-surfaces/overview`,
    );
  });

  it("maps overview slice suffixes when API base ends in cortex overview", () => {
    vi.spyOn(canonicalApi, "getApiBase").mockReturnValue(
      `http://localhost:8080/admin/tenants/${TID}/cortex/overview`,
    );
    expect(resolveAdminRequestUrl("/phases")).toBe(
      `http://localhost:8080/admin/tenants/${TID}/cortex/pipeline/overview/phases`,
    );
    expect(resolveAdminRequestUrl("/ingestion")).toBe(
      `http://localhost:8080/admin/tenants/${TID}/cortex/pipeline/overview/ingestion`,
    );
  });
});
