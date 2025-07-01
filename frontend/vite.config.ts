import { defineConfig, loadEnv } from "vite";
import path from "path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    // Add this server proxy configuration
    server: {
      proxy: {
        "/api": {
          target: env.VITE_BASE_URL || "http://127.0.0.1:5002", // Default to 5002
          changeOrigin: true,
        },
      },
    },
  };
});
