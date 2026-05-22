import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import type { IncomingMessage } from "node:http";
import { defineConfig, loadEnv } from "vite";

/** Let Vite serve the SPA for browser navigations; proxy only API fetches. */
function apiProxyBypass(req: IncomingMessage): string | undefined {
  const accept = req.headers.accept ?? "";
  if (accept.includes("text/html")) {
    return "/index.html";
  }
  return undefined;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + "/..", "");
  const apiProxyTarget =
    env.VITE_API_PROXY_TARGET?.trim() ||
    env.VITE_API_BASE_URL?.trim() ||
    "http://127.0.0.1:8000";

  const apiProxy = {
    target: apiProxyTarget,
    changeOrigin: true,
    bypass: apiProxyBypass,
  };

  return {
    plugins: [react(), tailwindcss()],
    /** One React instance for the whole app — avoids "Invalid hook call" / useContext null with react-query. */
    resolve: {
      dedupe: ["react", "react-dom"],
    },
    optimizeDeps: {
      include: ["react", "react-dom", "@tanstack/react-query"],
    },
    build: {
      outDir: "dist",
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/admin": apiProxy,
        "/auth": apiProxy,
        "/connectors": apiProxy,
        "/health": apiProxy,
        "/me": apiProxy,
        "/onboarding": apiProxy,
      },
    },
  };
});
