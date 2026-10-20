import { defineConfig } from "vite";

// Демо публикуется на GitHub Pages: https://kr0nsch.github.io/codesys-to-astra/
export default defineConfig({
  base: "/codesys-to-astra/",
  build: { outDir: "dist", emptyOutDir: true, target: "es2022" },
  worker: { format: "es" },
});
