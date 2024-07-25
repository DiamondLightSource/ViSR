import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const baseUrlCopy = "http://127.0.0.1:8000";
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: baseUrlCopy,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "ws://localhost:8000/ws",
        changeOrigin: true,
        rewriteWsOrigin: true,
        ws: true, // Enable WebSocket proxying
        rewrite: (path) => path.replace(/^\/ws/, ""),
      },
    },
  },
});
