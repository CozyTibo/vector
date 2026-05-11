import { describe, expect, it } from "vitest";

import {
  CONNECTOR_OAUTH_RETURN_PATH,
  connectorInstallUrl,
  type ConnectorOAuthProvider,
} from "./connectorsClient";

describe("connectorInstallUrl", () => {
  it("targets /connectors/:provider/install on the API base (cortex-backed routes)", () => {
    const base = "https://api.example.com";
    const expectedQuery = new URLSearchParams({ return_to: CONNECTOR_OAUTH_RETURN_PATH }).toString();

    const providers: ConnectorOAuthProvider[] = ["calls", "github", "linear", "notion", "slack"];
    for (const p of providers) {
      expect(connectorInstallUrl(base, p)).toBe(`${base}/connectors/${p}/install?${expectedQuery}`);
    }
  });

  it("adds install_response=json when requested (SPA OAuth bootstrap)", () => {
    const base = "https://api.example.com";
    const url = connectorInstallUrl(base, "slack", CONNECTOR_OAUTH_RETURN_PATH, {
      installResponseJson: true,
    });
    expect(url).toContain("/connectors/slack/install?");
    expect(url).toContain("install_response=json");
  });
});
