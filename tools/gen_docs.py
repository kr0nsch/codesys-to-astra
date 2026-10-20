#!/usr/bin/env python3
"""Документы из данных пакета: docs/RULES.md (реестр правил) и docs/LIBMAP.md (таблица замен).

python tools/gen_docs.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cds2astra import libmap  # noqa: E402
from cds2astra.rules import RULES  # noqa: E402

OUTCOME_RU = {"auto": "авто", "check": "сверить", "todo": "вручную", "impossible": "невозможно", "info": "сведения"}


def rules_md() -> str:
    lines = [
        "# Правила переноса C2A-*",
        "",
        "Документ собирается из реестра `cds2astra/rules/registry.py` (`python tools/gen_docs.py`); у каждого правила",
        "есть корпус pos/neg в `cds2astra/tests/corpus/<ID>/` (кроме `C2A-EDIT` — сторожа пересекающихся правок).",
        "Исходы: **авто** (`auto`) — правка без смены семантики; **сверить** (`check`) — правка сделана, поведение",
        "сверить (маркер `// MIGRATION-CHECK(ID)`); **вручную** (`todo`) — аналога нет (маркер `// MIGRATION-TODO(ID)`,",
        "код не удаляется); **сведения** (`info`). Подробно — `cds2astra explain <ID>`.",
        "",
        "| ID | Что | Исходы |",
        "|---|---|---|",
    ]
    for rid, r in RULES.items():
        lines.append(f"| `{rid}` | {r.title} | {', '.join(OUTCOME_RU[o] for o in r.outcomes)} |")
    for rid, r in RULES.items():
        lines += [
            "",
            f"## {rid} — {r.title}",
            "",
            r.explanation,
            "",
            f"- Исходы: {', '.join(OUTCOME_RU[o] + f' (`{o}`)' for o in r.outcomes)}.",
            f"- Автоправка: {r.autofix}.",
            f"- Источник: {r.source}.",
            f"- Язык находки по умолчанию: {r.language}.",
        ]
    return "\n".join(lines) + "\n"


def libmap_md() -> str:
    lm = libmap.load()
    lines = [
        "# Таблица замен библиотек ОВЕН",
        "",
        "Собирается из `cds2astra/data/libmap/*.toml` (`python tools/gen_docs.py`). Вид: `map` — другое имя, та же",
        "семантика (авто); `wrap` — обёртка AstraCompat с теми же пинами (сверить); `stub`/`none` — аналога нет",
        "(вручную). Сигнатуры POU ОВЕН — `cds2astra/data/owen_signatures.toml` (документ, версия, страница, SHA-256",
        "PDF); тест сверяет пины обёрток AstraCompat с ними.",
        "",
        "| Библиотека | POU ОВЕН | Вид | Замена | Документ | Уверенность | Примечание |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in lm.entries:
        lines.append(
            f"| {e.library} | `{e.source}` | {e.kind} | {('`' + e.target + '`') if e.target else '—'} | "
            f"[документ]({e.source_url}) | {e.confidence} | {e.note.replace('|', '/')} |"
        )
    lines += [
        "",
        "Узлы таргета ПЛК2xx (OwenRTC, Watchdog, LeftSide…) и модули Mx210 — `cds2astra/data/owen_modules.toml`,",
        "правила C2A-IO002 и C2A-IO003 ([RULES.md](RULES.md)).",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="docs/RULES.md и docs/LIBMAP.md из данных пакета")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    docs = {REPO / "docs" / "RULES.md": rules_md(), REPO / "docs" / "LIBMAP.md": libmap_md()}
    bad = []
    for path, text in docs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                bad.append(path.name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if args.check:
        print("docs: совпадают" if not bad else f"docs устарели: {', '.join(bad)}")
        return 1 if bad else 0
    print("docs: RULES.md, LIBMAP.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
