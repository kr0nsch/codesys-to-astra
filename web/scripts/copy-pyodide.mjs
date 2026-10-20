// Файлы Pyodide из node_modules -> dist/pyodide (без CDN: демо не обращается к чужим доменам).
import { cpSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";

const src = join("node_modules", "pyodide");
const dst = join("dist", "pyodide");
if (!existsSync(src)) {
  console.error("нет node_modules/pyodide: npm ci");
  process.exit(1);
}
mkdirSync(dst, { recursive: true });
const keep = /\.(mjs|js|wasm|json|zip|whl|tar)$/;
for (const name of readdirSync(src)) {
  if (keep.test(name) && !name.endsWith(".d.ts")) cpSync(join(src, name), join(dst, name));
}
console.log(`pyodide -> ${dst}`);
