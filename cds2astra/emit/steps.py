"""IMPORT_STEPS.md под проект: шаги в исходной IDE и в Astra.IDE с ожидаемым результатом и минутами."""

from __future__ import annotations

from typing import Any

from .. import TOOL_NAME, __version__
from ..session import Session


def build(s: Session, report: dict[str, Any]) -> str:
    p = s.project
    sp18 = any(f.rule.startswith("C2A-SP") for f in s.findings)
    libs = s.libraries_out
    lines = [
        "# Шаги импорта в Astra.IDE",
        "",
        f"Создано {TOOL_NAME} {__version__} для `{p.file.replace(chr(92), '/').rsplit('/', 1)[-1]}`. У каждого шага — "
        "ожидаемый результат и минуты (оценка, не замер).",
        "",
        "## В исходной IDE (CODESYS)",
        "",
        "1. Экспорт PLCopenXML с флагом «экспортировать объявления как простой текст» (Проект → Экспорт PLCopenXML). "
        "Ожидается: в XML есть `interfaceasplaintext`. 5 мин."
        + (" В этом входе текстов объявлений нет — переэкспортируйте (C2A-FMT001)." if not p.has_plaintext else ""),
    ]
    if sp18:
        lines.append(
            "2. Проект SP18+: «Проект → Настройки проекта → Параметры компиляции → фиксированная версия 3.5.17.x», "
            "затем «Файл → Сохранить проект как…» в формате SP17 (конспект §7.3). Ожидается: новые конструкции "
            "становятся ошибками компиляции. 30 мин."
        )
    lines += [
        "",
        "## В Astra.IDE 1.7.2.2",
        "",
        "1. «Инструменты → Опции → FBD, LD и IL»: опция «Включить IL» — только если в проекте остался IL "
        "(инструмент переводит IL в ST: импорт `<IL>` не работает — проба P4). 2 мин.",
        f"2. Новый проект мастером конфигурации Regul: {s.spec.cpu}, шина {s.spec.bus}"
        + (", резервирование" if s.spec.redundancy else "")
        + ". Ожидается: дерево устройств ЦП и крейта. 10 мин.",
        "3. Библиотеки (импорт PLCopenXML ссылок не создаёт — проба P3), «Менеджер библиотек → Добавить»:",
    ]
    for lib in libs:
        ns = f", пространство имён `{lib['namespace']}`" if lib.get("namespace") else ""
        lines.append(f"   - `{lib['name']}`{ns} — {lib.get('why', '')}")
    lines += [
        "   Ожидается: ссылки без жёлтых треугольников. 10 мин.",
        "4. «Проект → Импорт PLCopenXML…», файл `astra-import.xml`, цель — Application. Ожидается: объекты из "
        f"таблицы ниже ({len(report['objects'])} шт.), без сообщений об ошибках импорта. 5 мин.",
        "5. Устройства: Modbus TCP Master OS и Outer Slave OS на каждый модуль, каналы и привязки — по `io-map.md` "
        "(формат CSV привязок Astra.IDE не опубликован — эксперимент E5). 10 мин на модуль.",
        "6. Задачи (импорт задач не переносит — проба P6) — таблица ниже. `PRG_C2aIoUpdate` вызывать первым в "
        "задаче, где опрашивался ввод-вывод. 10 мин.",
        "7. «Сборка → Очистить всё», «Сборка → Генерировать код». Сообщения — в `docs/BUILD_ERRORS.md` своего проекта, "
        "разбор — `cds2astra build-errors parse`. Ожидается: ошибки только в объектах с находками todo. 15 мин.",
        "",
        "## Задачи",
        "",
    ]
    if s.task_table:
        lines.append("| задача | тип | интервал, мс | приоритет (было → стало) | POU |")
        lines.append("|---|---|---|---|---|")
        for t in s.task_table:
            pous = ", ".join(t.get("pous") or [])
            lines.append(
                f"| {t['task']} | {t.get('kind', '')} | {t.get('interval_ms', '')} | {t['before']} → {t['after']} | {pous} |"
            )
    else:
        lines.append("Во входе задач нет: создайте задачу по примеру исходного проекта.")
    lines += ["", "## Объекты импорта", "", "| объект | вид | откуда |", "|---|---|---|"]
    for o in report["objects"]:
        lines.append(f"| {o['name']} | {o['kind']} | {o['source']} |")
    todo = [f for f in s.findings if f.outcome in ("todo", "impossible")]
    if todo:
        lines += ["", "## Вручную (todo)", ""]
        for f in sorted(todo, key=lambda x: x.sort_key):
            lines.append(f"- `{f.rule}` {f.pou or ''}: {f.message}")
    lines += [
        "",
        "Компиляция в Astra.IDE подтверждает импорт и сборку, но не работу на контроллере REGUL: драйверы, "
        "RegulBus, RETAIN и порядок слов FLOAT32 проверяются на железе (docs/HARDWARE_VALIDATION.md).",
        "",
    ]
    return "\n".join(lines)
