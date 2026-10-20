# Пробы go/no-go (A0)

Пробы — минимальные XML в `probe/` и образцы из `docs/SOURCES.md`, прогнанные скриптом без интерфейса в
двух средах: Astra.IDE 1.7.2.2 (профиль `Astra.IDE_V1.7.2.2`, устройство REGUL R500 61, devdesc
11.7.2.60) и CODESYS 3.5.17.30 (профиль «CODESYS V3.5 SP17 Patch 3», Control Win V3). Каждая проба — случай
оракула `tools/codesys/xml_oracle_ide.py`: новый проект (цель `app` — с устройством, `pool` — пул POU без
устройства), импорт, дерево объектов, задачи, сборка, обратный экспорт.

```
python tools/probes.py --ide astra codesys --lang-matrix      # 24 случая, ~1 мин
```

Последний прогон — 20.10.2026 (сырые итоги `build/probes/<ide>-probes-result.json` не коммитятся; строки —
в `probe/RESULTS.csv`). Обе среды дали одинаковый результат во всех случаях.

| № | Проба | Итог (обе IDE) | Что сделано в инструменте |
|---|---|---|---|
| P1 | образец niksosov (экспорт Astra.IDE V1.7.0.0, форма `resource`) | не импортируется: «Объект 'REGUL_R500_71_W' не принят родительским объектом или некорректен (например, отсутствует плагин или описание устройства)», затем «Импортируемых объектов не найдено» | вход `resource` читается парсером; выход — форма `pous` |
| P2 | форма `resource/addData` с несовпадающими именами configuration/resource, без устройства | не импортируется ни в `app`, ни в `pool`: «Объект 'CfgOther' не принят родительским объектом …» | `--form pous` по умолчанию, `resource` — только в `preserve`; профиль `import.form_default = pous` (`verified_local`) |
| P3 | создаёт ли импорт ссылки на библиотеки | POU импортируется и собирается, список Library Manager до и после импорта одинаков — ссылки не создаются | ссылки не пишутся; список — в отчёте и `IMPORT_STEPS.md`, оракул ставит их скриптом; `import.creates_library_refs = false` |
| P4 | IL: импорт `<IL>`, «Enable IL» из скрипта | «Unknown 'LD' element: 'xhtml'», «Не удалось создать объект 'PRG_P4'». У ScriptEngine нет API опций среды — IL скриптом не включить | IL → ST (`cds2astra/iltost.py`, C2A-LANG-IL), неподдержанное — `todo`; `import.il = false` |
| P5 | рукописные TC6 FBD/LD/SFC/CFC (`corpus/lang-matrix/source.handmade.xml`) | 7 объектов созданы (все языки, кроме IL); `app` — 0 ошибок; `pool` — 13 ошибок, все от отсутствующей во входе библиотеки ОВЕН `OSU` (вход ещё не перенесён); обратный экспорт есть | графика переносится как есть (`import.graphics = true`); обратные экспорты — `corpus/lang-matrix/export.{codesys,astra}.xml` |
| P6 | `TaskSettings` в проект с другими именами задач и ресурса | задачи приходят только в форме `resource`, а она не импортируется (P2); в `app` после импорта задач нет | таблица задач в `IMPORT_STEPS.md`, оракул создаёт задачи скриптом; `import.tasks = false` |
| P7 | OwenTargets-3.5.17.36 и Mx210Templates в CODESYS 3.5.17.30 | не выполнялась (нужен UAC для установки devdesc) | слой ОВЕН котельной — `synthetic` (`docs/ASSUMPTIONS.md` A1) |
| P8 | ООП: фикстура kns `constructs` @ `6262d0f` | 58 объектов (интерфейсы, методы, свойства, наследование), 0 ошибок в `app` и 0 в `pool` («Проверить все объекты») | флаги `oop.*` = `verified_local`; находки LANG-OOP — `info` |
| P9 | coUnit на проекте после импорта XML в 3.5.17.30 | не выполнялась отдельно; AstraCompat проходит coUnit в своём проекте (25/25) | поведение перенесённого кода — см. ROADMAP (оракул эквивалентности) |
| E6 | `regul-devices.xml`: ЦП R500 61 с коннекторами | импорт в Astra.IDE 1.7.2.2 без ошибок, в дереве `Device → Plc Logic → Application`; без коннекторов — «Значение не может быть неопределенным. Имя параметра: array» | `regul-devices.xml` пишет только ЦП, модули Modbus — комментарием |

## Как повторить

1. Astra.IDE 1.7.2.2 и CODESYS 3.5.17.30 установлены в каталоги по умолчанию (пути — в
   `tools/codesys/cdshost/ide_env.py`, переменные `ASTRA_IDE_EXE`, `ASTRA_IDE_PROFILE`, `CODESYS_317_EXE`, `CODESYS_317_PROFILE`).
2. Для P1 и P8 нужны образцы: `python tools/fetch_samples.py niksosov` и
   `python tools/fetch_samples.py --kns <рабочая копия kns-port-domestic>`.
3. `python tools/probes.py --ide astra codesys --lang-matrix`. Среда не открывает окон; параллельные
   прогоны других проектов ждут на блокировках `cds.py`.

Пробы владельца (E5, E7, E8) — `docs/OWNER_EXPERIMENTS.md`, пакет — `cds2astra probe --out <каталог>`.
