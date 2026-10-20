# Правила переноса C2A-*

Документ собирается из реестра `cds2astra/rules/registry.py` (`python tools/gen_docs.py`); у каждого правила
есть корпус pos/neg в `cds2astra/tests/corpus/<ID>/` (кроме `C2A-EDIT` — сторожа пересекающихся правок).
Исходы: **авто** (`auto`) — правка без смены семантики; **сверить** (`check`) — правка сделана, поведение
сверить (маркер `// MIGRATION-CHECK(ID)`); **вручную** (`todo`) — аналога нет (маркер `// MIGRATION-TODO(ID)`,
код не удаляется); **сведения** (`info`). Подробно — `cds2astra explain <ID>`.

| ID | Что | Исходы |
|---|---|---|
| `C2A-IO001` | AT-адреса %I/%Q/%M | сверить, вручную, сведения |
| `C2A-IO002` | Привязки к узлам таргета ОВЕН | сверить, вручную |
| `C2A-IO003` | Типизированные каналы шаблонов Mx210 | сверить |
| `C2A-IO004` | Вход без проверки достоверности | сверить |
| `C2A-MB001` | Modbus 3S (стандартный стек CODESYS) | сверить, вручную |
| `C2A-TASK001` | Приоритеты задач | сверить, сведения |
| `C2A-TASK002` | Свободные задачи, быстрые задачи, >100 задач, >1 приложения | сверить, вручную |
| `C2A-LIB001` | Вызов POU вендорной библиотеки | авто, сверить, вручную |
| `C2A-LIB002` | Ссылки на библиотеки | авто, сведения, вручную |
| `C2A-SYM001` | Указатели и REFERENCE в символьной конфигурации | сверить |
| `C2A-RED001` | Резервированная цель: указатели и объём синхронизации | вручную, сведения |
| `C2A-RET001` | RETAIN/PERSISTENT | сведения, сверить |
| `C2A-PTR001` | Адреса в DWORD/UDINT, SIZEOF в смещениях | сверить |
| `C2A-EXC001` | Обработка исключений через узел Watchdog | вручную |
| `C2A-FMT001` | Вход без текстов объявлений | сведения |
| `C2A-LANG-IL0` | POU с пустым телом (IL потерян при экспорте) | вручную |
| `C2A-LANG-IL` | Тело на IL | сверить, вручную |
| `C2A-LANG-SFC` | Тело на SFC | сверить |
| `C2A-LANG-GRAPH` | Графическое тело (FBD, LD, CFC) | сведения |
| `C2A-LANG-OOP` | Конструкции ООП | сверить, сведения |
| `C2A-SP18-UTF8` | UTF8#'…' и не-ASCII STRING во входе SP18+ | авто, сверить, вручную |
| `C2A-SP18-GEN` | VAR_GENERIC CONSTANT, FB<N> | вручную |
| `C2A-SP19-BIT` | Частичный доступ к битовым полям .%X/.%B/.%W/.%D/.%L | авто, сверить, вручную |
| `C2A-SP20-LD` | Объект нового LD (SP20) | вручную |
| `C2A-SPxx-LIB` | Библиотеки компилятора новее 3.5.17 | вручную |
| `C2A-MARK` | Маркеры s7conv и kns во входе | сведения |
| `C2A-EDIT` | Пересекающиеся правки | вручную |

## C2A-IO001 — AT-адреса %I/%Q/%M

Адреса %I/%Q ОВЕН не совпадают с автоназначением REGUL по порядку модулей (DPA-302 с. 136–148): AT снимается, переменная уходит в GVL_IO, привязка канала — по io-map. %M проверяется по объёму.

- Исходы: сверить (`check`), вручную (`todo`), сведения (`info`).
- Автоправка: снять AT, перенести переменную в GVL_IO, переписать квалифицированные ссылки, строка io-map.
- Источник: https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf с. 136–148; профиль memory.marker.
- Язык находки по умолчанию: DECL.

## C2A-IO002 — Привязки к узлам таргета ОВЕН

Узлы OwenRTC, Watchdog, Info, Network, LeftSide… есть только в таргете ОВЕН. Переменные, привязанные к их каналам, получают источник по таблице замен (FB_C2aRtc) или остаются todo.

- Исходы: сверить (`check`), вручную (`todo`).
- Автоправка: OwenRTC -> FB_C2aRtc в PRG_C2aIoUpdate; прочие узлы -> todo с подсказкой.
- Источник: https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Targets_v3.4.pdf разд. 4.
- Язык находки по умолчанию: PROJECT.

## C2A-IO003 — Типизированные каналы шаблонов Mx210

Драйверы Modbus REGUL отдают канал как ARRAY OF WORD (DPA-302.1 с. 15–16), а не REAL: на блок регистров создаётся канал Modbus TCP Outer Slave OS, распаковка — FB_C2aMbUnpack. Порядок слов FLOAT32 по профилю unknown -> check.

- Исходы: сверить (`check`).
- Автоправка: массив WORD в GVL_IO, распаковка в PRG_C2aIoUpdate, строка io-map (FC, смещение, длина, период).
- Источник: https://reglab.ru/upload/iblock/c63/bxjpd31viamzx3b4i0nj0zthy4xq1sg1/Modbus-User-Guide-DPA_302-1_v1.7_rus.pdf с. 13–16; профиль modbus.word_order_float32.
- Язык находки по умолчанию: PROJECT.

## C2A-IO004 — Вход без проверки достоверности

На REGUL при отказе канала значение «замерзает» (DPA-302 с. 136–148); у Modbus — статус канала ChannelStatus (DPA-302.1 с. 15–16). Проверка вставляется в PRG_C2aIoUpdate.

- Исходы: сверить (`check`).
- Автоправка: проверка статуса канала в PRG_C2aIoUpdate; при отказе — последнее достоверное значение и флаг.
- Источник: https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf с. 136–148; https://reglab.ru/upload/iblock/c63/bxjpd31viamzx3b4i0nj0zthy4xq1sg1/Modbus-User-Guide-DPA_302-1_v1.7_rus.pdf с. 15–16.
- Язык находки по умолчанию: PROJECT.

## C2A-MB001 — Modbus 3S (стандартный стек CODESYS)

Документация РегЛаб описывает только свои драйверы (PsIoDrvModbus*). Мастер 3S -> Modbus TCP Master OS; FC 23 -> ФБ ModbusUserRequest; области slave -> PsModbus*Slave.

- Исходы: сверить (`check`), вручную (`todo`).
- Автоправка: строка io-map на канал REGUL; slave — todo.
- Источник: https://reglab.ru/upload/iblock/c63/bxjpd31viamzx3b4i0nj0zthy4xq1sg1/Modbus-User-Guide-DPA_302-1_v1.7_rus.pdf с. 6–29, прил. А.
- Язык находки по умолчанию: PROJECT.

## C2A-TASK001 — Приоритеты задач

На REGUL приоритеты 0–15: 0 — RegulBus, 1 — синхронизируемая задача резервирования (4 на ЦП II типа, 1–3 там запрещены), 14 — системные службы, 15 — визуализация. Остальные задачи переназначаются в полосу 2–13 (5–13) с сохранением порядка (PROMPT §7.5).

- Исходы: сверить (`check`), сведения (`info`).
- Автоправка: таблица до/после; задачи создаются по IMPORT_STEPS (импорт их не переносит — проба P6).
- Источник: профиль tasks.*; DPA-302 с. 46; DPA-302.4 с. 17, 22.
- Язык находки по умолчанию: PROJECT.

## C2A-TASK002 — Свободные задачи, быстрые задачи, >100 задач, >1 приложения

Свободную задачу нельзя использовать как задачу цикла шины; задача быстрее цикла RegulBus теряет смысл; на ЦП не больше 100 задач и одно приложение (devdesc R500).

- Исходы: сверить (`check`), вручную (`todo`).
- Автоправка: —.
- Источник: https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf с. 46–47; профиль tasks.max_tasks, memory.max_apps.
- Язык находки по умолчанию: PROJECT.

## C2A-LIB001 — Вызов POU вендорной библиотеки

Библиотек ОВЕН в Astra.IDE нет. По таблице замен: map -> auto (другое имя), wrap -> check (обёртка AstraCompat с теми же пинами), stub/none -> todo (вызов остаётся, ошибка компиляции ожидаема).

- Исходы: авто (`auto`), сверить (`check`), вручную (`todo`).
- Автоправка: замена имени POU/типа (ST и атрибут typeName графики); маркер.
- Источник: data/libmap/*.toml, data/owen_signatures.toml.
- Язык находки по умолчанию: ST.

## C2A-LIB002 — Ссылки на библиотеки

Ссылки на библиотеки ОВЕН не переносятся, Standard 3.5.9.0 ОВЕН -> плейсхолдер Standard, библиотеки новее 3.5.17 -> todo, имена РегЛаб до 1.7.2.0 -> словарь DPA-302 прил. Л. Импорт PLCopen ссылки не создаёт (проба P3) — список идёт в IMPORT_STEPS.

- Исходы: авто (`auto`), сведения (`info`), вручную (`todo`).
- Автоправка: список ссылок цели (AstraCompat, Standard, драйверы) в IMPORT_STEPS и addData.
- Источник: https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf прил. Л; профиль import.creates_library_refs.
- Язык находки по умолчанию: PROJECT.

## C2A-SYM001 — Указатели и REFERENCE в символьной конфигурации

С Astra.IDE 1.7.2.5 указатели и ссылки в символьной конфигурации запрещены. Объект Symbol Configuration в PLCopen не экспортируется — детектор по {attribute 'symbol'} и прагмам OPC UA.

- Исходы: сверить (`check`).
- Автоправка: —.
- Источник: профиль symbols.pointers_forbidden_since; https://reglab.ru/soft/.
- Язык находки по умолчанию: DECL.

## C2A-RED001 — Резервированная цель: указатели и объём синхронизации

В синхронизируемых данных указатели запрещены (ошибка компиляции резервирования), объём — до 500 КБ (ЦП I/III) или 100 КБ (ЦП II).

- Исходы: вручную (`todo`), сведения (`info`).
- Автоправка: —.
- Источник: https://reglab.ru/upload/iblock/28f/tmu37n4jz4w5oxepmx0431vb5q5yo6xw/Redundancy-User-Guide-_DPA_302_4_v2_11_rus.pdf с. 46–47.
- Язык находки по умолчанию: DECL.

## C2A-RET001 — RETAIN/PERSISTENT

На REGUL RETAIN пишется при каждом изменении (период ФС до 10 с) и сбрасывается при загрузке; объём — до 1 МБ. Запись RETAIN в каждом цикле грузит ЦП.

- Исходы: сведения (`info`), сверить (`check`).
- Автоправка: —.
- Источник: конспект §13 п. 10; профиль memory.retain.
- Язык находки по умолчанию: DECL.

## C2A-PTR001 — Адреса в DWORD/UDINT, SIZEOF в смещениях

ARM (ПЛК210) -> x86 (R500, pack-mode = 8): адресная арифметика через DWORD и SIZEOF в смещениях зависят от разрядности и выравнивания — сверить пробой SIZEOF(POINTER).

- Исходы: сверить (`check`).
- Автоправка: —.
- Источник: профиль platform.pack_mode, platform.pointer_size.
- Язык находки по умолчанию: ST.

## C2A-EXC001 — Обработка исключений через узел Watchdog

Режим обработки исключений ОВЕН выбирается в конфигураторе; на REGUL — системные события задач и PsSysExcept (DPA-302 прил. И). Каркас обработчиков — вручную.

- Исходы: вручную (`todo`).
- Автоправка: —.
- Источник: https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf прил. И; https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Targets_v3.4.pdf с. 23.
- Язык находки по умолчанию: PROJECT.

## C2A-FMT001 — Вход без текстов объявлений

Без interfaceasplaintext теряются VAR_INST, ABSTRACT, METHOD FINAL PRIVATE, комментарии и прагмы (kns docs/plcopen.md). Переэкспортируйте с флагом «объявления как простой текст».

- Исходы: сведения (`info`).
- Автоправка: —.
- Источник: kns-port-domestic docs/plcopen.md, «Только TC6».
- Язык находки по умолчанию: PROJECT.

## C2A-LANG-IL0 — POU с пустым телом (IL потерян при экспорте)

POU на IL, экспортированный при выключенной опции IL, приходит с пустым <ST> (ext §3.3). Тело потеряно — переэкспорт с включённым IL.

- Исходы: вручную (`todo`).
- Автоправка: —.
- Источник: migration/research/ext-s7-all-languages.md §3.3.
- Язык находки по умолчанию: ST.

## C2A-LANG-IL — Тело на IL

Импорт <IL> не работает в обеих IDE (проба P4: «Unknown 'LD' element: 'xhtml'»). Подмножество IL переводится в ST (check), остальное — todo.

- Исходы: сверить (`check`), вручную (`todo`).
- Автоправка: IL -> ST (LD/ST/S/R/AND/OR/XOR/NOT, арифметика, сравнения, JMP/CAL/RET).
- Источник: профиль import.il; docs/PROBES.md P4.
- Язык находки по умолчанию: IL.

## C2A-LANG-SFC — Тело на SFC

SFC переносится как есть; IecSfc и неявные переменные шагов сверить (флаги SFC проекта не в XML).

- Исходы: сверить (`check`).
- Автоправка: —.
- Источник: профиль import.graphics; docs/PROBES.md P5.
- Язык находки по умолчанию: SFC.

## C2A-LANG-GRAPH — Графическое тело (FBD, LD, CFC)

Цель знает те же редакторы: тело переносится как есть, правятся только атрибуты (typeName) и выражения. executionOrderId CFC не трогается.

- Исходы: сведения (`info`).
- Автоправка: —.
- Источник: профиль import.graphics, languages.
- Язык находки по умолчанию: FBD.

## C2A-LANG-OOP — Конструкции ООП

EXTENDS, SUPER^, ABSTRACT, спецификаторы доступа, наследование интерфейсов — по флагам oop_* профиля (проба P8). Пока флаг unknown — check.

- Исходы: сверить (`check`), сведения (`info`).
- Автоправка: —.
- Источник: профиль oop.*; docs/PROBES.md P8.
- Язык находки по умолчанию: DECL.

## C2A-SP18-UTF8 — UTF8#'…' и не-ASCII STRING во входе SP18+

UTF8# — с компилятора 3.5.18.0. ASCII-литерал: префикс снимается (auto); иначе todo. При опции «UTF8 encoding for STRING» (её нет в XML: --source-option utf8-strings) каждый не-ASCII STRING -> check.

- Исходы: авто (`auto`), сверить (`check`), вручную (`todo`).
- Автоправка: снять префикс UTF8# у ASCII-литерала.
- Источник: https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operands_constant_string_utf8.html.
- Язык находки по умолчанию: ST.

## C2A-SP18-GEN — VAR_GENERIC CONSTANT, FB<N>

Константные обобщения — с 3.5.18. Мономорфизация FB_X_N — после 0.1.0.

- Исходы: вручную (`todo`).
- Автоправка: —.
- Источник: https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_vartypes_var_generic_constant.html.
- Язык находки по умолчанию: DECL.

## C2A-SP19-BIT — Частичный доступ к битовым полям .%X/.%B/.%W/.%D/.%L

С 3.5.19. .%Xn -> .n (auto); чтение .%B/.%W/.%D/.%L -> сдвиг и маска (auto); запись, вложенный доступ, ADR(…) -> todo/check.

- Исходы: авто (`auto`), сверить (`check`), вручную (`todo`).
- Автоправка: .%Xn -> .n; чтение .%Bn -> TO_BYTE(SHR(x, 8*n)) и т. п..
- Источник: https://ftp.owen.ru/CoDeSys3/98_Books/FeaturesAndImprovements/ (F&I SP19).
- Язык находки по умолчанию: ST.

## C2A-SP20-LD — Объект нового LD (SP20)

Формат нового редактора LD не опубликован, образца нет: перевести в классический LD/FBD или ST в исходной IDE и переэкспортировать.

- Исходы: вручную (`todo`).
- Автоправка: —.
- Источник: https://ftp.owen.ru/CoDeSys3/98_Books/FeaturesAndImprovements/ (F&I SP20).
- Язык находки по умолчанию: LD.

## C2A-SPxx-LIB — Библиотеки компилятора новее 3.5.17

String Libraries (≥ 3.5.19.50), IIoT Libraries SL и библиотеки 3.5.18+ в 3.5.17 не подключаются.

- Исходы: вручную (`todo`).
- Автоправка: —.
- Источник: https://content.helpme-codesys.com/en/CODESYS%20String%20Libraries/_strlib_expert_information.html.
- Язык находки по умолчанию: PROJECT.

## C2A-MARK — Маркеры s7conv и kns во входе

Маркеры s7-to-codesys (`// MIGRATION-CHECK:` без ID) и kns (`// PORT: [кат]`) распознаются, считаются и повторно не ставятся.

- Исходы: сведения (`info`).
- Автоправка: —.
- Источник: migration/prompts/00-INDEX.md §4.1.
- Язык находки по умолчанию: ST.

## C2A-EDIT — Пересекающиеся правки

Две правки задели одни символы: обе не применены, место — вручную.

- Исходы: вручную (`todo`).
- Автоправка: —.
- Источник: PROMPT M2.
- Язык находки по умолчанию: ST.
