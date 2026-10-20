#!/usr/bin/env python3
"""Котельная boiler-plc210: раскладка ST (corpus/boiler-plc210/src) + синтетический слой ОВЕН -> export.xml.

Проба P7 (таргеты ОВЕН в CODESYS 3.5.17.30) не выполнялась, поэтому дерева ПЛК210 из настоящего экспорта нет:
слой ОВЕН накладывается этим скриптом (класс фикстуры synthetic, подпись — FIXTURE.toml и README).
Форма — как у экспорта CODESYS с устройством (размещение resource: instances/configuration/resource):
задачи с TaskSettings (приоритеты 0, 1, 15), ссылки на библиотеки ОВЕН, узлы OwenRTC и Watchdog, модули
МВ210-101 и МУ210-402 под Modbus TCP Master, счётчик энергии на стандартном Modbus 3S (канал FC 23).
Имена каналов — по документации ОВЕН (Targets v3.4, РЭ Mx210, шаблоны Mx210 — «Вход N/Измеренное значение»).
DeviceIdentification узлов ОВЕН неизвестны (devdesc не ставились) — в файле стоит Type 0 / Id «SYN …».

    python tools/corpus/owen_overlay.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from cds2astra import xmltree as X  # noqa: E402
from cds2astra.importers.layout import st_to_plcopen as S  # noqa: E402

CASE = REPO / "corpus" / "boiler-plc210"
OUT = CASE / "export.xml"
CDS = "http://www.3s-software.com/plcopenxml/"

TASKS = [
    ("FastTask", 0, "t#10ms", ["PRG_Fast"]),
    ("MainTask", 1, "t#50ms", ["PRG_Main", "PRG_Backup"]),
    ("SlowTask", 15, "t#1000ms", ["PRG_Slow"]),
]
LIBS = [
    ("#Standard", "Standard", "Standard, 3.5.9.0 (System)"),
    ("OwenStringUtils, 3.5.4.9 (ОВЕН)", "OSU", None),
    ("CmpOwenPidRegs, 3.5.14.33 (ОВЕН)", "OPR", None),
    ("OwenTypes, 3.5.17.5 (ОВЕН)", "OwenTypes", None),
    ("#IoStandard", "IoStandard", "IoStandard, 3.5.17.0 (System)"),
]
# (узел, [(канал, тип, направление, переменная)])
NODES = [
    (
        "OwenRTC",
        [
            ("Date And Time", "std:DT", "input", "GVL_Clock.dtNow"),
            ("Format date", "std:STRING", "input", "GVL_Clock.sDateText"),
            ("Format time", "std:STRING", "input", "GVL_Clock.sTimeText"),
            ("Hour", "std:USINT", "input", "GVL_Clock.usiHour"),
            ("Week of year", "std:USINT", "input", "GVL_Clock.usiWeek"),
        ],
    ),
    ("Watchdog", [("Last Exception Code", "std:UDINT", "input", "GVL_Clock.udiLastExc")]),
]
MODULES = [
    (
        "MV210_101_K3",
        [
            ("Вход 1/Измеренное значение", "std:REAL", "input", "GVL_Mx.rTSupply_C"),
            ("Вход 2/Измеренное значение", "std:REAL", "input", "GVL_Mx.rTReturn_C"),
            ("Вход 3/Измеренное значение", "std:REAL", "input", "GVL_Mx.rTOutdoor_C"),
            ("Вход 1/Значение (integer)", "std:INT", "input", "GVL_Mx.iTSupplyRaw"),
        ],
    ),
    ("MU210_402_K3", [("Выходы/Битовая маска установки", "std:WORD", "output", "GVL_Mx.wDoMask")]),
]


def esc(t: str) -> str:
    return X.escape_text(t).decode("utf-8")


def device(name: str, params: list[tuple[str, str, str, str]], ind: str, children: str = "", extra: str = "") -> str:
    ps = []
    for i, (chan, typ, direction, var) in enumerate(params):
        ps.append(
            f'{ind}        <Parameter ParameterId="{1000 + i}" type="{typ}">\n'
            f'{ind}          <Attributes channel="{direction}" />\n'
            f'{ind}          <Value name="p{1000 + i}" visiblename="{esc(chan)}" />\n'
            f"{ind}          <Name>{esc(chan)}</Name>\n"
            f"{ind}          <Mapping>Application.{var}</Mapping>\n"
            f"{ind}        </Parameter>\n"
        )
    kids = ""
    if children:
        kids = (
            f'{ind}<data name="configurations" handleUnknown="discard">\n{ind}  <configurations>\n'
            + children
            + f"{ind}  </configurations>\n{ind}</data>\n"
        )
    return (
        f'{ind}<data name="Device" handleUnknown="discard">\n'
        f'{ind}  <Device xmlns="">\n'
        f"{ind}    <DeviceType>\n"
        f"{ind}      <DeviceIdentification>\n{ind}        <Type>0</Type>\n{ind}        <Id>SYN {name}</Id>\n"
        f"{ind}        <Version>3.5.17.36</Version>\n{ind}      </DeviceIdentification>\n"
        f'{ind}      <Connector moduleType="0" interface="{extra or "Owen.Synthetic"}" connectorId="1">\n'
        f"{ind}        <HostParameterSet>\n"
        + "".join(ps)
        + f"{ind}        </HostParameterSet>\n{ind}      </Connector>\n"
        f"{ind}    </DeviceType>\n{ind}  </Device>\n{ind}</data>\n" + kids
    )


def configuration(name: str, body: str, ind: str) -> str:
    return f'{ind}<configuration name="{name}">\n{ind}  <addData>\n{body}{ind}  </addData>\n{ind}</configuration>\n'


def build() -> str:
    opts = S.Options(namespace=S.NS_0200, project_name="boiler-plc210", timestamp="2026-10-20T00:00:00", folders=False)
    placed, issues = S.collect_objects(str(CASE), [("src", [])])
    if any(i.severity == "error" for i in issues):
        raise SystemExit("ошибки раскладки: " + "; ".join(i.format() for i in issues))
    res = S.convert_objects(placed, opts)
    doc = X.parse(res.xml.encode("utf-8"))
    raw = doc.raw

    def sl(e: X.Elem) -> str:
        return raw[e.start : e.end].decode("utf-8")

    pous = [sl(e) for e in doc.root.iter("pou")]
    duts = [sl(e) for e in doc.root.iter("dataType")]
    gvls = [sl(e) for e in doc.root.iter("globalVars") if e.parent is not None and e.parent.tag == "data"]
    ind = "          "
    tasks = []
    for name, prio, interval, prgs in TASKS:
        insts = "".join(f'{ind}  <pouInstance name="{p}" typeName="" />\n' for p in prgs)
        tasks.append(
            f'{ind}<task name="{name}" interval="PT0.05S" priority="{prio}">\n{insts}'
            f"{ind}  <addData>\n"
            f'{ind}    <data name="{CDS}tasksettings" handleUnknown="implementation">\n'
            f'{ind}      <TaskSettings KindOfTask="Cyclic" Interval="{interval}" IntervalUnit="ms" WithinSPSTimeSlicing="true">\n'
            f'{ind}        <Watchdog Enabled="false" TimeUnit="ms" Sensitivity="1" />\n'
            f"{ind}      </TaskSettings>\n{ind}    </data>\n{ind}  </addData>\n{ind}</task>\n"
        )
    gv = "".join(f"{ind}{g}\n" for g in gvls)
    pou_data = "".join(
        f'{ind}  <data name="{CDS}pou" handleUnknown="implementation">\n{ind}    {p}\n{ind}  </data>\n' for p in pous
    )
    dut_data = "".join(
        f'{ind}  <data name="{CDS}datatype" handleUnknown="implementation">\n{ind}    {d}\n{ind}  </data>\n'
        for d in duts
    )
    libs = "".join(
        f'{ind}      <Library Name="{X.escape_attr(n)}" Namespace="{ns}"'
        + (f' DefaultResolution="{X.escape_attr(r)}"' if r else "")
        + " />\n"
        for n, ns, r in LIBS
    )
    lib_data = (
        f'{ind}  <data name="{CDS}libraries" handleUnknown="implementation">\n{ind}    <Libraries>\n{libs}'
        f"{ind}    </Libraries>\n{ind}  </data>\n"
    )
    sub = "              "
    node_conf = "".join(configuration(n, device(n, ps, sub + "    "), sub) for n, ps in NODES)
    mod_conf = "".join(
        configuration(n, device(n, ps, sub + "        ", extra="Owen.Mx210Template"), sub + "    ") for n, ps in MODULES
    )
    meter = configuration(
        "ModbusTCP_Slave_Device_Meter",
        device(
            "ModbusTCP_Slave_Device_Meter",
            [("Channel 1 Read/Write Multiple Registers (FC 23)", "std:WORD", "input", "GVL_Mx.wMeterStatus")],
            sub + "        ",
            extra="Common.ModbusTCPSlave",
        ),
        sub + "    ",
    )
    master = configuration(
        "Modbus_TCP_Master",
        device("Modbus_TCP_Master", [], sub + "    ", children=mod_conf + meter, extra="Common.ModbusTCPMaster"),
        sub,
    )
    plc = device("PLC210_11", [], "        ", children=node_conf + master, extra="Owen.PLC210")
    head = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<project xmlns="http://www.plcopen.org/xml/tc6_0200">\n'
        '  <fileHeader companyName="" productName="CODESYS" productVersion="CODESYS V3.5 SP17 Patch 3" '
        'creationDateTime="2026-10-20T00:00:00" />\n'
        '  <contentHeader name="boiler-plc210.project" modificationDateTime="2026-10-20T00:00:00">\n'
        "    <Comment>Синтетический экспорт: логика — corpus/boiler-plc210/src, слой ОВЕН — tools/corpus/owen_overlay.py "
        "(проба P7 не выполнялась)</Comment>\n"
        '    <coordinateInfo>\n      <fbd>\n        <scaling x="1" y="1" />\n      </fbd>\n'
        '      <ld>\n        <scaling x="1" y="1" />\n      </ld>\n'
        '      <sfc>\n        <scaling x="1" y="1" />\n      </sfc>\n    </coordinateInfo>\n'
        "  </contentHeader>\n  <types>\n    <dataTypes />\n    <pous />\n  </types>\n"
        "  <instances>\n    <configurations>\n"
        '      <configuration name="Device">\n'
        '        <resource name="Application">\n'
    )
    return (
        head
        + "".join(tasks)
        + gv
        + f"{ind}<addData>\n"
        + dut_data
        + pou_data
        + lib_data
        + f"{ind}</addData>\n"
        + "        </resource>\n"
        + "        <addData>\n"
        + plc
        + "        </addData>\n"
        + "      </configuration>\n    </configurations>\n  </instances>\n</project>\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="boiler-plc210: синтетический экспорт ПЛК210")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text = build()
    if args.check:
        same = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("boiler-plc210: совпадает" if same else "boiler-plc210: export.xml устарел")
        return 0 if same else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"boiler-plc210: {OUT.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
