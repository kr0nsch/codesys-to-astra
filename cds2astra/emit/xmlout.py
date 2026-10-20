"""Эмиттер PLCopen XML: режимы preserve (сшивка исходных байтов) и astra (форма pous для импорта в Astra.IDE).

preserve — исходный файл с правками на месте; без правил выход побайтно равен входу (тест round-trip).
astra — новый документ из байтовых срезов исходных объектов (с правками): POU и DUT — в types,
GVL, интерфейсы и объединения — в addData проекта; устройства и задачи в файл импорта не идут (проба P1/P2:
форма resource с конфигурацией не импортируется ни в Astra.IDE 1.7.2.2, ни в CODESYS 3.5.17.30; задачи
создаются по IMPORT_STEPS — проба P6). Созданные объекты (GVL_IO, PRG_C2aIoUpdate) пишет конвертер
раскладки (UUID5 ObjectId), существующие ObjectId сохраняются. Пересериализации ElementTree нет.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

from .. import TOOL_NAME, __version__
from .. import xmltree as X
from ..importers.layout import st_to_plcopen as S
from ..importers.layout import stlayout as L
from ..session import ByteEdit, Session, apply_bytes

NS = {"tc6_0200": "http://www.plcopen.org/xml/tc6_0200", "tc6_0201": "http://www.plcopen.org/xml/tc6_0201"}
CDS = "http://www.3s-software.com/plcopenxml/"


@dataclass
class EmitResult:
    xml: bytes
    objects: list[dict[str, str]] = field(default_factory=list)  # {name, kind, source, placement}


def header_comment(s: Session) -> str:
    if s.project.product == TOOL_NAME:
        # вход уже создан cds2astra (повторный прогон): заголовок исходника сохраняется — идемпотентность
        ch = s.project.doc.root.child("contentHeader")
        com = ch.child("Comment") if ch is not None else None
        if com is not None and com.text.startswith("создано"):
            return com.text
    sha = hashlib.sha256(s.project.doc.raw).hexdigest()
    src = s.project.file.replace("\\", "/").rsplit("/", 1)[-1]
    return f"создано {TOOL_NAME} {__version__} · источник {src} · SHA-256 {sha}"


def emit_preserve(s: Session, edits: Sequence[ByteEdit]) -> EmitResult:
    return EmitResult(apply_bytes(s.project.doc.raw, edits))


def _slice(s: Session, el: X.Elem, edits: Sequence[ByteEdit]) -> str:
    return apply_bytes(s.project.doc.raw, edits, el.start, el.end).decode("utf-8")


def _generated(s: Session) -> tuple[list[str], list[str]]:
    """GVL_IO и PRG_C2aIoUpdate через конвертер раскладки: (globalVars-элементы, pou-элементы)."""
    objs: list[L.StObject] = []
    names = s.project.object_names()
    if s.gvl_io and "gvl_io" not in names:
        decl = (
            f"// GVL_IO — создано {TOOL_NAME} {__version__}: переменные с AT-адресами источника и каналы Modbus REGUL\n"
            "// Привязка к каналам модулей и Modbus — по io-map.csv (мастер конфигурации Astra.IDE)\n"
            "VAR_GLOBAL\n" + "\n".join(s.gvl_io) + "\nEND_VAR\n"
        )
        objs.append(L.StObject(L.KIND_GVL, "GVL_IO", decl, []))
    if s.io_update_body and "prg_c2aioupdate" not in names:
        decl = (
            f"// PRG_C2aIoUpdate — создано {TOOL_NAME} {__version__}: замены узлов таргета ОВЕН, распаковка каналов\n"
            "// Modbus REGUL и проверка достоверности. Вызывать первым в задаче, где опрашивался ввод-вывод.\n"
            "PROGRAM PRG_C2aIoUpdate\nVAR\n" + "\n".join(s.io_update_decl) + "\nEND_VAR\n"
        )
        impl = "\n".join(s.io_update_body) + "\n"
        objs.append(L.StObject(L.KIND_POU, "PRG_C2aIoUpdate", decl, [], impl=impl, pou_kind=L.POU_PROGRAM))
    if not objs:
        return [], []
    opts = S.Options(
        namespace=NS[s.options.namespace], project_name="c2a", timestamp=s.options.source_date, folders=False
    )
    res = S.convert_objects([(o, []) for o in objs], opts)
    doc = X.parse(res.xml.encode("utf-8"))
    raw = doc.raw
    gvls = [
        raw[e.start : e.end].decode("utf-8") for e in doc.root.iter("globalVars") if e.parent and e.parent.tag == "data"
    ]
    pous = [raw[e.start : e.end].decode("utf-8") for e in doc.root.iter("pou")]
    return gvls, pous


def _libraries_xml(s: Session, ind: str) -> str:
    rows = []
    for lib in s.libraries_out:
        attrs = f'Name="{X.escape_attr(lib["name"])}"'
        if lib.get("namespace"):
            attrs += f' Namespace="{X.escape_attr(lib["namespace"])}"'
        if lib.get("resolution"):
            attrs += f' DefaultResolution="{X.escape_attr(lib["resolution"])}"'
        rows.append(f"{ind}      <Library {attrs} />")
    if not rows:
        return ""
    return (
        f'{ind}<data name="{CDS}libraries" handleUnknown="implementation">\n'
        f"{ind}  <Libraries>\n" + "\n".join(rows) + f"\n{ind}  </Libraries>\n{ind}</data>\n"
    )


def emit_astra(s: Session, edits: Sequence[ByteEdit]) -> EmitResult:
    p = s.project
    ns = NS[s.options.namespace]
    res = EmitResult(b"")
    duts: list[str] = []
    pous: list[str] = []
    gvls: list[str] = []
    itfs: list[str] = []
    unions: list[str] = []
    for d in p.duts:
        if id(d.elem) in s.dropped_objects:
            continue
        (unions if d.elem.tag == "union" else duts).append(_slice(s, d.elem, edits))
        res.objects.append({"name": d.name, "kind": "dut", "source": d.placement})
    for pou in p.pous:
        if id(pou.elem) in s.dropped_objects:
            continue
        if pou.kind == "interface":
            itfs.append(_slice(s, pou.elem, edits))
        else:
            pous.append(_slice(s, pou.elem, edits))
        res.objects.append({"name": pou.name, "kind": pou.kind, "source": pou.placement})
    for g in p.gvls:
        if id(g.elem) in s.dropped_objects:
            continue
        gvls.append(_slice(s, g.elem, edits))
        res.objects.append({"name": g.name, "kind": "pvl" if g.persistent else "gvl", "source": g.placement})
    gen_gvls, gen_pous = _generated(s)
    for text in gen_gvls:
        gvls.append(text)
        res.objects.append({"name": "GVL_IO", "kind": "gvl", "source": "cds2astra"})
    for text in gen_pous:
        pous.append(text)
        res.objects.append({"name": "PRG_C2aIoUpdate", "kind": "program", "source": "cds2astra"})
    ch = p.doc.root.child("contentHeader")
    coord = ""
    if ch is not None:
        ci = ch.child("coordinateInfo")
        if ci is not None:
            coord = "    " + p.doc.raw[ci.start : ci.end].decode("utf-8") + "\n"
    if not coord:
        coord = (
            '    <coordinateInfo>\n      <fbd>\n        <scaling x="1" y="1" />\n      </fbd>\n'
            '      <ld>\n        <scaling x="1" y="1" />\n      </ld>\n'
            '      <sfc>\n        <scaling x="1" y="1" />\n      </sfc>\n    </coordinateInfo>\n'
        )
    name = X.escape_attr(p.project_name or "project")
    date = s.options.source_date
    out: list[str] = [
        '<?xml version="1.0" encoding="utf-8"?>\n',
        f'<project xmlns="{ns}">\n',
        f'  <fileHeader companyName="plc-portfolio" productName="{TOOL_NAME}" productVersion="{TOOL_NAME} {__version__}" '
        f'creationDateTime="{date}" />\n',
        f'  <contentHeader name="{name}" modificationDateTime="{date}">\n',
        f"    <Comment>{X.escape_text(header_comment(s)).decode()}</Comment>\n",
        coord,
        "  </contentHeader>\n",
        "  <types>\n",
    ]
    if duts:
        out.append("    <dataTypes>\n" + "".join(f"      {d}\n" for d in duts) + "    </dataTypes>\n")
    else:
        out.append("    <dataTypes />\n")
    if pous:
        out.append("    <pous>\n" + "".join(f"      {x}\n" for x in pous) + "    </pous>\n")
    else:
        out.append("    <pous />\n")
    out.append("  </types>\n  <instances>\n    <configurations />\n  </instances>\n  <addData>\n")
    for gtext in gvls:
        out.append(f'    <data name="{CDS}globalvars" handleUnknown="implementation">\n      {gtext}\n    </data>\n')
    for u in unions:
        out.append(f'    <data name="{CDS}union" handleUnknown="implementation">\n      {u}\n    </data>\n')
    for i in itfs:
        out.append(f'    <data name="{CDS}interface" handleUnknown="implementation">\n      {i}\n    </data>\n')
    # Ссылки на библиотеки в файл импорта не пишутся: импорт их не создаёт (проба P3), а ссылка без
    # DefaultResolution ломает импорт («Не удалось создать объект 'Менеджер библиотек'», Astra.IDE 1.7.2.2,
    # 20.10.2026). Список — в IMPORT_STEPS.md и MIGRATION_REPORT.json (import.libraries).
    out.append("  </addData>\n</project>\n")
    text = "".join(out)
    if p.doc.newline == "\r\n":
        text = text.replace("\r\n", "\n")
    res.xml = text.encode("utf-8")
    return res
