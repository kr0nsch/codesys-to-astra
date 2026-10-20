# Источники

Каждый факт о продуктах вендоров в данных и правилах ссылается на документ из этого списка (страница —
в самой строке данных). PDF, пакеты, devdesc, библиотеки вендоров и чужие экспорты в репозиторий не
кладутся: только ссылки и SHA-256. Дата чтения документов — 19–20.10.2026.

## ОВЕН

| Документ | Что взято | SHA-256 |
|---|---|---|
| [CDSv3.5_OwenStringUtils_v3.0.pdf](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf) | сигнатуры `REAL_TO_STRING_FORMAT` (с. 9), `Before` (с. 15), `After` (с. 19), `ADD_CHAR` (с. 33), `CONCAT4` (с. 39), `HEX_STR_TO_WORD` (с. 50), `WORD_TO_HEX_STR` (с. 51), `LowerCase` (с. 52), `UpperCase` (с. 54); пространство имён `OSU` (с. 6) | `5570301ff6d96cb38fd80f78b2e2b0cee1f7e01f4880567e1a4301c73cf620b2` |
| [CDSv3.5_CmpOwenPidRegs_v2.2.pdf](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf) (10.06.2024, библиотека 3.5.14.33) | `STD_PID` (с. 10), `ON_OFF_HIST_REG` (с. 9), пространство имён `OPR` (с. 5) | `2a91eade9b563c8c7d1f01c83d8b843a5e0fc58dc65fcedec484f1f217bfb2f8` |
| [CDSv3.5_Targets_v3.4.pdf](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Targets_v3.4.pdf) | узлы таргета ПЛК2xx: OwenRTC, Watchdog, встроенные входы и выходы, режим обработки исключений | `d4fb22c2a5c27ab9fdb315dec294f275b8d02c12312e1819651b18888c836e91` |
| [РЭ МВ210-101, версия 1.41](https://owen.ru/uploads/167/re_mv210-101_1-ru-23540-1.41.pdf) | регистры измеренных значений (4000, шаг 3, FLOAT32), время цикла (4002), целые значения (4064), коды ошибок датчика (с. 36) | `86d5c9f3de0e52755017cc7a82d65976bb647717f31ec5c8103a9bdff6bff35d` |
| [РЭ МУ210-402, версия 2.9 (11.2022)](https://owen.ru/uploads/365/re_mu210-402_1-ru-44622-2.9_a4.pdf) | битовая маска выходов (регистр 470, WORD) | `63b1c1447796332705aa4a15dbcdf8cc47ddcbd0f62e253537c74263f51e8998` |
| [Карточка МВ210-101](https://owen.ru/product/mv210_101) | до 4 клиентов Modbus TCP (профиль источника) | — |
| [CDSv3.5_Modbus_v3.2.pdf](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Modbus_v3.2.pdf) | библиотека `OwenCommunication` — в таблице замен как `none` | — |
| [CDSv3.5_OwenVendorProtocols_v2.9.pdf](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenVendorProtocols_v2.9.pdf) | библиотека протоколов ОВЕН — в таблице замен как `none` | — |
| [CDSv3.5_Faq_v.3.7.pdf](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Faq_v.3.7.pdf) | компилятор 3.5.17.30 у ПЛК2xx (табл. 7.1), области ввода-вывода 64 КБ (п. 7.29), RETAIN/PERSISTENT 64 КБ (табл. 7.2) | — |
| [OwenTargets-3.5.17.36](https://ftp.owen.ru/CoDeSys3/03_Targets/OwenTargets-3.5.17.36.txt) | состав таргетов: `CmpSysExec`, `OwenStorage` — в таблице замен как `none` (проба P7 не выполнялась) | — |
| [Каталог библиотек 3.5.11.5](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/), [компоненты](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/01_Components/) | имена библиотек без замены (`ModulsOwenLib`, `OwenNet`, `OwenArchiver`, `OwenCloud`, `OwenSnmp`, `MQTT_Client`, …) | — |
| [Features and Improvements](https://ftp.owen.ru/CoDeSys3/98_Books/FeaturesAndImprovements/) | SP19: частичный доступ `.%B/.%W/.%D/.%L`; SP20: новый LD (профиль `source-codesys-sp18plus`) | — |

## РегЛаб (REGUL, Astra.IDE)

| Документ | Что взято |
|---|---|
| [Руководство пользователя Astra.IDE, DPA-302, v2.20](https://reglab.ru/upload/iblock/86e/aqrzbeuk0bjd3jdn1au63e8i2r5d63wk/Astra-IDE-User-Guide-_DPA_302_v2_20_rus.pdf) | приоритеты задач (с. 46, табл. 1: 0 — RegulBus, 2–3 выше сетевой подсистемы, 4–13 реальное время, 14 — системные службы), RETAIN, языки (с. 18, 32) |
| [Modbus, DPA-302.1, v1.7](https://reglab.ru/upload/iblock/c63/bxjpd31viamzx3b4i0nj0zthy4xq1sg1/Modbus-User-Guide-DPA_302-1_v1.7_rus.pdf) | Modbus TCP Master OS / Outer Slave OS, каналы `ARRAY OF WORD` (с. 15–16), таймауты (с. 25–27) |
| [Резервирование, DPA-302.4, v2.11](https://reglab.ru/upload/iblock/28f/tmu37n4jz4w5oxepmx0431vb5q5yo6xw/Redundancy-User-Guide-_DPA_302_4_v2_11_rus.pdf) | синхронизируемая задача (с. 17, 22), запрещённые приоритеты ЦП II типа, лимит синхронизируемых данных |
| [Пакет RegLab_Ltd_Regul_1.7.2.6](https://reglab.ru/upload/iblock/0fd/bkk3sngi1qu0kz62c3j1so8iykr78fr6/RegLab_Ltd_Regul_1.7.2.6.package) | devdesc REGUL R500 171: `defaulttaskpriority = 2`, `maxnumoftasks = 100`, `maxtaskpriority = 15`, размер областей ввода-вывода |
| [Курс РегЛаб: добавление объектов](https://reglab.ru/upload/materialy-kursa/dobavlenie_obektov_v_prilozhenie.htm) | «Включить IL» — опция среды |
| [Курс РегЛаб: VISU_TASK](https://reglab.ru/upload/materialy-kursa/zadacha_visu_task.htm) | приоритет задачи визуализации 15 |
| [Страница ПО РегЛаб](https://reglab.ru/soft/) | release notes 1.7.2.5: указатели и ссылки запрещены в символьной конфигурации (C2A-SYM001); образ ВПЛК R500 1.7.2.6 (E8) |
| локальная установка Astra.IDE 1.7.2.2 | `Profiles/Astra.IDE_V1.7.2.2.profile.xml` (компилятор 3.5.17.30, PLCopenXML 3.5.17.20), devdesc 11.7.2.60 из `C:/ProgramData/Astra.IDE_64_1.7.2.2/Devices` — читались, в репозиторий не копировались |

## CODESYS

| Документ | Что взято |
|---|---|
| [CODESYS Online Help](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/) | общий справочник по языку и PLCopen XML |
| [Строковые константы UTF8#](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operands_constant_string_utf8.html) | конструкция SP18+ (правило C2A-SP18-UTF8) |
| [VAR_GENERIC CONSTANT](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_vartypes_var_generic_constant.html) | конструкция SP18+ (правило C2A-SP18-GEN) |
| [String Libraries, expert information](https://content.helpme-codesys.com/en/CODESYS%20String%20Libraries/_strlib_expert_information.html) | CODESYS String Libraries с 3.5.19.50 (C2A-SPxx-LIB) |
| [Версии библиотек](https://content.helpme-codesys.com/en/LibDevSummary/versions.html) | каждая среда содержит компиляторы начиная с 3.5.17.0 (основа понижения SP18+) |
| локальная установка CODESYS 3.5.17.30 | оракул сборки и coUnit |

## Стандарты и форматы

| Документ | Что взято | SHA-256 |
|---|---|---|
| [PLCopen TC6 XML 2.01, архив со схемой](https://www.plcopen.org/download_file/force/d397ab98-6a21-47d5-9fb1-37da9e94ef34/342/) | `tc6_xml_v201.xsd` — сетевой тест структуры выхода | `591b92ba65018a77c32ab9e606abf27bd810cb1f7761d972a85689531c51e20f` (xsd) |
| [Modbus Application Protocol V1.1b3](https://modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf) | предел 125 регистров для FC 3/4, исключение 02 | — |

## Публичные образцы (в репозиторий не кладутся, кроме MIT)

| Образец | Коммит | SHA-256 | Где |
|---|---|---|---|
| [niksosov/astraregul_stand](https://github.com/niksosov/astraregul_stand), `AstraRegul_stand.xml` (экспорт Astra.IDE V1.7.0.0) | `851ac492` | `1c3d8d5731c9ff7faaa683d7cbe9aaeb6e5c6c3de28b074ac4be124866acf09d` | кэш `.cache/` (`tools/fetch_samples.py`), лицензии нет — только ссылка |
| [tkucic/codesys_code_execution_speedTests](https://github.com/tkucic/codesys_code_execution_speedTests), SP18 Patch 2 | `d3abcf45` | `3d56646f8d34e0b1bfb77b8d343c72817c318d5c0975ba70784c612bc8d9f80a` | `corpus/sp18-speedtests/` (MIT, лицензия рядом) |
| [ThorstenBrach/SRCI](https://github.com/ThorstenBrach/SRCI), `RobotLibrarySysDep_3S.xml` | `67fd773b` | `fe47b4f371a8efc74e98ac346a4b88f220f575379645bb288c5422d186168632` | `corpus/srci/` (MIT, лицензия рядом) |
| [kr0nsch/s7-to-codesys](https://github.com/kr0nsch/s7-to-codesys) 1.0 | `2285760` | — | `corpus/s7-chain/` и `tools/` (MIT, тот же автор) |
| [kr0nsch/kns-port-domestic](https://github.com/kr0nsch/kns-port-domestic) | `6262d0f` | — | конвертер раскладки, образец оракула, фикстура ООП для P8; [BUILD_ERRORS 1.1](https://github.com/kr0nsch/kns-port-domestic/blob/main/docs/BUILD_ERRORS.md) — тип статуса канала Modbus |

## Обсуждения (почему инструмент нужен)

| Ссылка | О чём |
|---|---|
| [Форум CODESYS: «Device not found» при импорте](https://forge.codesys.com/forge/talk/Engineering/thread/56e672bed8) | ошибка «Device not found» при импорте проекта, если в среде нет описания устройства; в пробах P1/P2 устройство из чужого экспорта тоже не принимается |
| [Форум CODESYS: блокировка сервера развёртывания для РФ](https://forge.codesys.com/forge/talk/Engineering/thread/a642d5cb92/) | сервер развёртывания CODESYS недоступен пользователям из РФ |
| [Форум CODESYS: визуализация не экспортируется в PLCopenXML](https://forge.codesys.com/forge/talk/Visualization/thread/35ee036484/) | визуализация переносится отдельно (E7), в `astra-import.xml` её нет |
