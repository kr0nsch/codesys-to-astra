"""Реестр правил C2A-*: ID, заголовок, объяснение, источник (ключ профиля или URL), исходы, автоправка.

Тест-реестр падает, если у правила чего-то не хватает, если правило не описано в docs/RULES.md или у
него нет корпуса pos/neg (cds2astra/tests/corpus/<ID>/).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleInfo:
    id: str
    title: str
    explanation: str
    source: str
    outcomes: tuple[str, ...]
    autofix: str
    language: str  # язык находок по умолчанию


DPA302 = (
    "https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf"
)
DPA3021 = (
    "https://reglab.ru/upload/iblock/c63/bxjpd31viamzx3b4i0nj0zthy4xq1sg1/Modbus-User-Guide-DPA_302-1_v1.7_rus.pdf"
)
DPA3024 = "https://reglab.ru/upload/iblock/28f/tmu37n4jz4w5oxepmx0431vb5q5yo6xw/Redundancy-User-Guide-_DPA_302_4_v2_11_rus.pdf"
TARGETS = "https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Targets_v3.4.pdf"
CDSHELP = "https://content.helpme-codesys.com/en/CODESYS%20Development%20System/"

RULES: dict[str, RuleInfo] = {
    r.id: r
    for r in (
        RuleInfo(
            "C2A-IO001",
            "AT-адреса %I/%Q/%M",
            "Адреса %I/%Q ОВЕН не совпадают с автоназначением REGUL по порядку модулей (DPA-302 с. 136–148): "
            "AT снимается, переменная уходит в GVL_IO, привязка канала — по io-map. %M проверяется по объёму.",
            f"{DPA302} с. 136–148; профиль memory.marker",
            ("check", "todo", "info"),
            "снять AT, перенести переменную в GVL_IO, переписать квалифицированные ссылки, строка io-map",
            "DECL",
        ),
        RuleInfo(
            "C2A-IO002",
            "Привязки к узлам таргета ОВЕН",
            "Узлы OwenRTC, Watchdog, Info, Network, LeftSide… есть только в таргете ОВЕН. Переменные, "
            "привязанные к их каналам, получают источник по таблице замен (FB_C2aRtc) или остаются todo.",
            f"{TARGETS} разд. 4",
            ("check", "todo"),
            "OwenRTC -> FB_C2aRtc в PRG_C2aIoUpdate; прочие узлы -> todo с подсказкой",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-IO003",
            "Типизированные каналы шаблонов Mx210",
            "Драйверы Modbus REGUL отдают канал как ARRAY OF WORD (DPA-302.1 с. 15–16), а не REAL: на блок "
            "регистров создаётся канал Modbus TCP Outer Slave OS, распаковка — F_C2aMbToReal и FB_C2aMbUnpack (AstraCompat). Порядок слов "
            "FLOAT32 по профилю unknown -> check.",
            f"{DPA3021} с. 13–16; профиль modbus.word_order_float32",
            ("check",),
            "массив WORD в GVL_IO, распаковка в PRG_C2aIoUpdate, строка io-map (FC, смещение, длина, период)",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-IO004",
            "Вход без проверки достоверности",
            "На REGUL при отказе канала значение «замерзает» (DPA-302 с. 136–148); у Modbus — статус канала "
            "ChannelStatus (DPA-302.1 с. 15–16). Проверка вставляется в PRG_C2aIoUpdate.",
            f"{DPA302} с. 136–148; {DPA3021} с. 15–16",
            ("check",),
            "проверка статуса канала в PRG_C2aIoUpdate; при отказе — последнее достоверное значение и флаг",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-MB001",
            "Modbus 3S (стандартный стек CODESYS)",
            "Документация РегЛаб описывает только свои драйверы (PsIoDrvModbus*). Мастер 3S -> Modbus TCP Master "
            "OS; FC 23 -> ФБ ModbusUserRequest; области slave -> PsModbus*Slave.",
            f"{DPA3021} с. 6–29, прил. А",
            ("check", "todo"),
            "строка io-map на канал REGUL; slave — todo",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-TASK001",
            "Приоритеты задач",
            "На REGUL приоритеты 0–15: 0 — RegulBus, 1 — синхронизируемая задача резервирования (4 на ЦП II "
            "типа, 1–3 там запрещены), 14 — системные службы, 15 — визуализация. Остальные задачи "
            "переназначаются в полосу 2–13 (5–13) с сохранением порядка (PROMPT §7.5).",
            "профиль tasks.*; DPA-302 с. 46; DPA-302.4 с. 17, 22",
            ("check", "info"),
            "таблица до/после; задачи создаются по IMPORT_STEPS (импорт их не переносит — проба P6)",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-TASK002",
            "Свободные задачи, быстрые задачи, >100 задач, >1 приложения",
            "Свободную задачу нельзя использовать как задачу цикла шины; задача быстрее цикла RegulBus теряет "
            "смысл; на ЦП не больше 100 задач и одно приложение (devdesc R500).",
            f"{DPA302} с. 46–47; профиль tasks.max_tasks, memory.max_apps",
            ("check", "todo"),
            "—",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-LIB001",
            "Вызов POU вендорной библиотеки",
            "Библиотек ОВЕН в Astra.IDE нет. По таблице замен: map -> auto (другое имя), wrap -> check (обёртка "
            "AstraCompat с теми же пинами), stub/none -> todo (вызов остаётся, ошибка компиляции ожидаема).",
            "data/libmap/*.toml, data/owen_signatures.toml",
            ("auto", "check", "todo"),
            "замена имени POU/типа (ST и атрибут typeName графики); маркер",
            "ST",
        ),
        RuleInfo(
            "C2A-LIB002",
            "Ссылки на библиотеки",
            "Ссылки на библиотеки ОВЕН не переносятся, Standard 3.5.9.0 ОВЕН -> плейсхолдер Standard, "
            "библиотеки новее 3.5.17 -> todo, имена РегЛаб до 1.7.2.0 -> словарь DPA-302 прил. Л. Импорт PLCopen "
            "ссылки не создаёт (проба P3) — список идёт в IMPORT_STEPS.",
            f"{DPA302} прил. Л; профиль import.creates_library_refs",
            ("auto", "info", "todo"),
            "список ссылок цели (AstraCompat, Standard, драйверы) в IMPORT_STEPS и addData",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-SYM001",
            "Указатели и REFERENCE в символьной конфигурации",
            "С Astra.IDE 1.7.2.5 указатели и ссылки в символьной конфигурации запрещены. Объект Symbol "
            "Configuration в PLCopen не экспортируется — детектор по {attribute 'symbol'} и прагмам OPC UA.",
            "профиль symbols.pointers_forbidden_since; https://reglab.ru/soft/",
            ("check",),
            "—",
            "DECL",
        ),
        RuleInfo(
            "C2A-RED001",
            "Резервированная цель: указатели и объём синхронизации",
            "В синхронизируемых данных указатели запрещены (ошибка компиляции резервирования), объём — до "
            "500 КБ (ЦП I/III) или 100 КБ (ЦП II).",
            f"{DPA3024} с. 46–47",
            ("todo", "info"),
            "—",
            "DECL",
        ),
        RuleInfo(
            "C2A-RET001",
            "RETAIN/PERSISTENT",
            "На REGUL RETAIN пишется при каждом изменении (период ФС до 10 с) и сбрасывается при загрузке; "
            "объём — до 1 МБ. Запись RETAIN в каждом цикле грузит ЦП.",
            "конспект §13 п. 10; профиль memory.retain",
            ("info", "check"),
            "—",
            "DECL",
        ),
        RuleInfo(
            "C2A-PTR001",
            "Адреса в DWORD/UDINT, SIZEOF в смещениях",
            "ARM (ПЛК210) -> x86 (R500, pack-mode = 8): адресная арифметика через DWORD и SIZEOF в смещениях "
            "зависят от разрядности и выравнивания — сверить пробой SIZEOF(POINTER).",
            "профиль platform.pack_mode, platform.pointer_size",
            ("check",),
            "—",
            "ST",
        ),
        RuleInfo(
            "C2A-EXC001",
            "Обработка исключений через узел Watchdog",
            "Режим обработки исключений ОВЕН выбирается в конфигураторе; на REGUL — системные события задач и "
            "PsSysExcept (DPA-302 прил. И). Каркас обработчиков — вручную.",
            f"{DPA302} прил. И; {TARGETS} с. 23",
            ("todo",),
            "—",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-FMT001",
            "Вход без текстов объявлений",
            "Без interfaceasplaintext теряются VAR_INST, ABSTRACT, METHOD FINAL PRIVATE, комментарии и прагмы "
            "(kns docs/plcopen.md). Переэкспортируйте с флагом «объявления как простой текст».",
            "kns-port-domestic docs/plcopen.md, «Только TC6»",
            ("info",),
            "—",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-LANG-IL0",
            "POU с пустым телом (IL потерян при экспорте)",
            "POU на IL, экспортированный при выключенной опции IL, приходит с пустым <ST> (ext §3.3). Тело "
            "потеряно — переэкспорт с включённым IL.",
            "migration/research/ext-s7-all-languages.md §3.3",
            ("todo",),
            "—",
            "ST",
        ),
        RuleInfo(
            "C2A-LANG-IL",
            "Тело на IL",
            "Импорт <IL> не работает в обеих IDE (проба P4: «Unknown 'LD' element: 'xhtml'»). Подмножество IL "
            "переводится в ST (check), остальное — todo.",
            "профиль import.il; docs/PROBES.md P4",
            ("check", "todo"),
            "IL -> ST (LD/ST/S/R/AND/OR/XOR/NOT, арифметика, сравнения, JMP/CAL/RET)",
            "IL",
        ),
        RuleInfo(
            "C2A-LANG-SFC",
            "Тело на SFC",
            "SFC переносится как есть; IecSfc и неявные переменные шагов сверить (флаги SFC проекта не в XML).",
            "профиль import.graphics; docs/PROBES.md P5",
            ("check",),
            "—",
            "SFC",
        ),
        RuleInfo(
            "C2A-LANG-GRAPH",
            "Графическое тело (FBD, LD, CFC)",
            "Цель знает те же редакторы: тело переносится как есть, правятся только атрибуты (typeName) и "
            "выражения. executionOrderId CFC не трогается.",
            "профиль import.graphics, languages",
            ("info",),
            "—",
            "FBD",
        ),
        RuleInfo(
            "C2A-LANG-OOP",
            "Конструкции ООП",
            "EXTENDS, SUPER^, ABSTRACT, спецификаторы доступа, наследование интерфейсов — по флагам oop_* профиля "
            "(проба P8). Пока флаг unknown — check.",
            "профиль oop.*; docs/PROBES.md P8",
            ("check", "info"),
            "—",
            "DECL",
        ),
        RuleInfo(
            "C2A-SP18-UTF8",
            "UTF8#'…' и не-ASCII STRING во входе SP18+",
            "UTF8# — с компилятора 3.5.18.0. ASCII-литерал: префикс снимается (auto); иначе todo. При опции "
            "«UTF8 encoding for STRING» (её нет в XML: --source-option utf8-strings) каждый не-ASCII STRING -> check.",
            f"{CDSHELP}_cds_operands_constant_string_utf8.html",
            ("auto", "check", "todo"),
            "снять префикс UTF8# у ASCII-литерала",
            "ST",
        ),
        RuleInfo(
            "C2A-SP18-GEN",
            "VAR_GENERIC CONSTANT, FB<N>",
            "Константные обобщения — с 3.5.18. Мономорфизация FB_X_N — после 0.1.0.",
            f"{CDSHELP}_cds_vartypes_var_generic_constant.html",
            ("todo",),
            "—",
            "DECL",
        ),
        RuleInfo(
            "C2A-SP19-BIT",
            "Частичный доступ к битовым полям .%X/.%B/.%W/.%D/.%L",
            "С 3.5.19. .%Xn -> .n (auto); чтение .%B/.%W/.%D/.%L -> сдвиг и маска (auto); запись, вложенный "
            "доступ, ADR(…) -> todo/check.",
            "https://ftp.owen.ru/CoDeSys3/98_Books/FeaturesAndImprovements/ (F&I SP19)",
            ("auto", "check", "todo"),
            ".%Xn -> .n; чтение .%Bn -> TO_BYTE(SHR(x, 8*n)) и т. п.",
            "ST",
        ),
        RuleInfo(
            "C2A-SP20-LD",
            "Объект нового LD (SP20)",
            "Формат нового редактора LD не опубликован, образца нет: перевести в классический LD/FBD или ST в "
            "исходной IDE и переэкспортировать.",
            "https://ftp.owen.ru/CoDeSys3/98_Books/FeaturesAndImprovements/ (F&I SP20)",
            ("todo",),
            "—",
            "LD",
        ),
        RuleInfo(
            "C2A-SPxx-LIB",
            "Библиотеки компилятора новее 3.5.17",
            "String Libraries (≥ 3.5.19.50), IIoT Libraries SL и библиотеки 3.5.18+ в 3.5.17 не подключаются.",
            "https://content.helpme-codesys.com/en/CODESYS%20String%20Libraries/_strlib_expert_information.html",
            ("todo",),
            "—",
            "PROJECT",
        ),
        RuleInfo(
            "C2A-MARK",
            "Маркеры s7conv и kns во входе",
            "Маркеры s7-to-codesys (`// MIGRATION-CHECK:` без ID) и kns (`// PORT: [кат]`) распознаются, "
            "считаются и повторно не ставятся.",
            "migration/prompts/00-INDEX.md §4.1",
            ("info",),
            "—",
            "ST",
        ),
        RuleInfo(
            "C2A-EDIT",
            "Пересекающиеся правки",
            "Две правки задели одни символы: обе не применены, место — вручную.",
            "PROMPT M2",
            ("todo",),
            "—",
            "ST",
        ),
    )
}
