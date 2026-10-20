#!/usr/bin/env python3
"""Корпус lang-matrix: по POU на каждый из шести языков (ST, FBD, LD, CFC, SFC, IL) — рукописный TC6.

Каждый POU использует Standard (TON, AND), Util (HYSTERESIS) и блок под замену — функцию
OwenStringUtils `OSU.WORD_TO_HEX_STR` (сигнатура — data/owen_signatures.toml). Графика пишется в форме,
которую экспортирует CODESYS 3.5.17.30 (localId = сеть·10^10 + номер, координаты 0,0 — ext §3.3).

Выход — `corpus/lang-matrix/source.handmade.xml` (класс handmade). Фикстура класса ide-roundtrip —
обратный экспорт этого файла из CODESYS 3.5.17.30 (`tools/probes.py --lang-matrix`), `export.xml`.

    python tools/corpus/build_lang_matrix.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "corpus" / "lang-matrix" / "source.handmade.xml"

HEADER = """<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="plc-portfolio" productName="cds2astra lang-matrix (рукописный TC6)" productVersion="0.1.0" creationDateTime="2026-10-20T00:00:00" />
  <contentHeader name="lang-matrix" modificationDateTime="2026-10-20T00:00:00">
    <coordinateInfo>
      <fbd>
        <scaling x="1" y="1" />
      </fbd>
      <ld>
        <scaling x="1" y="1" />
      </ld>
      <sfc>
        <scaling x="1" y="1" />
      </sfc>
    </coordinateInfo>
  </contentHeader>
  <types>
    <dataTypes />
    <pous>
"""

FOOTER = """    </pous>
  </types>
  <instances>
    <configurations />
  </instances>
</project>
"""

CDS = "http://www.3s-software.com/plcopenxml/"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plaintext(decl: str, indent: str = "          ") -> str:
    return (
        f'{indent}<data name="{CDS}interfaceasplaintext" handleUnknown="implementation">\n'
        f"{indent}  <InterfaceAsPlainText>\n"
        f'{indent}    <xhtml xmlns="http://www.w3.org/1999/xhtml">{esc(decl)}</xhtml>\n'
        f"{indent}  </InterfaceAsPlainText>\n"
        f"{indent}</data>\n"
    )


_TC6_TYPES = {"BOOL", "INT", "WORD", "TIME", "STRING", "REAL", "DINT"}


def var_xml(name: str, typ: str) -> str:
    if typ in _TC6_TYPES:
        inner = "<string />" if typ == "STRING" else f"<{typ} />"
    else:
        inner = f'<derived name="{typ}" />'
    return (
        f'            <variable name="{name}">\n'
        f"              <type>\n                {inner}\n              </type>\n"
        "            </variable>\n"
    )


def interface(local: list[tuple[str, str]]) -> str:
    body = "".join(var_xml(n, t) for n, t in local)
    return f"        <interface>\n          <localVars>\n{body}          </localVars>\n        </interface>\n"


def decl_text(name: str, purpose: str, local: list[tuple[str, str]]) -> str:
    lines = [f"// {purpose}", f"PROGRAM {name}", "VAR"]
    for n, t in local:
        lines.append(f"    {n} : {t};")
    lines.append("END_VAR")
    return "\n".join(lines) + "\n"


def pou(name: str, purpose: str, local: list[tuple[str, str]], body: str, actions: str = "") -> str:
    return (
        f'      <pou name="{name}" pouType="program">\n'
        + interface(local)
        + actions
        + "        <body>\n"
        + body
        + "        </body>\n"
        + "        <addData>\n"
        + plaintext(decl_text(name, purpose, local))
        + "        </addData>\n"
        + "      </pou>\n"
    )


COMMON = [
    ("xA", "BOOL"),
    ("xB", "BOOL"),
    ("xQ", "BOOL"),
    ("xDone", "BOOL"),
    ("iLevel", "INT"),
    ("xHigh", "BOOL"),
    ("wCode", "WORD"),
    ("sHex", "STRING"),
    ("fbTon", "TON"),
    ("fbHyst", "HYSTERESIS"),
]

ST_BODY = """// Standard: TON; Util: HYSTERESIS; блок под замену: OSU.WORD_TO_HEX_STR (OwenStringUtils)
xQ := xA AND xB;
fbTon(IN := xQ, PT := T#100MS);
xDone := fbTon.Q;
fbHyst(IN := iLevel, HIGH := 80, LOW := 20, OUT => xHigh);
sHex := OSU.WORD_TO_HEX_STR(wInput := wCode, xUpperCase := TRUE, sPrefix := '0x');
"""

IL_BODY = """LD xA
AND xB
ST xQ
CAL fbTon(IN := xQ, PT := T#100MS)
LD fbTon.Q
ST xDone
CAL fbHyst(IN := iLevel, HIGH := 80, LOW := 20)
LD fbHyst.OUT
ST xHigh
"""


def st_body(text: str, tag: str = "ST") -> str:
    return f'          <{tag}>\n            <xhtml xmlns="http://www.w3.org/1999/xhtml">{esc(text)}</xhtml>\n          </{tag}>\n'


def in_var(lid: str, expr: str) -> str:
    return (
        f'            <inVariable localId="{lid}">\n              <position x="0" y="0" />\n'
        f"              <connectionPointOut />\n              <expression>{esc(expr)}</expression>\n"
        "            </inVariable>\n"
    )


def out_var(lid: str, ref: str, param: str, expr: str) -> str:
    return (
        f'            <outVariable localId="{lid}">\n              <position x="0" y="0" />\n'
        f'              <connectionPointIn>\n                <connection refLocalId="{ref}" formalParameter="{param}" />\n'
        f"              </connectionPointIn>\n              <expression>{esc(expr)}</expression>\n"
        "            </outVariable>\n"
    )


CALL_TYPES = {"AND": "operator", "TON": "functionblock", "HYSTERESIS": "functionblock"}


def calltype_xml(type_name: str, cfc: bool, indent: str) -> str:
    call = CALL_TYPES.get(type_name, "function")
    ext = "cfccalltype" if cfc else "fbdcalltype"
    return (
        f"{indent}<addData>\n"
        f'{indent}  <data name="{CDS}{ext}" handleUnknown="implementation">\n'
        f'{indent}    <CallType xmlns="">{call}</CallType>\n'
        f"{indent}  </data>\n"
        f"{indent}</addData>\n"
    )


def block(
    lid: str,
    type_name: str,
    inputs: list[tuple[str, str]],
    outputs: list[str],
    instance: str | None = None,
    extra: str = "",
    cfc: bool = False,
) -> str:
    inst = f' instanceName="{instance}"' if instance else ""
    ins = "".join(
        f'                <variable formalParameter="{p}">\n                  <connectionPointIn>\n'
        f'                    <connection refLocalId="{r}" />\n                  </connectionPointIn>\n'
        "                </variable>\n"
        for p, r in inputs
    )
    outs = "".join(
        f'                <variable formalParameter="{p}">\n                  <connectionPointOut />\n'
        "                </variable>\n"
        for p in outputs
    )
    return (
        f'            <block localId="{lid}" typeName="{type_name}"{inst}{extra}>\n'
        '              <position x="0" y="0" />\n'
        f"              <inputVariables>\n{ins}              </inputVariables>\n"
        "              <inOutVariables />\n"
        f"              <outputVariables>\n{outs}              </outputVariables>\n"
        + calltype_xml(type_name, cfc, "              ")
        + "            </block>\n"
    )


def connector(lid: str, ref: str, param: str) -> str:
    """Провод CFC: connector name="" с соединением от выхода источника (так экспортирует CODESYS)."""
    return (
        f'            <connector localId="{lid}" name="">\n              <position x="0" y="0" />\n'
        f'              <connectionPointIn>\n                <connection refLocalId="{ref}" formalParameter="{esc(param)}" />\n'
        "              </connectionPointIn>\n            </connector>\n"
    )


def lid(net: int, n: int) -> str:
    return str(net * 10**10 + n)


# Сети: (тип блока, экземпляр, входы [(пин, выражение)], выходы [(пин, переменная)])
NETWORKS: list[tuple[str, str | None, list[tuple[str, str]], list[tuple[str, str]]]] = [
    ("AND", None, [("In1", "xA"), ("In2", "xB")], [("Out1", "xQ")]),
    ("TON", "fbTon", [("IN", "xQ"), ("PT", "T#100MS")], [("Q", "xDone")]),
    ("HYSTERESIS", "fbHyst", [("IN", "iLevel"), ("HIGH", "80"), ("LOW", "20")], [("OUT", "xHigh")]),
    (
        "OSU.WORD_TO_HEX_STR",
        None,
        [("wInput", "wCode"), ("xUpperCase", "TRUE"), ("sPrefix", "'0x'")],
        [("WORD_TO_HEX_STR", "sHex")],
    ),
]
ALL_OUTPUTS = {"AND": ["Out1"], "TON": ["Q", "ET"], "HYSTERESIS": ["OUT"], "OSU.WORD_TO_HEX_STR": ["WORD_TO_HEX_STR"]}


def fbd_networks() -> str:
    """FBD: сеть на блок, localId = сеть·10^10 + номер (как в экспорте CODESYS)."""
    parts: list[str] = []
    for net, (typ, inst, ins, outs) in enumerate(NETWORKS, start=1):
        refs: list[tuple[str, str]] = []
        for k, (pin, expr) in enumerate(ins, start=1):
            parts.append(in_var(lid(net, k), expr))
            refs.append((pin, lid(net, k)))
        blk = lid(net, len(ins) + 1)
        parts.append(block(blk, typ, refs, ALL_OUTPUTS[typ], inst))
        for k, (pin, var) in enumerate(outs, start=len(ins) + 2):
            parts.append(out_var(lid(net, k), blk, pin, var))
    return "".join(parts)


def cfc_networks() -> str:
    """CFC: те же блоки; провода — connector, порядок исполнения — executionOrderId блоков и выходов."""
    parts: list[str] = []
    counter = [0]
    order = 0

    def nid() -> str:
        counter[0] += 1
        return str(counter[0])

    for typ, inst, ins, outs in NETWORKS:
        if typ == "AND":
            # провод от выхода оператора AND CODESYS 3.5.17.30 при импорте CFC теряет (проба P5): в CFC без AND
            continue
        refs: list[tuple[str, str]] = []
        for pin, expr in ins:
            v = nid()
            parts.append(in_var(v, expr))
            c = nid()
            parts.append(connector(c, v, expr))
            refs.append((pin, c))
        blk = nid()
        order += 1
        parts.append(block(blk, typ, refs, ALL_OUTPUTS[typ], inst, extra=f' executionOrderId="{order}"', cfc=True))
        for pin, var in outs:
            c = nid()
            parts.append(connector(c, blk, pin))
            order += 1
            o = nid()
            parts.append(
                f'            <outVariable localId="{o}" executionOrderId="{order}">\n'
                '              <position x="0" y="0" />\n'
                f'              <connectionPointIn>\n                <connection refLocalId="{c}" />\n'
                f"              </connectionPointIn>\n              <expression>{esc(var)}</expression>\n"
                "            </outVariable>\n"
            )
    return "".join(parts)


def fbd_body() -> str:
    return "          <FBD>\n" + fbd_networks() + "          </FBD>\n"


def cfc_body() -> str:
    lines = cfc_networks().splitlines(keepends=True)
    body = "".join("    " + line for line in lines)
    return (
        '          <ST>\n            <xhtml xmlns="http://www.w3.org/1999/xhtml" />\n          </ST>\n'
        "          <addData>\n"
        f'            <data name="{CDS}cfc" handleUnknown="implementation">\n'
        "              <CFC>\n" + body + "              </CFC>\n            </data>\n          </addData>\n"
    )


def ld_body() -> str:
    return """          <LD>
            <leftPowerRail localId="0">
              <position x="0" y="0" />
              <connectionPointOut formalParameter="none" />
            </leftPowerRail>
            <contact localId="1" negated="false" storage="none" edge="none">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="0" />
              </connectionPointIn>
              <connectionPointOut />
              <variable>xA</variable>
            </contact>
            <contact localId="2" negated="false" storage="none" edge="none">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="1" />
              </connectionPointIn>
              <connectionPointOut />
              <variable>xB</variable>
            </contact>
            <coil localId="3" negated="false" storage="none">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="2" />
              </connectionPointIn>
              <connectionPointOut />
              <variable>xQ</variable>
            </coil>
            <rightPowerRail localId="2147483646">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="3" />
              </connectionPointIn>
            </rightPowerRail>
          </LD>
"""


SFC_ACTION = f"""        <actions>
          <action name="ActRun">
            <body>
{st_body("fbTon(IN := TRUE, PT := T#100MS);" + chr(10) + "xDone := fbTon.Q;" + chr(10) + "fbHyst(IN := iLevel, HIGH := 80, LOW := 20, OUT => xHigh);" + chr(10) + "sHex := OSU.WORD_TO_HEX_STR(wInput := wCode, xUpperCase := TRUE, sPrefix := '0x');" + chr(10)).replace("          <", "              <")}            </body>
          </action>
        </actions>
"""


def sfc_body() -> str:
    return """          <SFC>
            <inVariable localId="8">
              <position x="0" y="0" />
              <connectionPointOut />
              <expression>xA AND xB</expression>
            </inVariable>
            <inVariable localId="9">
              <position x="0" y="0" />
              <connectionPointOut />
              <expression>xDone</expression>
            </inVariable>
            <step localId="1" name="Init" initialStep="true">
              <position x="0" y="0" />
              <connectionPointIn />
              <connectionPointOut formalParameter="sfc" />
            </step>
            <transition localId="2">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="1" />
              </connectionPointIn>
              <connectionPointOut />
              <condition>
                <connectionPointIn>
                  <connection refLocalId="8" />
                </connectionPointIn>
              </condition>
            </transition>
            <step localId="3" name="Run">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="2" />
              </connectionPointIn>
              <connectionPointOut formalParameter="sfc" />
            </step>
            <actionBlock localId="4">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="3" />
              </connectionPointIn>
              <action localId="5" qualifier="N">
                <relPosition x="0" y="0" />
                <reference name="ActRun" />
              </action>
            </actionBlock>
            <transition localId="6">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="3" />
              </connectionPointIn>
              <connectionPointOut />
              <condition>
                <connectionPointIn>
                  <connection refLocalId="9" />
                </connectionPointIn>
              </condition>
            </transition>
            <jumpStep localId="7" targetName="Init">
              <position x="0" y="0" />
              <connectionPointIn>
                <connection refLocalId="6" />
              </connectionPointIn>
            </jumpStep>
          </SFC>
"""


MAIN_BODY = """// Вызов POU всех языков матрицы
PRG_LangSt();
PRG_LangFbd();
PRG_LangLd();
PRG_LangCfc();
PRG_LangSfc();
PRG_LangIl();
"""


def build() -> str:
    parts = [HEADER]
    parts.append(pou("PRG_LangSt", "lang-matrix: ST", COMMON, st_body(ST_BODY)))
    parts.append(pou("PRG_LangFbd", "lang-matrix: FBD", COMMON, fbd_body()))
    parts.append(pou("PRG_LangLd", "lang-matrix: LD", [("xA", "BOOL"), ("xB", "BOOL"), ("xQ", "BOOL")], ld_body()))
    parts.append(pou("PRG_LangCfc", "lang-matrix: CFC", COMMON, cfc_body()))
    parts.append(pou("PRG_LangSfc", "lang-matrix: SFC", COMMON, sfc_body(), SFC_ACTION))
    il_vars = [v for v in COMMON if v[0] not in ("wCode", "sHex")]
    parts.append(pou("PRG_LangIl", "lang-matrix: IL", il_vars, st_body(IL_BODY, "IL")))
    parts.append(pou("PRG_LangMain", "lang-matrix: вызов всех POU", [], st_body(MAIN_BODY)))
    parts.append(FOOTER)
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="сверить файл с генератором (код 1 при расхождении)")
    args = ap.parse_args(argv)
    text = build()
    if args.check:
        same = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("lang-matrix: совпадает" if same else "lang-matrix: файл устарел — запустите без --check")
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"lang-matrix: {OUT.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
