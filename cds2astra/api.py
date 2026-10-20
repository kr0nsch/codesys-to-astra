"""Программный интерфейс: inventory, analyze, migrate (файлы результата в памяти), zip.

Ядро без сети и процессов: тот же код работает в Pyodide (веб-демо). Вход — байты PLCopen XML или
раскладка plc-repo-template (словарь «относительный путь -> текст»); конфигурация — TOML.
"""

from __future__ import annotations

import io
import json
import tomllib
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from . import TOOL_NAME, __version__, libmap, profiles
from . import io as iox
from .emit import report as rep
from .emit import steps
from .emit.xmlout import emit_astra, emit_preserve
from .estimate import estimate
from .importers import plcopen
from .ir.model import Project
from .rules import run_all
from .session import Options, Session, TargetSpec

__all__ = ["MigrateResult", "Options", "Session", "TargetSpec", "analyze", "inventory", "migrate", "run", "to_zip"]

ZIP_DATE = (1980, 1, 1, 0, 0, 0)
DEFAULT_TARGET = "astra-1.7.2.2"


@dataclass
class MigrateResult:
    files: dict[str, bytes] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)
    session: Session | None = None


def load_project(data: bytes, name: str = "input.xml") -> Project:
    return plcopen.load(data, name)


def layout_to_xml(files: dict[str, str], name: str = "layout") -> bytes:
    """Раскладка plc-repo-template (относительные пути src/... -> текст) -> PLCopen XML (tc6_0200)."""
    import os
    import tempfile

    from .importers.layout import st_to_plcopen as S

    with tempfile.TemporaryDirectory() as tmp:
        for rel, text in files.items():
            path = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        opts = S.Options(namespace=S.NS_0200, project_name=name, timestamp="1970-01-01T00:00:00")
        res = S.convert_layout(tmp, opts)
        if res.errors:
            raise ValueError("ошибки раскладки: " + "; ".join(i.format() for i in res.errors))
        return res.xml.encode("utf-8")


def inventory(p: Project) -> dict[str, Any]:
    allp = p.all_pous()
    langs = Counter(x.body.language for x in allp if x.body is not None)
    return {
        "file": p.file,
        "product": p.product,
        "product_version": p.product_version,
        "namespace": p.namespace.rsplit("/", 1)[-1],
        "placements": p.placements,
        "pous": len([x for x in p.pous if x.kind != "interface"]),
        "interfaces": len([x for x in p.pous if x.kind == "interface"]),
        "actions": len([x for x in allp if x.kind == "action"]),
        "transitions": len([x for x in allp if x.kind == "transition"]),
        "methods": len([x for x in allp if x.kind == "method"]),
        "properties": len([x for x in allp if x.kind == "property"]),
        "bodies": dict(sorted(langs.items())),
        "cfc_bodies": langs.get("CFC", 0),
        "gvls": len(p.gvls),
        "duts": len(p.duts),
        "tasks": [
            {"name": t.name, "priority": t.priority, "interval_ms": t.interval_ms, "kind": t.kind} for t in p.tasks
        ],
        "libraries": len(p.libraries),
        "devices": len(p.all_devices()),
        "device_mappings": sum(len(d.mappings) for d in p.all_devices()),
        "unknown_adddata": len(p.unknown),
        "plaintext": p.has_plaintext,
        "issues": [i.code for i in p.issues],
    }


def make_session(
    p: Project,
    target: str = DEFAULT_TARGET,
    target_text: str | None = None,
    spec_text: str | None = None,
    io_list_text: str | None = None,
    options: Options | None = None,
) -> Session:
    prof = profiles.load(target, target_text)
    sources = [x for x in profiles.all_builtin() if x.kind == "source"]
    spec = TargetSpec.from_dict(tomllib.loads(spec_text)) if spec_text else TargetSpec()
    io_list = None
    if io_list_text:
        io_list = json.loads(io_list_text) if io_list_text.lstrip().startswith("{") else tomllib.loads(io_list_text)
    return Session(p, prof, sources, libmap.load(), spec, options or Options(), io_list)


def analyze(s: Session) -> Session:
    run_all(s)
    return s


def _libraries_out(s: Session) -> list[dict[str, str]]:
    libs: list[dict[str, str]] = [
        {"name": "#Standard", "namespace": "Standard", "why": "Standard (TON, R_TRIG, CONCAT…) — плейсхолдер профиля"},
    ]
    uses_compat = any(
        f.rule in ("C2A-LIB001", "C2A-IO002", "C2A-IO003") and f.outcome in ("auto", "check") for f in s.findings
    )
    if uses_compat:
        libs.append(
            {
                "name": "AstraCompat, * (plc-portfolio)",
                "namespace": "AstraCompat",
                "why": "замены ОВЕН (префикс C2a): установить .library из релиза cds2astra",
            }
        )
    if uses_compat:
        libs.append(
            {
                "name": "#SysTimeRtc",
                "namespace": "SysTimeRtc",
                "why": "SysTimeRtc — зависимость AstraCompat (FB_C2aRtc); плейсхолдер нужен и проекту",
            }
        )
    titles = {x.title.lower() for x in s.project.libraries}
    if "util" in titles or uses_compat:
        libs.append({"name": "#Util", "namespace": "Util", "why": "Util (HYSTERESIS, PID) — нужен и AstraCompat"})
    if any("eMbSt" in line for line in s.gvl_io):
        libs.append(
            {
                "name": "PsIoDrvModbusTcpMaster_OS, * (Prosoft-Systems Ltd)",
                "namespace": "PsIoDrvModbusTcpMaster_OS",
                "why": "тип ChannelStatus каналов Modbus; ставится устройством Modbus TCP Master OS",
            }
        )
    for ref in s.project.libraries:
        if s.libmap.vendor_library(ref.title) is not None or ref.title.lower() in ("standard", "util"):
            continue
        if ref.placeholder and ref.title.lower() in ("iostandard", "3slicense", "cds_memman", "breakpointlogging"):
            continue
        libs.append({"name": ref.name, "namespace": ref.namespace or "", "why": "из исходного проекта"})
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for lib in libs:
        if lib["name"].lower() in seen:
            continue
        seen.add(lib["name"].lower())
        out.append(lib)
    rank = {"#standard": 0, "#util": 1, "#systimertc": 2}

    def key(lib: dict[str, str]) -> tuple[int, str]:
        name = lib["name"].lower()
        if name in rank:
            return rank[name], name
        if name.startswith("astracompat"):
            return 3, name
        return 4, name

    return sorted(out, key=key)


def _trace(s: Session, objects: list[dict[str, str]]) -> dict[str, Any]:
    by_obj: dict[str, list[dict[str, Any]]] = {}
    for f in sorted(s.findings, key=lambda x: x.sort_key):
        key = (f.pou or "(проект)").split(".")[0]
        by_obj.setdefault(key, []).append({"rule": f.rule, "outcome": f.outcome, "line": f.line, "path": f.pou})
    items = []
    for o in objects:
        items.append(
            {
                "target": o["name"],
                "kind": o["kind"],
                "source": o["name"] if o["source"] != "cds2astra" else None,
                "generated": o["source"] == "cds2astra",
                "findings": by_obj.get(o["name"], []),
            }
        )
    return {
        "format": "cds2astra-trace/1",
        "tool": f"{TOOL_NAME} {__version__}",
        "objects": items,
        "project": by_obj.get("(проект)", []),
    }


def migrate(s: Session, with_devices: bool = True) -> MigrateResult:
    if not s.findings:
        analyze(s)
    s.libraries_out = _libraries_out(s)
    edits = s.resolve()
    emitted = emit_astra(s, edits) if s.options.mode == "astra" else emit_preserve(s, edits)
    if s.options.mode == "preserve":
        emitted.objects = [{"name": p.name, "kind": p.kind, "source": p.placement} for p in s.project.pous] + [
            {"name": g.name, "kind": "gvl", "source": g.placement} for g in s.project.gvls
        ]
    eff = estimate(s.findings)
    report = rep.build_json(s, eff, emitted.objects)
    files: dict[str, bytes] = {}
    files["astra-import.xml"] = emitted.xml
    files["MIGRATION_REPORT.json"] = rep.to_json_bytes(report)
    files["MIGRATION_REPORT.md"] = rep.build_md(report).encode("utf-8")
    files["MIGRATION_REPORT.html"] = rep.build_html(report).encode("utf-8")
    files["IMPORT_STEPS.md"] = steps.build(s, report).encode("utf-8")
    files["trace.json"] = (json.dumps(_trace(s, emitted.objects), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files["io-map.csv"] = iox.iomap_csv(s.io_map)
    files["io-map.md"] = iox.iomap_md(s.io_map).encode("utf-8")
    slaves = [{"name": r["source"].split("/")[0]} for r in s.io_map if r.get("rule") == "C2A-IO003"]
    uniq = list({sl["name"]: sl for sl in slaves}.values())
    if with_devices and uniq:
        files["regul-devices.xml"] = iox.regul_devices(s.spec.cpu, uniq)
    return MigrateResult(files, report, s)


def to_zip(files: dict[str, bytes]) -> bytes:
    """ZIP_STORED, имена по порядку, фиксированные date_time и external_attr — одинаковый SHA-256 везде."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            zf.writestr(info, files[name])
    return buf.getvalue()


def run(
    data: bytes,
    name: str = "input.xml",
    target: str = DEFAULT_TARGET,
    spec_text: str | None = None,
    options: Options | None = None,
    io_list_text: str | None = None,
) -> MigrateResult:
    """Одна функция для веб-демо: байты XML -> файлы результата."""
    p = load_project(data, name)
    s = make_session(p, target, None, spec_text, io_list_text, options)
    analyze(s)
    return migrate(s)
