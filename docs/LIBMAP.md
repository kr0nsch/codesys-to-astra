# Таблица замен библиотек ОВЕН

Собирается из `cds2astra/data/libmap/*.toml` (`python tools/gen_docs.py`). Вид: `map` — другое имя, та же
семантика (авто); `wrap` — обёртка AstraCompat с теми же пинами (сверить); `stub`/`none` — аналога нет
(вручную). Сигнатуры POU ОВЕН — `cds2astra/data/owen_signatures.toml` (документ, версия, страница, SHA-256
PDF); тест сверяет пины обёрток AstraCompat с ними.

| Библиотека | POU ОВЕН | Вид | Замена | Документ | Уверенность | Примечание |
|---|---|---|---|---|---|---|
| CmpOwenPidRegs | `STD_PID` | wrap | `FB_C2aPid` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf#page=10) | M | интерфейс STD_PID поверх Util.PID: алгоритм другой (XN, VSP, INF, PV_TIME не повторяются) — всегда check |
| CmpOwenPidRegs | `ON_OFF_HIST_REG` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf#page=9) | H | логика зоны нечувствительности описана только рисунком — реализовать по месту |
| CmpOwenPidRegs | `APID_POS_VALV` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf#page=12) | H | ПИД с автонастройкой: автонастройки на REGUL нет (Util.PID, PsTechOG) |
| CmpOwenPidRegs | `APID_PWM` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf#page=15) | H | см. APID_POS_VALV |
| CmpOwenPidRegs | `DIG_FLTR` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf#page=7) | H |  |
| CmpOwenPidRegs | `PSI_MOIST` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_CmpOwenPidRegs_v2.2.pdf#page=8) | H |  |
| OwenStringUtils | `WORD_TO_HEX_STR` | wrap | `F_C2aWordToHexStr` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=51) | H |  |
| OwenStringUtils | `HEX_STR_TO_WORD` | wrap | `F_C2aHexStrToWord` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=50) | H |  |
| OwenStringUtils | `Before` | wrap | `F_C2aBefore` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=15) | H |  |
| OwenStringUtils | `After` | wrap | `F_C2aAfter` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=19) | H |  |
| OwenStringUtils | `ADD_CHAR` | wrap | `F_C2aAddChar` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=33) | H |  |
| OwenStringUtils | `CONCAT4` | wrap | `F_C2aConcat4` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=39) | H |  |
| OwenStringUtils | `REAL_TO_STRING_FORMAT` | wrap | `F_C2aRealToStringFormat` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=9) | M | округление и экспоненциальная запись (> 1e8) могут отличаться в последнем знаке — check |
| OwenStringUtils | `DECIMAL_SEPARATOR` | map | `E_C2aDecimalSeparator` | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=9) | H | тип перечисления: DOT = 0, COMMA = 1 (USINT), табл. 3.2.2 |
| OwenStringUtils | `LowerCase` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=52) | H | CP1251-регистр: кириллица в STRING на Astra требует отдельного решения (kns R23) |
| OwenStringUtils | `UpperCase` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=54) | H | см. LowerCase |
| OwenStringUtils | `CP1251_TO_UNICODE` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenStringUtils_v3.0.pdf#page=7) | M | на Astra — PsUtils (UTF-8 <-> WSTRING), DPA-302 прил. Л; перекодировку CP1251 писать отдельно |
| OwenCommunication | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_Modbus_v3.2.pdf) | H | работает только на контроллерах ОВЕН; на REGUL — Modbus TCP/Serial Master (OS) + Outer Slave + каналы (DPA-302.1) |
| ModulsOwenLib | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/) | M | опрос модулей ОВЕН — каналы Modbus REGUL и FB_C2aMbUnpack |
| OwenNet | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/) | M | протокол ОВЕН по RS-485: своя реализация на SysCom / CAA SerialCom |
| OwenVendorProtocols | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/11_Documentation/03_3.5.11.5/CDSv3.5_OwenVendorProtocols_v2.9.pdf) | M | SysCom, SysSocket, CAA SerialCom, CAA NetBaseSrv; статистика COM — PsSysSerial |
| CmpSysExec | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/03_Targets/OwenTargets-3.5.17.36.txt) | M | вызов команд ОС — аналога на REGUL нет (оболочка ПЛК доступна только инженеру) |
| OwenArchiver | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/01_Components/) | M | SysFile / CAA File + PsSysFile |
| OwenStorage | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/03_Targets/OwenTargets-3.5.17.36.txt) | M | SysFile / CAA File + PsSysFile |
| OwenCloud | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/01_Components/) | M |  |
| OwenSnmp | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/) | M | SNMP на REGUL — системная служба, не библиотека |
| MQTT_Client | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/) | M | MQTT — своя реализация на SysSocket или шлюз |
| OwenVisuDialogs | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/) | M | визуализация в PLCopen XML не переносится |
| OwenVisuTools | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/04_Library/05_3.5.11.5/02_Libraries/) | M |  |
| OwenTypes | `*` | none | — | [документ](https://ftp.owen.ru/CoDeSys3/03_Targets/OwenTargets-3.5.17.36.txt) | H | типы узлов таргета (ExceptionHandling) удаляются вместе с узлами |

Узлы таргета ПЛК2xx (OwenRTC, Watchdog, LeftSide…) и модули Mx210 — `cds2astra/data/owen_modules.toml`,
правила C2A-IO002 и C2A-IO003 ([RULES.md](RULES.md)).
