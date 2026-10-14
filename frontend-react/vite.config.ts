import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // 127.0.0.1 sart: uvicorn yalnizca IPv4 dinler, "localhost" IPv6'ya cozulebilir (502).
      "/api": "http://127.0.0.1:8124",
    },
  },
});
