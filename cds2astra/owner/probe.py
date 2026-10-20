"""Пакет проб для владельца Astra.IDE и железа (M10): E5, E7, E8 и проба раскладки памяти.

`cds2astra probe --out DIR` пишет файлы, которые нельзя проверить скриптом без интерфейса или без ПЛК:
- `layout-probe.xml` — PRG_C2aLayoutProbe: SIZEOF(POINTER), SIZEOF структур с LREAL/LINT, байты REAL 1.0
  (порядок слов) — импорт в Astra.IDE, загрузка в ПЛК или ВПЛК, значения — в docs/OWNER_EXPERIMENTS.md;
- `E5.md`, `E7.md`, `E8.md` — шаги экспериментов и куда записать результат;
- `RESULTS.csv` — пустая таблица результатов со столбцами семейства (00-INDEX §4.9).
"""

from __future__ import annotations

from ..importers.layout import st_to_plcopen as S
from ..importers.layout import stlayout as L

RESULTS_HEADER = "probe_id,construct,file,expected,observed,ide,ide_version,date,notes\n"

LAYOUT_DUT = """// Назначение: структура для пробы выравнивания (pack-mode R500 = 8 по devdesc).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/OWNER_EXPERIMENTS.md
TYPE ST_C2aProbeAlign :
STRUCT
    xFlag : BOOL;       // 1 байт
    lrValue : LREAL;    // 8 байт: смещение 8 при pack-mode 8
    iShort : INT;       // 2 байта
    liLong : LINT;      // 8 байт
END_STRUCT
END_TYPE
"""

LAYOUT_DECL = """// Назначение: проба раскладки памяти на REGUL R500 / ВПЛК: разрядность указателя, выравнивание структур,
//             порядок байт REAL. Значения прочитать онлайн и записать в docs/OWNER_EXPERIMENTS.md (E8, раскладка).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/OWNER_EXPERIMENTS.md
PROGRAM PRG_C2aLayoutProbe
VAR
    udiPointerSize : UDINT;     // SIZEOF(POINTER TO BYTE): 4 или 8
    udiAlignSize : UDINT;       // SIZEOF(ST_C2aProbeAlign): 32 при pack-mode 8
    stAlign : ST_C2aProbeAlign; // экземпляр для SIZEOF
    rOne : REAL := 1.0;         // 16#3F800000
    pBytes : POINTER TO BYTE;   // байты rOne
    abReal : ARRAY [0..3] OF BYTE;  // байты REAL в памяти (x86 — младший первым: 00 00 80 3F)
    iIdx : INT;                 // индекс байта
END_VAR
"""

LAYOUT_IMPL = """udiPointerSize := SIZEOF(pBytes);
udiAlignSize := SIZEOF(stAlign);
pBytes := ADR(rOne);
FOR iIdx := 0 TO 3 DO
    abReal[iIdx] := pBytes[iIdx];
END_FOR
"""

E5 = """# E5 — образцы форматов Astra.IDE (у владельца)

Публичных образцов нет (конспект §3.3); без них форматы CSV привязок и XML каналов Modbus у cds2astra — допущения.

1. В проекте R500 с модулем AI/DI: ПКМ по модулю → «Экспортировать соотнесения в CSV». Ожидается: CSV с
   разделителем списков Windows.
2. Modbus TCP Master OS → Outer Slave OS → вкладка каналов → «Экспорт». Ожидается: `*mb_outer_channels.xml`.
3. «Проект → Экспорт PLCopenXML» проекта с крейтом и Modbus (флаг «объявления как простой текст»).
4. «Проект → Экспорт…» визуализации в `.export`.

Результат: файлы — в `probe/E5/` (без данных лицензий и учётных записей), строки — в `probe/RESULTS.csv`.
"""

E7 = """# E7 — визуализация (у владельца)

1. В CODESYS 3.5.17.30 экспортировать визуализацию проекта ОВЕН в `.export`.
2. В Astra.IDE 1.7.2.x «Проект → Импорт…» этого файла в проект на ЦП с TargetVisu (R500 71/171) или «-W».
3. Записать: импортировалось ли, какие элементы потеряны, кириллица (флаг «Использовать строки Unicode»).

Результат — строка E7 в `probe/RESULTS.csv` и `docs/OWNER_EXPERIMENTS.md`.
"""

E8 = """# E8 — ВПЛК REGUL R500 (у владельца, некоммерческое использование)

1. Образ ВПЛК R500 1.7.2.6 (`.ova`, reglab.ru/soft), проект на CU 00 071-W.
2. Импортировать `astra-import.xml` и `layout-probe.xml`, задачи — по IMPORT_STEPS.md.
3. Загрузить, войти онлайн, записать значения PRG_C2aLayoutProbe: `udiPointerSize`, `udiAlignSize`, `abReal`.
4. Для keep-modbus: подать на Outer Slave значения с симулятора Mx210 (pymodbus) и сверить порядок слов FLOAT32.

Результат — `probe/RESULTS.csv` (`value:<значение>`), статусы профиля `platform.pointer_size`,
`modbus.word_order_float32` -> owner_verified (дата, версия СПО).
"""


def layout_probe_xml() -> bytes:
    objs: list[tuple[L.StObject, list[str]]] = [
        (L.StObject(L.KIND_DUT, "ST_C2aProbeAlign", LAYOUT_DUT, []), []),
        (L.StObject(L.KIND_POU, "PRG_C2aLayoutProbe", LAYOUT_DECL, [], impl=LAYOUT_IMPL, pou_kind=L.POU_PROGRAM), []),
    ]
    opts = S.Options(
        namespace=S.NS_0200, project_name="c2a-layout-probe", timestamp="1970-01-01T00:00:00", folders=False
    )
    return S.convert_objects(objs, opts).xml.encode("utf-8")


def package() -> dict[str, bytes]:
    return {
        "layout-probe.xml": layout_probe_xml(),
        "E5.md": E5.encode("utf-8"),
        "E7.md": E7.encode("utf-8"),
        "E8.md": E8.encode("utf-8"),
        "RESULTS.csv": RESULTS_HEADER.encode("utf-8"),
    }
