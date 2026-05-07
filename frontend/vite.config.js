import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api/v1/agents": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/api/v1/conversations": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/api/v1/session/prompt": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/api": {
        target: "http://localhost:8502",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8502",
        changeOrigin: true,
      },
    },
  },
});
