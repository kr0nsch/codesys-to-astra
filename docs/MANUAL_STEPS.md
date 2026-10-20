# Ручные шаги

Что нужно на машине разработчика, чтобы гонять то, чего нет в CI: сборку и тесты AstraCompat, установку
библиотек в обе IDE, оракулы импорта. Всё остальное (конвертер, линтеры, статанализ, RuSTy, веб) — в
README и `ci.yml`. Команды IDE выполняет `tools/codesys/cds.py` (подробно — `tools/README.md`), в
нужной IDE — `tools/codesys/cds_ide.py astra|codesys <команда>`.

## 1. Установка

1. CODESYS V3.5 SP17 Patch 3 (3.5.17.30) с компонентом CODESYS Control Win V3.
2. Astra.IDE 1.7.2.2 с пакетом REGUL (устройства 11.7.2.60) — с сайта РегЛаб.
3. coUnit (CfUnit) 1.2.0.0 в репозитории библиотек CODESYS; если её нет, `cds.py` поставит её из файла
   `COUNIT_LIBRARY`.
4. Пути по умолчанию заданы в `tools/codesys/cdshost/ide_env.py`; другие — переменными `ASTRA_IDE_EXE`,
   `ASTRA_IDE_PROFILE`, `CODESYS_317_EXE`, `CODESYS_317_PROFILE`.

## 2. AstraCompat в CODESYS 3.5.17.30

```bat
python tools\codesys\cds.py check --tests       :: все объекты src/ и tests/ (пул POU без устройства)
python tools\codesys\cds.py test                :: тестовый проект, Control Win, coUnit
python tools\codesys\cds.py library --install   :: build\AstraCompat.library -> репозиторий CODESYS
```

Заглушка драйвера Modbus для сборки в CODESYS (тип `ChannelStatus`, только сборка):

```bat
set CDS_REPO_ROOT=stubs\ps\C2aStub_PsIoDrvModbusTcpMaster_OS
set CDS_CONFIG=stubs\ps\C2aStub_PsIoDrvModbusTcpMaster_OS\config.json
python tools\codesys\cds.py library --install
```

Заглушку в Astra.IDE не ставят: там есть настоящий драйвер.

## 3. AstraCompat в Astra.IDE 1.7.2.2

```bat
python tools\codesys\cds_ide.py astra check
python tools\codesys\cds_ide.py astra library --install
```

У Astra.IDE свой репозиторий библиотек (`C:\ProgramData\Astra.IDE_64_1.7.2.2\Managed Libraries`), свой
учёт установок (`%LOCALAPPDATA%\plc-tools\astra-libraries.json`) и своя блокировка
(`astra-library-repo.lock`) — установки CODESYS и Astra.IDE не мешают друг другу. coUnit в Astra.IDE не
гоняется (`docs/ROADMAP.md`).

## 4. Рантайм Control Win

`cds.py test` работает с пользовательским процессом CODESYS Control Win V3 (без прав администратора):
`python tools/codesys/cds.py runtime init` один раз, дальше рантайм запускается сам. Учётные данные входа
в рантайм — файл `CODESYS_RUNTIME_CREDENTIALS` (по умолчанию `credentials.json` в каталоге рантайма, ключи
`user`, `password`). Без лицензии Control Win работает 2 часа; `cds.py test` перезапускает рантайм старше
`CODESYS_RUNTIME_MAX_AGE_MIN` минут (100). Рантайм, запущенный другим процессом, не трогайте: задайте
большое `CODESYS_RUNTIME_MAX_AGE_MIN`, а прогоны разведёт блокировка `codesys-runtime.lock`.

## 5. Оракулы импорта и сборки

```bat
python tools\run_oracles.py                     :: корпус -> migrate -> обе IDE, app и pool -> docs\oracle-results.json
python tools\codesys\xml_oracle.py out\boiler\astra-import.xml --ide astra --target app pool
python tools\probes.py --ide astra codesys --lang-matrix
```

AstraCompat и заглушка должны быть установлены (разделы 2–3). Сообщения — `build/oracle/*.json`, разбор —
`docs/BUILD_ERRORS.md`.

## 6. Что делается только в интерфейсе IDE

- «Enable IL» (Инструменты → Опции): из скрипта не включается (P4). Пока выключено, IL переводится в ST.
- Выгрузки форматов Astra.IDE (E5), визуализация (E7), ВПЛК (E8) — `docs/OWNER_EXPERIMENTS.md`.
- Перенос своего проекта: шаги `IMPORT_STEPS.md` из выхода `cds2astra migrate`.

## 7. Недостающие библиотеки

Сообщение «нет библиотек в репозиториях CODESYS: …» значит, что ссылки из `tools/codesys/config.json`
(или из списка библиотек оракула) нет в репозитории IDE. Варианты:

1. Плейсхолдер (`#Standard`, `#Util`, `#SysTimeRtc`) — библиотека ставится с IDE; проверьте профиль IDE.
2. Своя библиотека (AstraCompat, заглушка) — `cds.py library --install` в нужной IDE (разделы 2–3).
3. Файл `.library` — путь в `libraries.<ключ>.install_from` (`config.json`) или в переменной, которую
   этот ключ называет (например, `COUNIT_LIBRARY`); `cds.py deps` поставит его сам.
4. Плейсхолдер, которого нет в среде (например, `#CAA Device Diagnosis` образца SP18), — оракул собирает
   без него и пишет его в `libraries_missing`; если код его вызывает, это видно по ошибкам сборки.
