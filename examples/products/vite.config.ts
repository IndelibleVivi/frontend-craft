import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  root: "music-library",
  base: "./",
  plugins: [react()],
  build: { outDir: "../dist/music-library", emptyOutDir: true },
});
