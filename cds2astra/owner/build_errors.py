"""Цикл исправления (M10): сообщения Astra.IDE / CODESYS -> объект, позиция, правило -> предложение правки.

Строки — как копирует окно «Сообщения» или пишут журналы cds.py (русский и английский интерфейс):

    Error       C0077 Неизвестный тип: 'X' [Regul.PRG_Main, Строка 23 (Объявл.)]
    Error C0046 Identifier 'F_X' not defined [PRG_Main, Line 4, Column 1 (Impl)]
    Warning     C0100 Библиотека CmpCodeMeter не добавлена … [Library Manager]
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_MSG_RE = re.compile(
    r"^\s*(?P<sev>Error|Warning|FatalError|Information|Ошибка|Предупреждение|Сообщение)\s+"
    r"(?:(?P<code>[CW]\d{4})\s+)?(?P<text>.*?)\s*(?:\[(?P<where>[^\]]*)\])?\s*$"
)
_POS_RE = re.compile(
    r"(?:Строка|Line)\s+(?P<line>\d+)(?:,\s*(?:Столбец|Column)\s+(?P<col>\d+))?\s*(?:\((?P<part>[^)]*)\))?",
    re.IGNORECASE,
)
SEVERITY = {"ошибка": "Error", "предупреждение": "Warning", "сообщение": "Information"}
HINTS = {
    "C0077": "неизвестный тип: проверьте ссылку на библиотеку (AstraCompat, драйвер РегЛаб) и замену в таблице",
    "C0046": "идентификатор не задан: POU вендорной библиотеки без замены (C2A-LIB001) или ссылка не добавлена",
    "C0035": "вызов не POU: следствие неизвестного типа или идентификатора выше",
    "C0032": "преобразование типов: следствие неизвестного типа или разница сигнатур обёртки",
    "C0041": "VAR_IN_OUT требует переменную: сверьте сигнатуру функции библиотеки цели",
    "C0100": "лицензия CmpCodeMeter: вторичное сообщение (kns BUILD_ERRORS 1.9), правки обычно не требует",
}


@dataclass
class Message:
    severity: str
    code: str | None
    text: str
    object: str | None
    position: str | None
    line: int | None
    column: int | None
    part: str | None  # impl | decl | None


def parse(text: str) -> list[Message]:
    out: list[Message] = []
    for raw in text.splitlines():
        m = _MSG_RE.match(raw)
        if not m or not m.group("text"):
            continue
        sev = m.group("sev")
        sev = SEVERITY.get(sev.lower(), sev)
        where = m.group("where") or ""
        obj = None
        pos = None
        line = col = None
        part = None
        if where:
            obj, _, pos = where.partition(",")
            obj = obj.strip()
            pos = pos.strip() or None
            if obj.lower().startswith("regul."):
                obj = obj.split(".", 1)[1]
            pm = _POS_RE.search(pos or "")
            if pm:
                line = int(pm.group("line"))
                col = int(pm.group("col")) if pm.group("col") else None
                p = (pm.group("part") or "").lower()
                part = (
                    "impl"
                    if p.startswith(("реализ", "impl"))
                    else ("decl" if p.startswith(("объявл", "decl")) else None)
                )
        out.append(Message(sev, m.group("code"), m.group("text"), obj, pos, line, col, part))
    return out


def suggest(messages: list[Message], trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Сообщение -> объект трассы, находки и правило -> предложение правки."""
    by_obj: dict[str, dict[str, Any]] = {}
    if trace:
        for o in trace.get("objects", []):
            by_obj[str(o["target"]).lower()] = o
    rows = []
    for msg in messages:
        row = asdict(msg)
        top = (msg.object or "").split(".")[0].lower()
        entry = by_obj.get(top)
        rules = sorted({f["rule"] for f in entry.get("findings", [])}) if entry else []
        todo = [f for f in (entry or {}).get("findings", []) if f.get("outcome") in ("todo", "impossible")]
        hint = HINTS.get(msg.code or "", "сверьте текст сообщения с находками отчёта")
        if todo:
            suggestion = f"ожидаемо: в объекте находки todo ({', '.join(sorted({f['rule'] for f in todo}))}) — реализовать вручную"
        elif entry and entry.get("generated"):
            suggestion = f"объект создан cds2astra ({', '.join(rules) or 'IO'}): {hint}"
        elif entry:
            suggestion = f"правила объекта: {', '.join(rules) or 'нет находок'}; {hint}"
        else:
            suggestion = hint
        row["rules"] = rules
        row["suggestion"] = suggestion
        row["source_object"] = entry.get("source") if entry else None
        rows.append(row)
    return rows


_ITER_RE = re.compile(r"^###\s+Итерация\s+(\d+)", re.MULTILINE)
_STATUS_RE = re.compile(
    r"\|\s*([0-9.–-]+)\s*\|[^\n]*\|\s*(открыто|исправлено[^|]*|ручной шаг|особенность среды|принято[^|]*)\s*\|"
)


def status(text: str) -> dict[str, Any]:
    """BUILD_ERRORS.md -> число итераций и записей по статусам."""
    iters = [int(x) for x in _ITER_RE.findall(text)]
    counts: dict[str, int] = {}
    for _num, st in _STATUS_RE.findall(text):
        key = st.split(" ")[0]
        counts[key] = counts.get(key, 0) + 1
    return {
        "iterations": len(iters),
        "last": max(iters) if iters else 0,
        "statuses": counts,
        "open": counts.get("открыто", 0),
    }
