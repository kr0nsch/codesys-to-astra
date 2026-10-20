"""Ввод-вывод: карта каналов (io-map.csv/.md) и экспериментальный фрагмент устройств REGUL (regul-devices.xml).

Стратегия по умолчанию — keep-modbus: модули Mx210 остаются в поле и опрашиваются через Modbus TCP
Master OS; на модуль — Outer Slave OS, на блок регистров — канал (ARRAY OF WORD + Status). Каналы и
DeviceIdentification — data/owen_modules.toml и data/regul_modules.toml.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from .. import TOOL_NAME, __version__, resources
from .. import xmltree as X

COLUMNS = ("variable", "type", "direction", "owen", "regul", "outcome", "rule", "source")


def iomap_csv(rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(COLUMNS)
    for r in rows:
        w.writerow([str(r.get(c, "")) for c in COLUMNS])
    return buf.getvalue().encode("utf-8")


def iomap_md(rows: list[dict[str, Any]]) -> str:
    head = ["переменная", "тип", "направление", "ОВЕН", "REGUL", "исход", "правило"]
    out = [
        "# Карта каналов (io-map)",
        "",
        f"Создано {TOOL_NAME} {__version__}. Стратегия keep-modbus: Mx210 остаются в поле, опрос — Modbus TCP Master OS.",
        "Привязка выполняется в мастере конфигурации Astra.IDE по этой таблице (формат CSV привязок Astra.IDE не "
        "опубликован — эксперимент E5 у владельца).",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "|".join("---" for _ in head) + "|",
    ]
    for r in rows:
        cells = [str(r.get(c, "")) for c in ("variable", "type", "direction", "owen", "regul", "outcome", "rule")]
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    return "\n".join(out) + "\n"


def _ident(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def regul_devices(cpu: str, slaves: list[dict[str, Any]]) -> bytes:
    """Фрагмент дерева REGUL по структуре экспорта Astra V1.7.0.0 (niksosov): ЦП, Modbus TCP Master OS,
    Outer Slave OS на каждый модуль Mx210. Экспериментально: импорт — эксперимент E6 (docs/PROBES.md)."""
    data = resources.read_toml("data", "regul_modules.toml")
    c = data["cpu"].get(cpu) or data["cpu"]["REGUL R500 61"]
    master = data["modbus"]["Modbus TCP Master OS"]
    outer = data["modbus"]["Modbus TCP Outer Slave OS"]

    def ident(t: Any, i: str, v: str, ind: str) -> str:
        return (
            f"{ind}<DeviceIdentification>\n{ind}  <Type>{t}</Type>\n{ind}  <Id>{i}</Id>\n"
            f"{ind}  <Version>{v}</Version>\n{ind}</DeviceIdentification>\n"
        )

    slaves_xml = []
    for sl in slaves:
        name = X.escape_attr(_ident(sl["name"]))
        slaves_xml.append(
            f'                  <configuration name="{name}">\n'
            "                    <addData>\n"
            '                      <data name="Device" handleUnknown="discard">\n'
            '                        <Device xmlns="">\n'
            "                          <DeviceType>\n"
            + ident(outer["type"], outer["id"], outer["version"], "                            ")
            + "                          </DeviceType>\n"
            "                        </Device>\n"
            "                      </data>\n"
            "                    </addData>\n"
            "                  </configuration>\n"
        )
    text = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<project xmlns="http://www.plcopen.org/xml/tc6_0200">\n'
        f'  <fileHeader companyName="plc-portfolio" productName="{TOOL_NAME}" productVersion="{TOOL_NAME} {__version__}" '
        'creationDateTime="1970-01-01T00:00:00" />\n'
        '  <contentHeader name="regul-devices (экспериментально)">\n'
        "    <Comment>Фрагмент дерева устройств REGUL. Статус: экспериментально, импорт не подтверждён (E6).</Comment>\n"
        '    <coordinateInfo>\n      <fbd>\n        <scaling x="1" y="1" />\n      </fbd>\n'
        '      <ld>\n        <scaling x="1" y="1" />\n      </ld>\n'
        '      <sfc>\n        <scaling x="1" y="1" />\n      </sfc>\n    </coordinateInfo>\n'
        "  </contentHeader>\n"
        "  <types>\n    <dataTypes />\n    <pous />\n  </types>\n"
        "  <instances>\n    <configurations>\n"
        '      <configuration name="Device">\n'
        "        <addData>\n"
        '          <data name="Device" handleUnknown="discard">\n'
        '            <Device xmlns="">\n'
        "              <DeviceType>\n"
        + ident(c["type"], c["id"], c["version"], "                ")
        + "              </DeviceType>\n"
        "            </Device>\n"
        "          </data>\n"
        '          <data name="configurations" handleUnknown="discard">\n'
        "            <configurations>\n"
        '              <configuration name="Modbus_TCP_Master_OS">\n'
        "                <addData>\n"
        '                  <data name="Device" handleUnknown="discard">\n'
        '                    <Device xmlns="">\n'
        "                      <DeviceType>\n"
        + ident(master["type"], master["id"], master["version"], "                        ")
        + "                      </DeviceType>\n"
        "                    </Device>\n"
        "                  </data>\n"
        '                  <data name="configurations" handleUnknown="discard">\n'
        "                <configurations>\n" + "".join(slaves_xml) + "                </configurations>\n"
        "                  </data>\n"
        "                </addData>\n"
        "              </configuration>\n"
        "            </configurations>\n"
        "          </data>\n"
        "        </addData>\n"
        "      </configuration>\n"
        "    </configurations>\n  </instances>\n"
        "</project>\n"
    )
    return text.encode("utf-8")
