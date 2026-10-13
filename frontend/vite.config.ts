import { defineConfig } from "vite";

// Every /api/* request from the frontend is forwarded to Django (port 8000)
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
