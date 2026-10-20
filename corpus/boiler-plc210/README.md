# Котельная на ПЛК210 (синтетический слой ОВЕН)

Вымышленная котельная №3: два газовых котла, насос сетевого контура, погодозависимая уставка подачи,
резервный электрокотёл. Проект написан как типичный проект ОВЕН ПЛК210 на CODESYS 3.5.17.30 — чтобы на нём
проверить весь путь cds2astra: AT-адреса, узлы таргета, модули Mx210 по Modbus TCP, вызовы библиотек ОВЕН,
приоритеты задач 0/1/15, RETAIN.

**Класс фикстуры — `synthetic`** (`FIXTURE.toml`). Код ST — рукописный (`src/`), дерево ПЛК210 с узлами
ОВЕН наложено скриптом `tools/corpus/owen_overlay.py`: проба P7 (таргеты ОВЕН в CODESYS) не выполнялась,
поэтому `DeviceIdentification` узлов ОВЕН — заглушки `SYN …`, коннекторы — `Owen.Synthetic`. Исходный
проект в CODESYS с таргетами ОВЕН не собирался; собирается выход cds2astra (Astra.IDE 1.7.2.2 и CODESYS
3.5.17.30, `docs/TEST_REPORT.md`).

## Состав

| Объект | Что делает | На чём проверяется перенос |
|---|---|---|
| `PRG_Fast` (FastTask, 10 мс, приоритет 0) | аварии горелок → состояние `Fault`, сирена | AT `%IX/%QX` → `GVL_IO` (C2A-IO001), приоритет 0 (только RegulBus на REGUL) → 2 (C2A-TASK001) |
| `PRG_Main` (MainTask, 50 мс, приоритет 1) | погодная кривая `F_HeatingCurve`, ПИД подачи `OPR.STD_PID`, насос, маска выходов МУ210-402, наработка; строки для HMI через `OSU.CONCAT4`, `OSU.REAL_TO_STRING_FORMAT`, `OSU.WORD_TO_HEX_STR` | замена `STD_PID` → `FB_C2aPid` (обёртка), OwenStringUtils → AstraCompat (`map`) — C2A-LIB001; RETAIN (C2A-RET001) |
| `PRG_Slow` (SlowTask, 1000 мс, приоритет 15) | слово состояния для HMI | приоритет 15 (на REGUL — визуализация) → 4 (C2A-TASK001) |
| `PRG_Backup` (MainTask) | резервный электрокотёл на `OPR.ON_OFF_HIST_REG` | замены нет (`none`) → `todo`; в оракулах ошибки сборки только здесь |
| `GVL_Hw` | входы и выходы ПЛК210 через `AT` | C2A-IO001 |
| `GVL_Mx` | значения МВ210-101 (три FLOAT32 и INT), маска МУ210-402, статус счётчика на Modbus 3S | C2A-IO003, C2A-IO004, C2A-MB001 |
| `GVL_Clock` | дата и время OwenRTC, код последнего исключения Watchdog (привязки к узлам таргета) | OwenRTC → `FB_C2aRtc`, C2A-IO002 (`check` и `todo`) |
| `GVL_Persist` | RETAIN: базовая уставка, наработка насоса | C2A-RET001 |
| `GVL_Hmi`, `E_BoilerState` | состояние для HMI | — |

Слой ОВЕН в `export.xml`: ПЛК210 с узлами OwenRTC и Watchdog, Ethernet → Modbus TCP Master (способ 2 из
документации ОВЕН) → МВ210-101 (канал `MV210_101_K3`) и МУ210-402 (`MU210_402_K3`) с каналами шаблонов
Mx210, стандартный `ModbusTCP_Slave_Device_Meter` (канал FC 23). Цель переноса — `target.toml`: REGUL R500
61, RegulBus OS, без резервирования.

```bash
python tools/corpus/owen_overlay.py            # пересобрать export.xml из src/
cds2astra migrate corpus/boiler-plc210/export.xml --target-spec corpus/boiler-plc210/target.toml --out out/boiler
```
