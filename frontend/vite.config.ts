import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + "/..", "");
  const apiProxyTarget =
    env.VITE_API_PROXY_TARGET?.trim() ||
    env.VITE_API_BASE_URL?.trim() ||
    "http://127.0.0.1:8000";

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
        "/admin": { target: apiProxyTarget, changeOrigin: true },
        "/auth": { target: apiProxyTarget, changeOrigin: true },
        "/connectors": { target: apiProxyTarget, changeOrigin: true },
        "/health": { target: apiProxyTarget, changeOrigin: true },
        "/me": { target: apiProxyTarget, changeOrigin: true },
        "/onboarding": { target: apiProxyTarget, changeOrigin: true },
      },
    },
  };
});
