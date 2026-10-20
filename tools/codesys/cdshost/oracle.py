"""Оракул XML (M11): astra-import.xml -> новый проект Astra.IDE 1.7.2.2 (REGUL R500 61) или CODESYS 3.5.17.30
(Control Win V3) -> библиотеки -> импорт -> сверка дерева объектов с отчётом -> задачи -> сборка ->
сопоставление сообщений с находками todo -> обратный экспорт.

Правила итога (PROMPT §8, оракулы 0 и 1): ошибки компиляции допустимы только в объектах с находкой todo
(1:1 по объекту), для auto/check — строго 0; любой объект из отчёта, которого нет в дереве после импорта, —
ошибка (на ImportReporter не полагаемся: IL пропадает молча, ext §3.3).

Цель pool: PVL заменяется GVL без PERSISTENT (в пул PVL не вставить — kns docs/plcopen.md), задач нет.
В CODESYS ссылки на библиотеки РегЛаб `<Lib>, * (Prosoft-Systems Ltd)` подменяются заглушками
`C2aStub_<Lib>` (компания plc-portfolio), соответствие — build/oracle/libsubst.json.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from . import ide_env

TOOLS_CODESYS = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLS_CODESYS.parent.parent
SCRIPT = TOOLS_CODESYS / "xml_oracle_ide.py"
OUT = REPO_ROOT / "build" / "oracle"
ERROR_SEVERITIES = ("Error", "FatalError")
REGLAB_COMPANY = "Prosoft-Systems Ltd"
_PVL_RE = re.compile(r"\s+PERSISTENT\b", re.IGNORECASE)


def pool_variant(xml: bytes) -> bytes:
    """PVL -> GVL: снять persistent="true" и слово PERSISTENT в тексте объявления (точечно, по тексту)."""
    text = xml.decode("utf-8")
    out = []
    pos = 0
    for m in re.finditer(r'<globalVars name="[^"]*"[^>]*persistent="true"[^>]*>', text):
        out.append(text[pos : m.start()])
        out.append(m.group(0).replace(' persistent="true"', ""))
        pos = m.end()
    out.append(text[pos:])
    text = "".join(out)
    text = re.sub(r"(VAR_GLOBAL(?:\s+RETAIN)?)\s+PERSISTENT", r"\1", text)
    text = re.sub(r"VAR_GLOBAL\s+PERSISTENT(\s+RETAIN)?", r"VAR_GLOBAL\1", text)
    return text.encode("utf-8")


def library_specs(ide: str, libraries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Ссылки отчёта (import.libraries) -> описания cds.py; в CODESYS — заглушки вместо библиотек РегЛаб."""
    specs: list[dict[str, Any]] = []
    subst: dict[str, str] = {}
    for lib in libraries:
        name = str(lib["name"])
        ns = str(lib.get("namespace") or "")
        if name.startswith("#"):
            specs.append(ide_env.placeholder_spec(name[1:], ns or None) if name != "#Standard" else ide_env.standard_spec())
            continue
        m = re.match(r"^(.+?),\s*([^\s(]+)\s*\((.+)\)\s*$", name)
        if not m:
            continue
        title, _version, company = m.group(1), m.group(2), m.group(3)
        if company == REGLAB_COMPANY and ide == "codesys":
            stub = f"C2aStub_{title}"
            subst[name] = f"{stub}, * (plc-portfolio)"
            specs.append(ide_env.library_spec(stub, "plc-portfolio", "*", ns or title))
        else:
            specs.append(ide_env.library_spec(title, company, "*", ns or None))
    return specs, subst


def expected_objects(report: dict[str, Any]) -> list[str]:
    return [str(o["name"]) for o in report.get("objects", [])]


def todo_objects(report: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for f in report.get("findings", []):
        if f.get("outcome") in ("todo", "impossible") and f.get("pou"):
            out.add(str(f["pou"]).split(".")[0].lower())
    return out


def tasks_for(report: dict[str, Any], objects: list[str]) -> list[dict[str, Any]]:
    """Задачи из таблицы отчёта (приоритеты REGUL); PRG_C2aIoUpdate — первой в первой задаче."""
    names = {o.lower() for o in objects}
    tasks: list[dict[str, Any]] = []
    for t in report.get("tasks", []):
        pous = [p for p in t.get("pous", []) if p.lower() in names]
        tasks.append({
            "name": t["task"],
            "interval_ms": float(t.get("interval_ms") or 20),
            "priority": t["after"],
            "pous": pous,
        })
    if not tasks:
        progs = [o["name"] for o in report.get("objects", []) if o.get("kind") == "program"]
        tasks = [{"name": "MainTask", "interval_ms": 20.0, "priority": 2, "pous": progs}]
    if "prg_c2aioupdate" in names:
        for t in tasks:
            t["pous"] = [p for p in t["pous"] if p.lower() != "prg_c2aioupdate"]
        tasks[0]["pous"].insert(0, "PRG_C2aIoUpdate")
    return tasks


def message_object(msg: dict[str, Any]) -> str:
    obj = str(msg.get("object") or "")
    return obj.split(".")[0].split(" ")[0].lower()


def evaluate(case: dict[str, Any], report: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    dumped = {"/".join(o["path"]).lower(): o for o in raw.get("objects", [])}
    top = {o["path"][-1].lower() for o in raw.get("objects", []) if o.get("kind") not in ("folder", "libman", "other")}
    missing = [n for n in expected_objects(report) if n.lower() not in top]
    msgs = raw.get("messages") or []
    errors = [m for m in msgs if m.get("severity") in ERROR_SEVERITIES]
    warnings = [m for m in msgs if m.get("severity") == "Warning"]
    allowed = todo_objects(report)
    unexpected = [m for m in errors if message_object(m) not in allowed]
    import_errors = [m for m in raw.get("import_messages", []) if m.get("level") in ("error", "skipped", "conflict")]
    ok = bool(raw.get("ok")) and not missing and not unexpected and not import_errors and not raw.get("import_exception")
    return {
        "case": case["name"],
        "ide": case["ide"],
        "target": case["target"],
        "form": case["form"],
        "ok": ok,
        "objects_expected": len(expected_objects(report)),
        "objects_found": len(dumped),
        "missing": missing,
        "import_errors": [m.get("text") for m in import_errors],
        "import_exception": raw.get("import_exception"),
        "errors": [_fmt(m) for m in errors],
        "errors_unexpected": [_fmt(m) for m in unexpected],
        "warnings": [_fmt(m) for m in warnings],
        "allowed_objects": sorted(allowed),
        "summary_line": (raw.get("summary") or {}).get("summary_line"),
        "libraries": raw.get("libraries_after"),
        "tasks": raw.get("tasks_after_sync") or raw.get("tasks_after_import"),
        "export": raw.get("export"),
        "export_error": raw.get("export_error"),
        "error": raw.get("error"),
        "seconds": raw.get("seconds"),
    }


def _fmt(m: dict[str, Any]) -> str:
    where = f" [{m.get('object')}, {m.get('position')}]" if m.get("object") else ""
    code = f"{m.get('code')} " if m.get("code") else ""
    return f"{m.get('severity')} {code}{m.get('text')}{where}"


def run(
    ide: str,
    xml_path: Path,
    report_path: Path,
    targets: list[str],
    case_name: str,
    timeout_s: float = 1800.0,
) -> list[dict[str, Any]]:
    OUT.mkdir(parents=True, exist_ok=True)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    xml = xml_path.read_bytes()
    specs, subst = library_specs(ide, report.get("import", {}).get("libraries", []))
    work = OUT / "work"
    work.mkdir(parents=True, exist_ok=True)
    cases = []
    for target in targets:
        if target == "pool":
            src = work / f"{case_name}-{ide}-pool.xml"
            src.write_bytes(pool_variant(xml))
        else:
            src = xml_path
        cases.append({
            "name": f"{case_name}-{ide}-pous-{target}",
            "ide": ide,
            "form": "pous",
            "xml": str(src.resolve()),
            "target": target,
            "device": ide_env.ide(ide)["device"] if target == "app" else None,
            "project": str((work / f"{case_name}-{ide}-{target}.project").resolve()),
            "tasks": tasks_for(report, expected_objects(report)) if target == "app" else None,
            "export": str((OUT / "export" / f"{case_name}-{ide}-{target}.xml").resolve()),
            "build": True,
        })
    job = {"repository": "System", "libraries": specs, "cases": cases}
    started = time.time()
    data = ide_env.run_ide_job(ide, SCRIPT, job, work, f"{case_name}-{ide}", timeout_s)
    by_name = {c["name"]: c for c in data.get("cases", [])}
    results = []
    for case in cases:
        raw = by_name.get(case["name"], {"ok": False, "error": data.get("error") or "нет результата"})
        res = evaluate(case, report, raw)
        res["ide_title"] = ide_env.ide(ide)["title"]
        res["date"] = time.strftime("%Y-%m-%d")
        res["xml"] = str(xml_path)
        res["libsubst"] = subst
        res["elapsed_s"] = round(time.time() - started, 1)
        (OUT / f"{case_name}-{ide}-pous-{case['target']}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        results.append(res)
    if subst:
        (OUT / "libsubst.json").write_text(json.dumps(subst, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return results
