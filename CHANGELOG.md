# Changelog

Все заметные изменения проекта записываются в этот файл.

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии — по
[Semantic Versioning](https://semver.org/lang/ru/spec/v2.0.0.html).

## [0.1.0] — 2026-10-20

Первый выпуск.

### Added

- Импорт PLCopen XML CODESYS 3.5 (TC6 0200/0201, addData 3S): размещения `types`, `resource`, `application`
  (TwinCAT — распознавание), шесть языков, действия, переходы, методы, свойства, интерфейсы, GVL, DUT,
  задачи с `TaskSettings`, библиотеки, дерево устройств и привязки; ловушка CFC; отказ DOCTYPE и сущностей.
  Вход также из ST-раскладки `src/`.
- Промежуточное представление и лексер ST без потерь; правки — байтами исходного XML (режим `preserve`
  без правил побайтно равен входу).
- Профили: Astra.IDE 1.7.2.2 / REGUL R500 (устройства 11.7.2.60), источники ОВЕН ПЛК2xx SP17 и CODESYS
  SP18–SP21; статус, источник и дата у каждого значения; `probe` сверяет профиль с установленной IDE и собирает пакет проб владельца.
- 26 правил C2A-* (+ C2A-EDIT): ввод-вывод (AT, узлы таргета ОВЕН, каналы Mx210 → Modbus TCP REGUL,
  достоверность), Modbus 3S, приоритеты задач, библиотеки, символьная конфигурация, резервирование, RETAIN,
  указатели, исключения, языки (IL → ST, SFC, графика, ООП), понижение SP18–SP21, маркеры s7conv.
- Таблица замен библиотек ОВЕН (`map`/`wrap`/`stub`/`none`) со ссылками на страницы документации.
- AstraCompat 0.1.0.0 — библиотека ST: строковые функции OwenStringUtils, `FB_C2aPid` (обёртка `STD_PID`
  на Util), `FB_C2aRtc` (OwenRTC на SysTimeRtc), распаковка регистров Modbus, коды ошибок МВ210;
  25 тестов coUnit. Заглушка типа `ChannelStatus` драйвера Modbus для сборки в CODESYS.
- Выход: `astra-import.xml` (форма `pous`), `trace.json`, `MIGRATION_REPORT.{json,md,html}` по схеме
  семейства, `IMPORT_STEPS.md`, `io-map.{csv,md}`, `regul-devices.xml`; детерминированный `--zip`.
- Модель трудоёмкости P50/P90 (Монте-Карло, калибровка по kns-port-domestic).
- CLI: `inventory`, `analyze`, `migrate`, `downgrade`, `explain`, `profiles`, `probe`, `build-errors`.
- Оракулы импорта и сборки в Astra.IDE 1.7.2.2 и CODESYS 3.5.17.30 (цели `app` и `pool`), пробы P1–P8 и
  E6; корпус: котельная (синтетика), матрица языков, SP18 (MIT), цепочка S7 → REGUL.
- Веб-демо на Pyodide (тот же пакет в браузере), e2e на Playwright, GitHub Pages.
- CI: ruff, mypy, pytest с порогом покрытия на ubuntu и windows (Python 3.12 и 3.14), ST-линтер,
  iec_checker, RuSTy, сравнение SHA-256 zip между ОС.

[0.1.0]: https://github.com/kr0nsch/codesys-to-astra/releases/tag/v0.1.0
