# Правила разработки

## Контекст

- Репозиторий — часть открытого портфолио инженера АСУ ТП (kr0nsch, github.com/kr0nsch), серия
  «Миграция ПЛК-проектов». Честность важнее объёма: в README и docs — только то, что проверено, с датой и
  версией среды.
- Источник: CODESYS 3.5 SP17 Patch 3 (ОВЕН ПЛК2xx) и SP18–SP21 других вендоров. Цель: Astra.IDE 1.7.2.x
  (OEM CODESYS 3.5.17), REGUL R500/R400/R050.
- Инструмент неофициальный. Проект не связан с компаниями ОВЕН, Прософт-Системы, РегЛаб и CODESYS GmbH;
  названия продуктов — товарные знаки их владельцев.

## Язык и оформление

- Идентификаторы — ASCII, по-английски. Комментарии, docstring и документация — по-русски.
- UTF-8 без BOM, LF (`.gitattributes`); экспорты IDE в `corpus/lang-matrix/export.*.xml` хранятся байт в байт.
- Python 3.12, ядро `cds2astra/` — только стандартная библиотека (работает в Pyodide). `ruff`, `ruff format`,
  `mypy --strict`, pytest; покрытие `cds2astra/` — строки ≥ 85 %, ветви ≥ 75 %.
- ST — по раскладке `docs/LAYOUT.md`, префиксы `PRG_/FB_/F_/ST_/E_/U_/GVL_`, объекты AstraCompat — с `C2a`,
  венгерские префиксы переменных, единицы в именах, заголовок POU (назначение, автор, версия, документ).

## Данные о продуктах вендоров

- Нет источника — нет строки. У каждой сигнатуры POU ОВЕН, регистра модуля, значения профиля — URL и
  страница (`docs/SOURCES.md`), у профиля — статус (`documented`, `observed_in_sample`, `verified_local`,
  `owner_verified`, `unknown`) и дата.
- PDF, пакеты, devdesc, библиотеки вендоров и чужие экспорты не коммитятся: только ссылки и SHA-256.
  Образцы без лицензии — в кэш `.cache/` через `tools/fetch_samples.py`; под MIT — в `corpus/` с LICENSE.
- `.compiled-library` и DLL не декомпилируются. Библиотеки с именем или компанией вендора в IDE не ставятся
  (заглушки — `C2aStub_*`, компания `plc-portfolio`).

## Как добавить правило

1. Строка в `cds2astra/rules/registry.py`: id `C2A-…`, объяснение, источник, возможные исходы, автоправка.
2. Детектор и правка в `cds2astra/rules/` через `Session` (правки байтов, маркер `// C2A-…`).
3. Случаи `pos` и `neg` — генератор `tools/corpus/make_rule_corpus.py`, затем `--check`.
4. `python tools/gen_docs.py` (обновит `docs/RULES.md`, `docs/LIBMAP.md`), минуты — в `data/effort.toml`.
5. Если правило меняет выход — прогон оракулов (`tools/run_oracles.py`) и запись в `docs/BUILD_ERRORS.md`.

## Как добавить замену библиотеки

Строка в `cds2astra/data/libmap/<библиотека>.toml`: `map` (переименование), `wrap` (обёртка AstraCompat с
теми же пинами), `stub` или `none`; `source_url` со страницей. Сигнатуру — в `data/owen_signatures.toml`
(страница, SHA-256 документа). Для `wrap` — функция или ФБ в `src/` и тесты coUnit в `tests/`.

## Проверки перед коммитом

```bash
python -m ruff check . && python -m ruff format --check . && python -m mypy && python -m pytest
python tools/assemble.py --tests && python tools/check/st_lint.py --strict
python tools/corpus/make_rule_corpus.py --check && python tools/gen_docs.py --check
```

С IDE на машине — `tools/run_oracles.py` и `tools/codesys/cds.py test` (`docs/MANUAL_STEPS.md`).

## Git

- Conventional Commits по-русски (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`), небольшие осмысленные
  коммиты, без служебных трейлеров.
- В `main` — только зелёные проверки.

## Медиа

Картинки README — только из `tools/media/make_media.py` (фирменный медиа-кит портфолио, путь — переменная
`MEDIA_KIT`). GIF терминала — реальная сессия (`term2gif.py capture`), скриншоты — реальное веб-демо.
`docs/media/social-preview.png` загружается вручную: Settings → General → Social preview.
