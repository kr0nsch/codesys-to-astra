# Отчёт о проверках

Дата прогона — **20.10.2026**. Машина: Windows 11, Python 3.12.10, Astra.IDE 1.7.2.2 (профиль
`Astra.IDE_V1.7.2.2`, устройство REGUL R500 61, devdesc 11.7.2.60), CODESYS 3.5.17.30 (профиль «CODESYS
V3.5 SP17 Patch 3», CODESYS Control Win V3). На контроллере REGUL и на ПЛК210 ничего не запускалось.

## Сводка

| Проверка | Результат |
|---|---|
| ruff check, ruff format --check | чисто |
| mypy --strict (`cds2astra`, `tools`) | 68 файлов, 0 ошибок |
| pytest | **688 пройдено** (151 — пакет `cds2astra`, 537 — `tools/`), 48.9 с |
| покрытие `cds2astra/` | строки **91.9 %** (порог 85), ветви **81.4 %** (порог 75) |
| round-trip `preserve` без правил | 100 % побайтно на всём корпусе и публичных образцах |
| корпус правил pos/neg | 26 правил × 2 = 52 случая, все зелёные |
| Hypothesis | мутации XML дают находку или `ImportError_`, не исключение; правки в любом порядке — один результат |
| идемпотентность, детерминизм | `migrate(migrate(x)) == migrate(x)`; два прогона побайтно равны, zip тоже |
| st_lint (`--strict`) | 98 файлов, 0 ошибок, 4 предупреждения STL011 (счёт циклов в многоцикловых тестах ПИД — так задуман тест) |
| RuSTy `plc --check` v1.0.6 | 19 файлов без ошибок (2 предупреждения E067 «Implicit downcast DINT → INT» в `F_C2aBefore`/`F_C2aAfter` — в RuSTy `FIND` возвращает DINT, в CODESYS — INT), 8 исключены: расхождения диалектов (`Util`, `SysTimeRtc`, индекс символа STRING) и зависящие от них объекты (`tools/check/rusty_exclude.txt`, `docs/STATIC_ANALYSIS.md`) |
| iec_checker v0.4 | 27 файлов, необоснованных 0, обоснованных 229 (`tools/check/iec_checker_allow.toml`), артефактов сборки 12 |
| AstraCompat в CODESYS 3.5.17.30 | «Проверить все объекты» с тестами: 27 объектов, 0 ошибок, 0 предупреждений |
| AstraCompat в Astra.IDE 1.7.2.2 | 21 объект, 0 ошибок, 0 предупреждений; установлена в репозиторий библиотек Astra.IDE |
| coUnit (CODESYS Control Win V3) | **25 из 25** тестов пройдены |
| оракулы импорта и сборки | 16 прогонов из 16 — OK (таблица ниже) |
| пробы A0 | 24 случая в двух IDE (`docs/PROBES.md`) |
| разметка FP | 115 находок, FP 0 (`docs/FP_LABELS.md`) |
| веб-демо e2e (Playwright, Chromium) | Pyodide считает котельную в браузере; SHA-256 zip из Pyodide = CPython (`fec7ae6d43f2d4e5…`), запросов к чужим доменам 0 |
| actionlint | `ci.yml`, `pages.yml` — чисто |

## Оракулы: Astra.IDE 1.7.2.2 и CODESYS 3.5.17.30

`python tools/run_oracles.py` → `docs/oracle-results.json`. Для каждого случая: `cds2astra migrate`,
затем в каждой IDE новый проект, библиотеки (Standard, Util, SysTimeRtc, AstraCompat; в Astra.IDE —
настоящий `PsIoDrvModbusTcpMaster_OS`, в CODESYS — заглушка того же типа), импорт `astra-import.xml`,
задачи по отчёту, сборка, обратный экспорт. `app` — приложение на устройстве (R500 61 / Control Win V3),
`pool` — пул POU без устройства («Проверить все объекты»). Ошибки допускаются только в объектах с находкой
`todo` (1:1 через `trace.json`).

| Случай | Класс входа | IDE | Цель | Объектов | Ошибок импорта | Ошибок сборки | Вне `todo` | Предупр. |
|---|---|---|---|---:|---:|---:|---:|---:|
| boiler-plc210 | synthetic | Astra.IDE 1.7.2.2 | app (R500 61) | 13 | 0 | 6 | 0 | 1 |
| boiler-plc210 | synthetic | Astra.IDE 1.7.2.2 | pool | 13 | 0 | 6 | 0 | 0 |
| boiler-plc210 | synthetic | CODESYS 3.5.17.30 | app (Control Win) | 13 | 0 | 6 | 0 | 1 |
| boiler-plc210 | synthetic | CODESYS 3.5.17.30 | pool | 13 | 0 | 6 | 0 | 0 |
| lang-matrix | handmade → ide-roundtrip | Astra.IDE 1.7.2.2 | app | 7 | 0 | 0 | 0 | 0 |
| lang-matrix | handmade → ide-roundtrip | Astra.IDE 1.7.2.2 | pool | 7 | 0 | 0 | 0 | 0 |
| lang-matrix | handmade → ide-roundtrip | CODESYS 3.5.17.30 | app | 7 | 0 | 0 | 0 | 0 |
| lang-matrix | handmade → ide-roundtrip | CODESYS 3.5.17.30 | pool | 7 | 0 | 0 | 0 | 0 |
| s7-chain | ide-export (s7-to-codesys 1.0) | Astra.IDE 1.7.2.2 | app | 40 | 0 | 0 | 0 | 0 |
| s7-chain | ide-export | Astra.IDE 1.7.2.2 | pool | 40 | 0 | 0 | 0 | 0 |
| s7-chain | ide-export | CODESYS 3.5.17.30 | app | 40 | 0 | 0 | 0 | 0 |
| s7-chain | ide-export | CODESYS 3.5.17.30 | pool | 40 | 0 | 0 | 0 | 0 |
| sp18-speedtests | ide-export (SP18 Patch 2, MIT) | Astra.IDE 1.7.2.2 | app | 45 | 0 | 0 | 0 | 7 |
| sp18-speedtests | ide-export | Astra.IDE 1.7.2.2 | pool | 45 | 0 | 0 | 0 | 5 |
| sp18-speedtests | ide-export | CODESYS 3.5.17.30 | app | 45 | 0 | 0 | 0 | 7 |
| sp18-speedtests | ide-export | CODESYS 3.5.17.30 | pool | 45 | 0 | 0 | 0 | 5 |

- **boiler-plc210:** все 6 ошибок — в `PRG_Backup`: вызов `OPR.ON_OFF_HIST_REG`, у которого нет замены
  (находка C2A-LIB001 `todo`). Предупреждение `app` — C0100 о лицензионной библиотеке среды (CmpCodeMeter в
  Astra.IDE, CBML в CODESYS). Разбор — `docs/BUILD_ERRORS.md`, итерация 5.
- **lang-matrix:** шесть языков; IL пришёл переведённым в ST (IL не импортируется — P4), FBD/LD/CFC/SFC —
  как есть, с заменой `OSU.WORD_TO_HEX_STR` → `F_C2aWordToHexStr` в каждом языке.
- **sp18-speedtests:** библиотеки-плейсхолдера `#CAA Device Diagnosis` нет в репозиториях этих IDE — оракул
  собирает без неё (в коде она не вызывается). Предупреждения — из исходного кода образца (C0228, C0308,
  C0197), атрибуты SP18 у массивов переменной длины (C0351) и задача визуализации без POU (C0373).
- Дерево объектов после импорта совпадает с IR (`missing = 0` во всех прогонах).

Что оракулы **не** проверяют: поведение перенесённого кода (оракул эквивалентности не сделан —
`docs/ROADMAP.md`), работу на контроллере, порядок слов FLOAT32, RETAIN, Modbus на проводе
(`docs/HARDWARE_VALIDATION.md`).

## coUnit: AstraCompat

`python tools/codesys/cds.py test` (CODESYS 3.5.17.30, Control Win V3; рантайм, запущенный другим
процессом, не перезапускался — `CODESYS_RUNTIME_MAX_AGE_MIN`).

| Набор | Что проверяет |
|---|---|
| `FB_C2aStrings_Test` | `F_C2aWordToHexStr`, `F_C2aHexStrToWord`, `F_C2aBefore`, `F_C2aAfter`, `F_C2aAddChar`, `F_C2aConcat4` — примеры из документации ОВЕН и граничные случаи |
| `FB_C2aRealFormat_Test` | `F_C2aRealToStringFormat`: знак, округление половин, разделитель, число знаков |
| `FB_C2aTime_Test` | `F_C2aUnixToDate`, `F_C2aPad2`, разбор даты и времени `FB_C2aRtc` |
| `FB_C2aModbus_Test` | `F_C2aMbToReal`, `FB_C2aMbUnpack` в обоих порядках слов, границы массива, `F_C2aMx210Status` |
| `FB_C2aPid_Test` | `FB_C2aPid`: знак П-звена, ограничения выхода, ручной режим (многоцикловые тесты) |

Итог: 25 тестов, 25 пройдены. Двойники, AstraCompat и тесты написаны по одной документации ОВЕН —
совпадение с ПЛК210 не доказано (`docs/ASSUMPTIONS.md` A4).

## Модель трудоёмкости (часы — модель)

| Случай | Находок (авто / сверить / вручную / сведения) | P50, ч | P90, ч |
|---|---|---:|---:|
| boiler-plc210 | 2 / 26 / 4 / 5 | 19.84 | 23.49 |
| lang-matrix | 0 / 6 / 0 / 3 | 1.93 | 2.45 |
| sp18-speedtests | 0 / 36 / 0 / 5 | 4.45 | 4.81 |
| s7-chain | 0 / 0 / 0 / 66 | 0.37 | 0.41 |

Треугольные распределения по правилам, Монте-Карло 10 000 прогонов, seed 20261019, калибровка по
kns-port-domestic (`docs/ASSUMPTIONS.md` A11).

## Воспроизводимость

- Pyodide (Chromium) и CPython 3.12 на Windows дают один SHA-256 zip котельной: `fec7ae6d43f2d4e5…`.
- CI сравнивает zip котельной и SP18 между ubuntu и windows (джоб `repro`); результат — после первого
  прогона CI на GitHub.

## Как повторить

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check . && python -m ruff format --check . && python -m mypy
python -m pytest --cov=cds2astra --cov-branch --cov-report=json:build/coverage.json
python tools/check/coverage_gate.py build/coverage.json
python tools/assemble.py --tests && python tools/check/st_lint.py --strict
python tools/check/run_rusty.py --optional && python tools/check/run_iec_checker.py --tests
python tools/run_oracles.py                                  # нужны Astra.IDE 1.7.2.2 и CODESYS 3.5.17.30
python tools/codesys/cds.py test                             # coUnit в Control Win
python tools/web_bundle.py && (cd web && npm ci && npm run build) && python tools/e2e_smoke.py
```
