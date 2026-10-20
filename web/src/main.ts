// Веб-демо cds2astra: PLCopen XML CODESYS -> Astra.IDE в браузере (Pyodide). Файл не покидает вкладку.
import "./style.css";

interface Finding {
  rule: string;
  outcome: string;
  family_outcome: string;
  language: string;
  pou?: string;
  message: string;
  origin: { line?: number };
}
interface Report {
  outcomes: Record<string, number>;
  effort: { p50_h: number; p90_h: number; runs: number; calibration: string; calibrated: boolean };
  matrix: Record<string, Record<string, number>>;
  findings: Finding[];
  tasks: { task: string; before: number | null; after: number; interval_ms: number | null; reason: string }[];
  replacements: { source: string; target: string | null; kind: string; count: number; url: string | null }[];
  io_map: { variable: string; owen: string; regul: string; outcome: string; rule: string; type?: string }[];
  objects: { name: string; kind: string; source: string }[];
  notes: string[];
  source: { ide?: string; ide_version?: string };
}
interface Result {
  report: Report;
  files: Record<string, string>;
  zip?: string;
  zip_sha256?: string;
  version?: string;
}
interface Example {
  id: string;
  title: string;
  klass: string;
  input: string;
  spec?: string;
}

const BASE = import.meta.env.BASE_URL;
const VERIFIED = "Импорт и сборка проверены в Astra.IDE 1.7.2.2 локально, 20.10.2026; на контроллере REGUL — нет.";
const OUTCOME_RU: Record<string, string> = {
  auto: "авто",
  check: "сверить",
  todo: "вручную",
  impossible: "невозможно",
  info: "сведения",
};
const EXAMPLES: Example[] = [
  { id: "boiler", title: "Котельная на ПЛК210", klass: "синтетический слой ОВЕН", input: "boiler/input.xml", spec: "boiler/target.toml" },
  { id: "lang-matrix", title: "Матрица шести языков", klass: "рукописный TC6", input: "lang-matrix/input.xml" },
  { id: "sp18", title: "Проект CODESYS SP18", klass: "экспорт IDE, MIT", input: "sp18/input.xml" },
  { id: "s7-chain", title: "S7 → CODESYS → REGUL", klass: "выход s7-to-codesys 1.0", input: "s7-chain/input.xml" },
];

const $ = <T extends HTMLElement>(sel: string): T => {
  const el = document.querySelector<T>(sel);
  if (!el) throw new Error(sel);
  return el;
};
const esc = (s: unknown): string =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);

let current: Result | null = null;
let inputText = "";
let inputName = "";
let ready = false;
const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });

function setStatus(text: string, kind: "wait" | "ok" | "err" = "wait"): void {
  const el = $("#status");
  el.textContent = text;
  el.dataset.kind = kind;
}

worker.onmessage = (ev: MessageEvent) => {
  const msg = ev.data as { kind: string; payload?: string; message?: string };
  if (msg.kind === "ready") {
    ready = true;
    setStatus("Pyodide готов: отчёт считается в браузере", "ok");
    if (inputText) runLive();
  } else if (msg.kind === "result" && msg.payload) {
    current = JSON.parse(msg.payload) as Result;
    render(true);
    setStatus(`Посчитано в браузере за ${((performance.now() - started) / 1000).toFixed(1)} с`, "ok");
  } else if (msg.kind === "error") {
    setStatus(`Ошибка: ${msg.message ?? ""}`, "err");
  }
};
worker.postMessage({ kind: "boot", base: BASE });

function runLive(spec?: string): void {
  if (!ready) return;
  setStatus("Перенос…", "wait");
  started = performance.now();
  const data = new TextEncoder().encode(inputText).buffer;
  worker.postMessage({ kind: "run", data, name: inputName, spec: spec ?? currentSpec }, [data]);
}

let currentSpec = "";
let started = 0;

async function loadExample(ex: Example): Promise<void> {
  const [inp, rep, spec] = await Promise.all([
    fetch(`${BASE}examples/${ex.input}`).then((r) => r.text()),
    fetch(`${BASE}examples/${ex.id}/result.json`).then((r) => r.json() as Promise<Result>),
    ex.spec ? fetch(`${BASE}examples/${ex.spec}`).then((r) => r.text()) : Promise.resolve(""),
  ]);
  inputText = inp;
  inputName = `${ex.id}.xml`;
  currentSpec = spec;
  current = rep;
  $("#source").textContent = `${ex.title} · ${ex.klass}`;
  render(false);
  if (ready) runLive(spec);
}

function tiles(r: Report): string {
  const order = ["auto", "check", "todo", "impossible", "info"];
  const t = order
    .map((k) => `<div class="tile o-${k}"><span>${OUTCOME_RU[k]}</span><b>${r.outcomes[k] ?? 0}</b></div>`)
    .join("");
  return `${t}<div class="tile acc"><span>P50 / P90, ч · модель</span><b>${r.effort.p50_h} / ${r.effort.p90_h}</b></div>`;
}

function table(head: string[], rows: string[][]): string {
  if (!rows.length) return `<p class="muted">нет данных</p>`;
  return `<div class="wrap"><table><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows
    .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;
}

const oc = (o: string): string => `<span class="o-${esc(o)}">${esc(OUTCOME_RU[o] ?? o)}</span>`;

function crateSvg(r: Report): string {
  const slaves = [...new Set(r.io_map.filter((m) => m.rule === "C2A-IO003").map((m) => m.owen.split(" ")[0]))];
  const local = r.io_map.filter((m) => m.rule === "C2A-IO001").length;
  const mods = slaves.length ? slaves : ["—"];
  const busY = 206;
  const boxes = mods
    .map((m, i) => {
      const x = 370 + i * 130;
      return `<g><rect x="${x}" y="64" width="110" height="64" rx="6" class="mx"/><text x="${x + 55}" y="92" text-anchor="middle">${esc(m)}</text><text x="${x + 55}" y="112" text-anchor="middle" class="sub">Outer Slave OS</text><line x1="${x + 55}" y1="128" x2="${x + 55}" y2="${busY}" class="bus"/></g>`;
    })
    .join("");
  const busEnd = 370 + (mods.length - 1) * 130 + 55;
  const width = Math.max(660, busEnd + 90);
  return `<svg viewBox="0 0 ${width} 240" class="crate" role="img" aria-label="Крейт REGUL R500 и модули Mx210 на линии Modbus TCP">
  <rect x="20" y="30" width="310" height="150" rx="8" class="rack"/>
  <text x="34" y="52" text-anchor="start">REGUL R500 · крейт</text>
  <rect x="34" y="64" width="70" height="100" rx="4" class="cpu"/><text x="69" y="110" text-anchor="middle">ЦП</text><text x="69" y="128" text-anchor="middle" class="sub">R500 61</text>
  <rect x="112" y="64" width="56" height="100" rx="4" class="mod"/><text x="140" y="118" text-anchor="middle" class="sub">DI</text>
  <rect x="176" y="64" width="56" height="100" rx="4" class="mod"/><text x="204" y="118" text-anchor="middle" class="sub">DO</text>
  <rect x="240" y="64" width="76" height="100" rx="4" class="mod"/><text x="278" y="108" text-anchor="middle" class="sub">AT →</text><text x="278" y="124" text-anchor="middle" class="sub">GVL_IO: ${local}</text>
  <line x1="69" y1="164" x2="69" y2="${busY}" class="bus"/><line x1="69" y1="${busY}" x2="${busEnd}" y2="${busY}" class="bus"/>
  <text x="${(370 + busEnd) / 2}" y="${busY + 22}" text-anchor="middle" class="sub">Modbus TCP Master OS → каналы ARRAY OF WORD</text>
  ${boxes}
</svg>`;
}

function codeTab(res: Result): string {
  const out = res.files["astra-import.xml"] ?? "";
  const parse = (xml: string): Map<string, string> => {
    const m = new Map<string, string>();
    const doc = new DOMParser().parseFromString(xml, "application/xml");
    for (const pou of Array.from(doc.getElementsByTagName("pou"))) {
      const st = pou.getElementsByTagName("ST")[0] ?? pou.getElementsByTagName("IL")[0];
      const body = st?.textContent?.trim();
      if (body) m.set(pou.getAttribute("name") ?? "?", body);
    }
    return m;
  };
  const before = parse(inputText);
  const after = parse(out);
  const names = [...after.keys()].filter((n) => before.has(n) && before.get(n) !== after.get(n));
  if (!names.length) return `<p class="muted">Тела ST без изменений.</p>`;
  return names
    .slice(0, 8)
    .map(
      (n) =>
        `<h3>${esc(n)}</h3><div class="diff"><pre><code>${esc(before.get(n))}</code></pre><pre><code>${esc(after.get(n))}</code></pre></div>`,
    )
    .join("");
}

function render(live: boolean): void {
  if (!current) return;
  const r = current.report;
  const byRule = (p: string) => r.findings.filter((f) => f.rule.startsWith(p));
  $("#tab-summary").innerHTML = `
    <div class="tiles">${tiles(r)}</div>
    <p class="muted">${live ? "Посчитано в браузере (Pyodide)" : "Предрасчитанный отчёт — Pyodide загружается"} · файл не покидает браузер.
    Часы — модель (треугольное распределение, ${r.effort.runs} проб${r.effort.calibrated ? `, калибровка: ${esc(r.effort.calibration)}` : ""}).</p>
    <p class="note">${VERIFIED}</p>
    ${table(
      ["правило", "исход", "объект", "сообщение"],
      r.findings.filter((f) => f.outcome !== "info").slice(0, 40).map((f) => [esc(f.rule), oc(f.outcome), esc(f.pou ?? "—"), esc(f.message)]),
    )}
    ${r.notes.length ? `<ul>${r.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}`;
  $("#tab-langs").innerHTML = table(
    ["язык", "авто", "сверить", "вручную", "невозможно", "сведения"],
    Object.entries(r.matrix).map(([l, c]) => [esc(l), ...["auto", "check", "todo", "impossible", "info"].map((k) => String(c[k] ?? 0))]),
  ) + table(["правило", "исход", "объект", "сообщение"], byRule("C2A-LANG").map((f) => [esc(f.rule), oc(f.outcome), esc(f.pou ?? ""), esc(f.message)]));
  $("#tab-libs").innerHTML = table(
    ["источник", "замена", "вид", "мест", "документ"],
    r.replacements.map((x) => [
      `<code>${esc(x.source)}</code>`,
      x.target ? `<code>${esc(x.target)}</code>` : "—",
      esc(x.kind),
      String(x.count),
      x.url ? `<a href="${esc(x.url)}" rel="noopener noreferrer">ОВЕН</a>` : "",
    ]),
  );
  $("#tab-io").innerHTML = crateSvg(r) + table(
    ["переменная", "ОВЕН", "REGUL", "исход"],
    r.io_map.map((m) => [`<code>${esc(m.variable)}</code>`, esc(m.owen), esc(m.regul), oc(m.outcome)]),
  );
  $("#tab-tasks").innerHTML = table(
    ["задача", "интервал, мс", "было", "стало", "почему"],
    r.tasks.map((t) => [esc(t.task), esc(t.interval_ms), esc(t.before), `<b>${esc(t.after)}</b>`, esc(t.reason)]),
  );
  $("#tab-sp18").innerHTML = table(
    ["правило", "исход", "объект", "сообщение"],
    r.findings.filter((f) => /^C2A-SP/.test(f.rule)).map((f) => [esc(f.rule), oc(f.outcome), esc(f.pou ?? ""), esc(f.message)]),
  );
  $("#tab-code").innerHTML = codeTab(current);
  const dl = $("#tab-zip");
  if (current.zip) {
    const bin = Uint8Array.from(atob(current.zip), (c) => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bin], { type: "application/zip" }));
    dl.innerHTML = `<p><a class="btn" id="zip-link" href="${url}" download="cds2astra-result.zip">Скачать zip</a></p>
      <p class="muted">SHA-256: <code>${esc(current.zip_sha256)}</code> — тот же, что у CLI на тех же данных (ZIP без сжатия, фиксированные даты).</p>
      <ul>${Object.keys(current.files).map((f) => `<li><code>${esc(f)}</code></li>`).join("")}</ul>`;
  } else {
    dl.innerHTML = `<p class="muted">Zip появится после расчёта в браузере.</p>`;
  }
}

function showTab(id: string): void {
  document.querySelectorAll<HTMLElement>(".tab").forEach((t) => (t.hidden = t.id !== `tab-${id}`));
  document.querySelectorAll<HTMLButtonElement>("nav.tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === id)));
}

function init(): void {
  const list = $("#examples");
  for (const ex of EXAMPLES) {
    const b = document.createElement("button");
    b.className = "ex";
    b.dataset.example = ex.id;
    b.innerHTML = `${esc(ex.title)}<small>${esc(ex.klass)}</small>`;
    b.onclick = () => void loadExample(ex);
    list.append(b);
  }
  document.querySelectorAll<HTMLButtonElement>("nav.tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab ?? "summary")));
  const file = $<HTMLInputElement>("#file");
  const take = async (f: File) => {
    inputText = await f.text();
    inputName = f.name;
    currentSpec = "";
    $("#source").textContent = `${f.name} · ваш файл`;
    if (ready) runLive("");
    else setStatus("Pyodide ещё загружается — расчёт начнётся сам", "wait");
  };
  file.onchange = () => file.files?.[0] && void take(file.files[0]);
  const drop = $("#drop");
  drop.ondragover = (e) => {
    e.preventDefault();
    drop.classList.add("over");
  };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => {
    e.preventDefault();
    drop.classList.remove("over");
    const f = e.dataTransfer?.files?.[0];
    if (f) void take(f);
  };
  showTab("summary");
  void loadExample(EXAMPLES[0]);
}

init();
