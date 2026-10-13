import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Панель обслуживается с того же домена, что и API (/panel/ → nginx, /api/ → Django),
// поэтому cookie сессии и CSRF работают без CORS. В dev то же даёт прокси Vite.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const backend = env.VITE_BACKEND_URL ?? "http://localhost:8000";
  return {
    base: "/panel/",
    plugins: [react()],
    server: {
      port: 5173,
      // Host не подменяется (changeOrigin: false): Origin и Host совпадают, CSRF-проверка Django проходит.
      proxy: { "/api": { target: backend, changeOrigin: false } },
    },
  };
});
