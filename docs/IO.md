# Ввод-вывод: из ОВЕН в REGUL

Как cds2astra переносит привязки ввода-вывода проекта ПЛК2xx на REGUL. Стратегия 0.1.0 — **keep-modbus**:
модули Mx210 остаются в поле, их опрашивает мастер `Modbus TCP Master OS` контроллера REGUL. Стратегия
`--io local` (замена Mx210 модулями REGUL в крейте) отложена (`docs/ROADMAP.md`).

## Что во что превращается

| В проекте ОВЕН | Правило | В выходе |
|---|---|---|
| `AT %I*/%Q*` в любой GVL или POU | C2A-IO001 | переменная переезжает в `GVL_IO` без `AT` (комментарий «было: AT %IX0.0 в GVL_Hw»), обращения `GVL_Hw.x` переименовываются в `GVL_IO.x`; привязка к каналу модуля REGUL — в мастере конфигурации по `io-map` (`check`) |
| `AT %M*` | C2A-IO001 | остаётся как есть: область `%M` на REGUL есть (`info`) |
| привязки к узлам таргета ОВЕН (OwenRTC, Watchdog, LeftSide …) | C2A-IO002 | OwenRTC → `FB_C2aRtc` (AstraCompat, на `SysTimeRtc`): присваивания в `PRG_C2aIoUpdate`; каналы без аналога («Week of year», «Last Exception Code») — `todo` |
| каналы шаблонов Mx210 под Modbus TCP Master ОВЕН (способ 2 ОВЕН) | C2A-IO003 | каналы `Modbus TCP Outer Slave OS` с массивами `ARRAY OF WORD` в `GVL_IO` (`awMbR_<модуль>_<канал>`, `awMbW_…`) и распаковка в `PRG_C2aIoUpdate` |
| значение канала читается без проверки связи | C2A-IO004 | признак `xRValid_…` из статуса канала; переменные процесса обновляются только при `ChannelStatus.Ok` |
| стандартный Modbus 3S (`ModbusTCP_Slave_Device` и т. п.) | C2A-MB001 | канал Outer Slave OS по таблице, `check` |

`PRG_C2aIoUpdate` вызывается первым в задаче, где опрашивался ввод-вывод (шаг 6 `IMPORT_STEPS.md`; оракул
ставит его первым в самую быструю задачу): распаковка входов идёт до логики.

## Каналы Modbus

Регистры модулей — из РЭ ОВЕН (`cds2astra/data/owen_modules.toml`, страница у каждой строки):

| Модуль | Значение | Регистр | Тип | Функция |
|---|---|---|---|---|
| МВ210-101 | «Вход N/Измеренное значение» | 4000 + 3·(N−1) | FLOAT32, 2 регистра | FC 4 |
| МВ210-101 | «Вход N/Циклическое время измерения» | 4002 + 3·(N−1) | UINT | FC 4 |
| МВ210-101 | «Вход N/Значение (integer)» | 4064 + (N−1) | INT, 1 регистр | FC 4 |
| МУ210-402 | «Выходы/Битовая маска установки» | 470 | WORD | FC 16 |

Соседние регистры одного модуля и одной функции объединяются в канал, если пропуск не больше 4
регистров и длина не больше 120 (`docs/ASSUMPTIONS.md` A8). Так у котельной вышло три канала: МВ210-101
4000..4007 (три FLOAT32), МВ210-101 4064 (INT) и МУ210-402 470 (запись).

### Распаковка

```iecst
GVL_IO.xRValid_MV210_101_K3 := GVL_IO.eMbStR_MV210_101_K3 = PsIoDrvModbusTcpMaster_OS.ChannelStatus.Ok;
IF GVL_IO.xRValid_MV210_101_K3 THEN
    GVL_Mx.rTSupply_C := F_C2aMbToReal(GVL_IO.awMbR_MV210_101_K3[0], GVL_IO.awMbR_MV210_101_K3[1], GVL_IO.eC2aWordOrder);
END_IF
```

- `F_C2aMbToReal(w0, w1, eOrder)` — два регистра в REAL через `U_C2aReal32` (побитно, без арифметики).
- `FB_C2aMbUnpack` — распаковка REAL (по порядку слов), INT и WORD из массива канала по индексу с проверкой
  границ; тесты coUnit сверяют оба порядка слов.
- `F_C2aMx210Status` / `E_C2aMx210Status` — коды ошибок датчика МВ210 (РЭ с. 36), которые модуль передаёт
  в регистре значения.
- Тип статуса канала `PsIoDrvModbusTcpMaster_OS.ChannelStatus` и значение `Ok` сверены сборкой против
  настоящей библиотеки драйвера 1.7.2.60 в Astra.IDE (профиль `modbus.status_type_tcp`, `verified_local`).
  Для сборки в CODESYS вместо драйвера ставится заглушка `C2aStub_PsIoDrvModbusTcpMaster_OS` с тем же
  типом.

### Порядок слов FLOAT32

`GVL_IO.eC2aWordOrder := E_C2aWordOrder.HighWordFirst` — одна строка на проект. Порядок слов модулей Mx210
через драйвер REGUL не сверен (профиль `modbus.word_order_float32 = unknown`), поэтому распаковка помечена
`MIGRATION-CHECK(C2A-IO003)`. Проверка — `docs/HARDWARE_VALIDATION.md`, раздел 2, или ВПЛК (E8).

## Файлы

| Файл | Что в нём |
|---|---|
| `io-map.csv` | `variable;type;direction;owen;regul;outcome;rule;source` — разделитель `;`, как у CSV Windows с русской локалью; свой формат: формат CSV привязок Astra.IDE не опубликован (E5) |
| `io-map.md` | то же таблицей для чтения |
| `regul-devices.xml` | фрагмент дерева устройств: ЦП REGUL R500 с коннекторами (импорт проверен, E6); модули Modbus перечислены комментарием и добавляются вручную |
| `IMPORT_STEPS.md` | порядок: устройства, библиотеки, импорт, задачи, каналы Modbus по `io-map` |

## Чего нет

- Модулей ввода-вывода REGUL в `regul-devices.xml` и автоматической привязки каналов (нужны образцы E5).
- Стратегии `--io local`.
- Проверки на железе: порядок слов, таймауты, поведение при обрыве связи (`HARDWARE_VALIDATION.md`).
