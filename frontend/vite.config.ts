import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api va a la API local (uvicorn en el puerto 8301; el contenedor web usa el 8300).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8301" },
  },
});
