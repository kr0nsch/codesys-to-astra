"""Ввод-вывод: карта каналов (io-map.csv/.md) и устройство ЦП REGUL для импорта (regul-devices.xml).

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


# Коннекторы ЦП R500 — как в экспорте Astra.IDE V1.7.0.0 (niksosov, ЦП 4096 / 109B 0008). Без них импорт
# устройства падает («Значение не может быть неопределенным. Имя параметра: array», Astra.IDE 1.7.2.2, 20.10.2026).
CPU_CONNECTORS = (
    ("256", "Common.PCI", "0"),
    ("4096", "Regul.SysSerial", "1"),
    ("4096", "Regul.Common", "2"),
    ("4096", "RegulR500.Common", "3"),
)


def regul_devices(cpu: str, slaves: list[dict[str, Any]]) -> bytes:
    """Устройство ЦП REGUL по структуре экспорта Astra V1.7.0.0 (niksosov) для импорта в проект.

    Импорт этого фрагмента (ЦП с коннекторами) в Astra.IDE 1.7.2.2 проверен локально 20.10.2026 (E6, docs/PROBES.md).
    Modbus TCP Master OS и Outer Slave OS в файл не идут: без образца их коннекторов импорт падает, они
    добавляются в мастере конфигурации по io-map (перечень — в Comment)."""
    data = resources.read_toml("data", "regul_modules.toml")
    c = data["cpu"].get(cpu) or data["cpu"]["REGUL R500 61"]
    master = data["modbus"]["Modbus TCP Master OS"]
    outer = data["modbus"]["Modbus TCP Outer Slave OS"]
    names = ", ".join(_ident(sl["name"]) for sl in slaves) or "нет"
    conns = "".join(
        f'                <Connector moduleType="{mt}" interface="{iface}" connectorId="{cid}">\n'
        "                  <HostParameterSet />\n"
        "                </Connector>\n"
        for mt, iface, cid in CPU_CONNECTORS
    )
    comment = (
        f"Устройство ЦП {cpu} ({c['type']} / {c['id']} / {c['version']}). Добавить вручную: Modbus TCP Master OS "
        f"({master['type']} / {master['id']}) и Modbus TCP Outer Slave OS ({outer['type']} / {outer['id']}) на модули: "
        f"{names}; каналы — io-map.md"
    )
    text = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<project xmlns="http://www.plcopen.org/xml/tc6_0200">\n'
        f'  <fileHeader companyName="plc-portfolio" productName="{TOOL_NAME}" productVersion="{TOOL_NAME} {__version__}" '
        'creationDateTime="1970-01-01T00:00:00" />\n'
        '  <contentHeader name="regul-devices">\n'
        f"    <Comment>{X.escape_text(comment).decode('utf-8')}</Comment>\n"
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
        "                <DeviceIdentification>\n"
        f"                  <Type>{c['type']}</Type>\n"
        f"                  <Id>{c['id']}</Id>\n"
        f"                  <Version>{c['version']}</Version>\n"
        "                </DeviceIdentification>\n" + conns + "                <DeviceParameterSet />\n"
        "              </DeviceType>\n"
        "            </Device>\n"
        "          </data>\n"
        "        </addData>\n"
        "      </configuration>\n"
        "    </configurations>\n  </instances>\n"
        "</project>\n"
    )
    return text.encode("utf-8")
