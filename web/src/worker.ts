// Worker с Pyodide: тот же Python-код cds2astra, что в CLI. Файл пользователя не покидает вкладку.
/// <reference lib="webworker" />

interface PyodideApi {
  unpackArchive(buffer: ArrayBuffer, format: string, options?: { extractDir?: string }): void;
  runPython(code: string): unknown;
  globals: { set(name: string, value: unknown): void };
}

type LoadPyodide = (opts: { indexURL: string }) => Promise<PyodideApi>;

const ctx = self as unknown as DedicatedWorkerGlobalScope;
let pyodide: PyodideApi | null = null;

async function boot(base: string): Promise<void> {
  const mod = (await import(/* @vite-ignore */ `${base}pyodide/pyodide.mjs`)) as { loadPyodide: LoadPyodide };
  pyodide = await mod.loadPyodide({ indexURL: `${base}pyodide/` });
  const pkg = await fetch(`${base}cds2astra.zip`);
  if (!pkg.ok) throw new Error(`cds2astra.zip: HTTP ${pkg.status}`);
  pyodide.unpackArchive(await pkg.arrayBuffer(), "zip", { extractDir: "/home/pyodide" });
  pyodide.runPython(`
import sys, json, base64, hashlib
sys.path.insert(0, "/home/pyodide")
from cds2astra import api, __version__
from cds2astra.session import Options

def c2a_run(data, name, spec):
    res = api.run(bytes(data), name, spec_text=spec or None, options=Options(source_date="1970-01-01T00:00:00"))
    z = api.to_zip(res.files)
    files = {k: v.decode("utf-8", "replace") for k, v in res.files.items() if not k.endswith(".zip")}
    return json.dumps({"report": res.report, "files": files, "zip": base64.b64encode(z).decode(),
                       "zip_sha256": hashlib.sha256(z).hexdigest(), "version": __version__}, ensure_ascii=False)
`);
}

ctx.onmessage = async (ev: MessageEvent) => {
  const msg = ev.data as { kind: string; base?: string; data?: ArrayBuffer; name?: string; spec?: string };
  try {
    if (msg.kind === "boot") {
      await boot(msg.base ?? "./");
      ctx.postMessage({ kind: "ready" });
      return;
    }
    if (msg.kind === "run" && pyodide) {
      pyodide.globals.set("c2a_data", new Uint8Array(msg.data ?? new ArrayBuffer(0)));
      pyodide.globals.set("c2a_name", msg.name ?? "input.xml");
      pyodide.globals.set("c2a_spec", msg.spec ?? "");
      const out = pyodide.runPython("c2a_run(c2a_data.to_py(), c2a_name, c2a_spec)") as string;
      ctx.postMessage({ kind: "result", payload: out });
    }
  } catch (err) {
    ctx.postMessage({ kind: "error", message: String(err) });
  }
};
