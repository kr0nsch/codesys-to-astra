#!/usr/bin/env python3
"""Корпус правил cds2astra/tests/corpus/<ID>/{pos,neg}: минимальный вход на каждое правило (класс synthetic).

Вход — раскладка ST (`src/…`, тест превращает её в PLCopen XML конвертером раскладки) или `input.xml`
(задачи, библиотеки, устройства, графика — то, чего в раскладке нет). Ожидание — `case.toml`:
rule, outcomes (для pos — допустимые исходы находки; для neg — находок правила быть не должно),
target_spec и options (необязательно). Файлы генерирует этот скрипт; правка корпуса — здесь.

    python tools/corpus/make_rule_corpus.py [--check]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "cds2astra" / "tests" / "corpus"
CDS = "http://www.3s-software.com/plcopenxml/"
H = "// Назначение: корпус правила cds2astra (synthetic).\n// Автор:      kr0nsch\n// Версия:     0.1.0\n// Документ:   docs/RULES.md\n"


def prg(name: str, decl_vars: str, body: str) -> dict[str, str]:
    return {
        f"src/POUs/{name}/{name}.decl.st": f"{H}PROGRAM {name}\nVAR\n{decl_vars}END_VAR\n",
        f"src/POUs/{name}/{name}.impl.st": body,
    }


def gvl(name: str, text: str) -> dict[str, str]:
    return {f"src/GVLs/{name}.gvl.st": H + text}


def xml_doc(
    resource_body: str = "", conf_add: str = "", types: str = "", product: str = "CODESYS V3.5 SP17 Patch 3"
) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<project xmlns="http://www.plcopen.org/xml/tc6_0200">\n'
        f'  <fileHeader companyName="" productName="CODESYS" productVersion="{product}" creationDateTime="2026-10-20T00:00:00" />\n'
        '  <contentHeader name="case"><coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld>'
        '<sfc><scaling x="1" y="1" /></sfc></coordinateInfo></contentHeader>\n'
        f"  <types><dataTypes />{types or '<pous />'}</types>\n"
        '  <instances><configurations><configuration name="Device">\n'
        f'    <resource name="Application">\n{resource_body}    </resource>\n'
        f"    <addData>{conf_add}</addData>\n"
        "  </configuration></configurations></instances>\n</project>\n"
    )


def task(name: str, prio: int, interval: str = "t#20ms", kind: str = "Cyclic") -> str:
    return (
        f'      <task name="{name}" interval="PT0.02S" priority="{prio}"><pouInstance name="PRG_A" typeName="" />'
        f'<addData><data name="{CDS}tasksettings" handleUnknown="implementation">'
        f'<TaskSettings KindOfTask="{kind}" Interval="{interval}" IntervalUnit="ms" /></data></addData></task>\n'
    )


def libs(*names: str) -> str:
    rows = "".join(f'<Library Name="{n}" Namespace="{n.split(",")[0].lstrip("#")}" />' for n in names)
    return f'      <addData><data name="{CDS}libraries" handleUnknown="implementation"><Libraries>{rows}</Libraries></data></addData>\n'


def device(name: str, params: list[tuple[str, str, str]], children: str = "", iface: str = "Owen.Synthetic") -> str:
    ps = "".join(
        f'<Parameter ParameterId="{i}" type="std:REAL"><Attributes channel="{d}" /><Name>{c}</Name>'
        f"<Mapping>Application.{v}</Mapping></Parameter>"
        for i, (c, d, v) in enumerate(params)
    )
    kids = (
        f'<data name="configurations" handleUnknown="discard"><configurations>{children}</configurations></data>'
        if children
        else ""
    )
    return (
        f'<data name="Device" handleUnknown="discard"><Device xmlns=""><DeviceType><DeviceIdentification><Type>0</Type>'
        f"<Id>SYN {name}</Id><Version>0</Version></DeviceIdentification>"
        f'<Connector moduleType="0" interface="{iface}" connectorId="1"><HostParameterSet>{ps}</HostParameterSet></Connector>'
        f"</DeviceType></Device></data>{kids}"
    )


def conf(name: str, body: str) -> str:
    return f'<configuration name="{name}"><addData>{body}</addData></configuration>'


def graph_pou(name: str, lang_body: str) -> str:
    return (
        f'<pous><pou name="{name}" pouType="program"><interface><localVars><variable name="xA"><type><BOOL /></type></variable>'
        f"</localVars></interface><body>{lang_body}</body></pou></pous>"
    )


FBD_OSU = (
    '<FBD><inVariable localId="10000000001"><position x="0" y="0" /><connectionPointOut /><expression>wX</expression></inVariable>'
    '<block localId="10000000002" typeName="OSU.WORD_TO_HEX_STR"><position x="0" y="0" /><inputVariables>'
    '<variable formalParameter="wInput"><connectionPointIn><connection refLocalId="10000000001" /></connectionPointIn></variable>'
    '</inputVariables><inOutVariables /><outputVariables><variable formalParameter="WORD_TO_HEX_STR"><connectionPointOut />'
    "</variable></outputVariables></block></FBD>"
)
FBD_PLAIN = FBD_OSU.replace("OSU.WORD_TO_HEX_STR", "AND")

CASES: dict[str, dict[str, dict[str, object]]] = {
    "C2A-IO001": {
        "pos": {
            "files": gvl("GVL_Hw", "VAR_GLOBAL\n    xIn AT %IX0.0 : BOOL; // вход\nEND_VAR\n"),
            "outcomes": ["check"],
        },
        "neg": {"files": gvl("GVL_Hw", "VAR_GLOBAL\n    xIn : BOOL; // вход без AT\nEND_VAR\n")},
    },
    "C2A-LIB001": {
        "pos": {
            "files": prg(
                "PRG_A",
                "    sHex : STRING(8); // строка\n",
                "sHex := OSU.WORD_TO_HEX_STR(wInput := 16#FF, xUpperCase := TRUE, sPrefix := '');\n",
            ),
            "outcomes": ["check"],
        },
        "neg": {"files": prg("PRG_A", "    sHex : STRING(8); // строка\n", "sHex := CONCAT('a', 'b');\n")},
    },
    "C2A-SP18-UTF8": {
        "pos": {"files": prg("PRG_A", "    s : STRING; // строка\n", "s := UTF8#'Hello';\n"), "outcomes": ["auto"]},
        "neg": {"files": prg("PRG_A", "    s : STRING; // строка\n", "s := 'Hello';\n")},
    },
    "C2A-SP18-GEN": {
        "pos": {"files": prg("PRG_A", "    fbBuf : FB_Ring<16>; // обобщённый ФБ\n", ";\n"), "outcomes": ["todo"]},
        "neg": {"files": prg("PRG_A", "    fbBuf : FB_Ring; // обычный ФБ\n", ";\n")},
    },
    "C2A-SP19-BIT": {
        "pos": {
            "files": prg("PRG_A", "    w : WORD; // слово\n    x : BOOL; // бит\n", "x := w.%X3;\n"),
            "outcomes": ["auto"],
        },
        "neg": {"files": prg("PRG_A", "    w : WORD; // слово\n    x : BOOL; // бит\n", "x := w.3;\n")},
    },
    "C2A-RET001": {
        "pos": {
            "files": {
                **gvl("GVL_R", "VAR_GLOBAL RETAIN\n    udiCnt : UDINT; // счётчик\nEND_VAR\n"),
                **prg("PRG_A", "", "GVL_R.udiCnt := GVL_R.udiCnt + 1;\nudiCnt := 0;\n"),
            },
            "outcomes": ["info", "check"],
        },
        "neg": {"files": gvl("GVL_R", "VAR_GLOBAL\n    udiCnt : UDINT; // счётчик\nEND_VAR\n")},
    },
    "C2A-SYM001": {
        "pos": {
            "files": {
                "src/POUs/PRG_A/PRG_A.decl.st": H
                + "{attribute 'symbol' := 'readwrite'}\nPROGRAM PRG_A\nVAR\n    pData : POINTER TO INT; // указатель\nEND_VAR\n",
                "src/POUs/PRG_A/PRG_A.impl.st": ";\n",
            },
            "outcomes": ["check"],
        },
        "neg": {"files": prg("PRG_A", "    pData : POINTER TO INT; // указатель без символов\n", ";\n")},
    },
    "C2A-PTR001": {
        "pos": {
            "files": prg("PRG_A", "    dwAddr : DWORD; // адрес\n    i : INT; // значение\n", "dwAddr := ADR(i);\n"),
            "outcomes": ["check"],
        },
        "neg": {
            "files": prg(
                "PRG_A", "    pAddr : POINTER TO INT; // указатель\n    i : INT; // значение\n", "pAddr := ADR(i);\n"
            )
        },
    },
    "C2A-RED001": {
        "pos": {
            "files": gvl("GVL_S", "VAR_GLOBAL\n    pX : POINTER TO INT; // указатель\nEND_VAR\n"),
            "spec": {"redundancy": True},
            "outcomes": ["todo", "info"],
        },
        "neg": {"files": gvl("GVL_S", "VAR_GLOBAL\n    pX : POINTER TO INT; // указатель\nEND_VAR\n")},
    },
    "C2A-LANG-IL0": {
        "pos": {
            "xml": xml_doc(types=graph_pou("PRG_A", '<ST><xhtml xmlns="http://www.w3.org/1999/xhtml" /></ST>')),
            "outcomes": ["todo"],
        },
        "neg": {
            "xml": xml_doc(
                types=graph_pou("PRG_A", '<ST><xhtml xmlns="http://www.w3.org/1999/xhtml">xA := TRUE;</xhtml></ST>')
            )
        },
    },
    "C2A-LANG-IL": {
        "pos": {
            "xml": xml_doc(
                types=graph_pou(
                    "PRG_A", '<IL><xhtml xmlns="http://www.w3.org/1999/xhtml">LD xA\nNOT\nST xA\n</xhtml></IL>'
                )
            ),
            "outcomes": ["check"],
        },
        "neg": {
            "xml": xml_doc(
                types=graph_pou("PRG_A", '<ST><xhtml xmlns="http://www.w3.org/1999/xhtml">xA := NOT xA;</xhtml></ST>')
            )
        },
    },
    "C2A-LANG-SFC": {
        "pos": {
            "xml": xml_doc(
                types=graph_pou(
                    "PRG_A",
                    '<SFC><step localId="1" name="Init" initialStep="true"><position x="0" y="0" /></step></SFC>',
                )
            ),
            "outcomes": ["check"],
        },
        "neg": {"xml": xml_doc(types=graph_pou("PRG_A", FBD_PLAIN))},
    },
    "C2A-LANG-GRAPH": {
        "pos": {"xml": xml_doc(types=graph_pou("PRG_A", FBD_PLAIN)), "outcomes": ["info"]},
        "neg": {
            "xml": xml_doc(
                types=graph_pou("PRG_A", '<ST><xhtml xmlns="http://www.w3.org/1999/xhtml">xA := TRUE;</xhtml></ST>')
            )
        },
    },
    "C2A-SP20-LD": {
        "pos": {
            "xml": xml_doc(
                types=graph_pou(
                    "PRG_A",
                    '<ST><xhtml xmlns="http://www.w3.org/1999/xhtml" /></ST><addData>'
                    f'<data name="{CDS}ldnew" handleUnknown="implementation"><LD20 /></data></addData>',
                )
            ),
            "outcomes": ["todo"],
        },
        "neg": {"xml": xml_doc(types=graph_pou("PRG_A", FBD_PLAIN))},
    },
    "C2A-TASK001": {
        "pos": {"xml": xml_doc(task("MainTask", 1) + task("SlowTask", 20)), "outcomes": ["check"]},
        "neg": {"xml": xml_doc(task("MainTask", 5) + task("SlowTask", 10)), "allow_info": True},
    },
    "C2A-TASK002": {
        "pos": {
            "xml": xml_doc(
                task("FreeTask", 5, "t#0ms", "Freewheeling")
                + task("FastTask", 6, "500", "Cyclic").replace('IntervalUnit="ms"', 'IntervalUnit="us"')
            ),
            "outcomes": ["check"],
        },
        "neg": {"xml": xml_doc(task("MainTask", 5))},
    },
    "C2A-LIB002": {
        "pos": {"xml": xml_doc(libs("OwenStringUtils, 3.5.4.9 (ОВЕН)")), "outcomes": ["info"]},
        "neg": {"xml": xml_doc(libs("#Standard"))},
    },
    "C2A-SPxx-LIB": {
        "pos": {"xml": xml_doc(libs("String Libraries, 3.5.19.50 (CODESYS)")), "outcomes": ["todo"]},
        "neg": {"xml": xml_doc(libs("#Standard"))},
    },
    "C2A-IO002": {
        "pos": {
            "xml": xml_doc(
                conf_add=device("PLC", [], conf("OwenRTC", device("OwenRTC", [("Hour", "input", "GVL.usiHour")])))
            ),
            "outcomes": ["check"],
        },
        "neg": {"xml": xml_doc()},
    },
    "C2A-IO003": {
        "pos": {
            "xml": xml_doc(
                conf_add=device(
                    "PLC",
                    [],
                    conf("MV210_101_A", device("MV210_101_A", [("Вход 1/Измеренное значение", "input", "GVL.rT")])),
                )
            ),
            "outcomes": ["check"],
        },
        "neg": {"xml": xml_doc()},
    },
    "C2A-IO004": {
        "pos": {
            "xml": xml_doc(
                conf_add=device(
                    "PLC",
                    [],
                    conf("MV210_101_A", device("MV210_101_A", [("Вход 2/Измеренное значение", "input", "GVL.rT")])),
                )
            ),
            "outcomes": ["check"],
        },
        "neg": {
            "xml": xml_doc(
                conf_add=device(
                    "PLC",
                    [],
                    conf("MU210_402_A", device("MU210_402_A", [("Выходы/Битовая маска установки", "output", "GVL.w")])),
                )
            )
        },
    },
    "C2A-MB001": {
        "pos": {
            "xml": xml_doc(
                conf_add=device(
                    "PLC",
                    [],
                    conf("Modbus_TCP_Master", device("Modbus_TCP_Master", [], iface="Common.ModbusTCPMaster")),
                )
            ),
            "outcomes": ["check"],
        },
        "neg": {"xml": xml_doc()},
    },
    "C2A-EXC001": {
        "pos": {
            "xml": xml_doc(
                conf_add=device(
                    "PLC", [], conf("Watchdog", device("Watchdog", [("Last Exception Code", "input", "GVL.udiExc")]))
                )
            ),
            "outcomes": ["todo"],
        },
        "neg": {
            "xml": xml_doc(
                conf_add=device("PLC", [], conf("OwenRTC", device("OwenRTC", [("Hour", "input", "GVL.usiHour")])))
            )
        },
    },
    "C2A-FMT001": {
        "pos": {
            "xml": xml_doc(
                types=graph_pou("PRG_A", '<ST><xhtml xmlns="http://www.w3.org/1999/xhtml">xA := TRUE;</xhtml></ST>')
            ),
            "outcomes": ["info"],
        },
        "neg": {"files": prg("PRG_A", "    xA : BOOL; // флаг\n", "xA := TRUE;\n")},
    },
    "C2A-LANG-OOP": {
        "pos": {
            "files": {
                "src/POUs/FB_B/FB_B.decl.st": H + "FUNCTION_BLOCK FB_B EXTENDS FB_A\nVAR\nEND_VAR\n",
                "src/POUs/FB_B/FB_B.impl.st": ";\n",
                "src/POUs/FB_A/FB_A.decl.st": H + "FUNCTION_BLOCK FB_A\nVAR\nEND_VAR\n",
                "src/POUs/FB_A/FB_A.impl.st": ";\n",
            },
            "profile_unknown": ["oop.extends"],
            "outcomes": ["check"],
        },
        "neg": {
            "files": {
                "src/POUs/FB_B/FB_B.decl.st": H + "FUNCTION_BLOCK FB_B EXTENDS FB_A\nVAR\nEND_VAR\n",
                "src/POUs/FB_B/FB_B.impl.st": ";\n",
                "src/POUs/FB_A/FB_A.decl.st": H + "FUNCTION_BLOCK FB_A\nVAR\nEND_VAR\n",
                "src/POUs/FB_A/FB_A.impl.st": ";\n",
            }
        },
    },
    "C2A-MARK": {
        "pos": {
            "files": prg(
                "PRG_A", "    x : BOOL; // флаг\n", "// MIGRATION-CHECK: проверить вручную (s7conv)\nx := TRUE;\n"
            ),
            "outcomes": ["info"],
        },
        "neg": {"files": prg("PRG_A", "    x : BOOL; // флаг\n", "x := TRUE;\n")},
    },
}


def toml_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int | float):
        return str(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    raise TypeError(v)


def write_case(rule: str, kind: str, case: dict[str, object], root: Path) -> None:
    d = root / rule / kind
    d.mkdir(parents=True, exist_ok=True)
    lines = [f'rule = "{rule}"', f'kind = "{kind}"']
    if "outcomes" in case:
        lines.append(f"outcomes = {toml_value(case['outcomes'])}")
    if case.get("allow_info"):
        lines.append("allow_info = true")
    if "profile_unknown" in case:
        lines.append(f"profile_unknown = {toml_value(case['profile_unknown'])}")
    if "edits" in case:
        lines.append(f"edits = {toml_value(case['edits'])}")
    if "spec" in case:
        lines.append("[spec]")
        for k, v in dict(case["spec"]).items():  # type: ignore[call-overload]
            lines.append(f"{k} = {toml_value(v)}")
    (d / "case.toml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    if "xml" in case:
        (d / "input.xml").write_text(str(case["xml"]), encoding="utf-8", newline="\n")
    for rel, text in dict(case.get("files", {})).items():  # type: ignore[call-overload]
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(text), encoding="utf-8", newline="\n")


def build(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    for rule, kinds in CASES.items():
        for kind, case in kinds.items():
            write_case(rule, kind, case, root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="корпус правил pos/neg")
    ap.add_argument("--check", action="store_true", help="сверить с генератором")
    args = ap.parse_args(argv)
    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp) / "c")

            def files(root: Path) -> dict[str, bytes]:
                return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

            same = files(Path(tmp) / "c") == files(OUT)
            print("корпус правил: совпадает" if same else "корпус правил устарел: запустите без --check")
            return 0 if same else 1
    build(OUT)
    print(f"корпус правил: {sum(1 for _ in OUT.rglob('case.toml'))} случаев")
    return 0


if __name__ == "__main__":
    sys.exit(main())
