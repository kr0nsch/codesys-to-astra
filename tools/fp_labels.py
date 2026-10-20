#!/usr/bin/env python3
"""Разметка TP/FP находок на наборе niksosov, SRCI, sp18, s7-chain -> docs/FP_LABELS.md.

Каждая находка получает метку и причину по правилу разметки (case, rule): правило написано по ручному разбору
находок этого набора; находка, для которой правила нет, получает «?» и проваливает прогон — значит, разметку
надо дописать. niksosov берётся из кэша `tools/fetch_samples.py niksosov` (в репозиторий не кладётся).

    python tools/fp_labels.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cds2astra import api  # noqa: E402
from cds2astra.session import Options  # noqa: E402

OUT = REPO / "docs" / "FP_LABELS.md"
# цель образца niksosov — из его проекта: R500 71-W, резервирование, MAIN_TASK синхронизируемая
NIKSOSOV_SPEC = (
    'cpu = "REGUL R500 71-W"\ncpu_type = "I"\nbus = "RegulBus OS"\nredundancy = true\nsync_task = "MAIN_TASK"\n'
)

LABELS: dict[tuple[str, str], tuple[str, str]] = {
    ("niksosov", "C2A-FMT001"): ("TP", "в экспорте нет interfaceasplaintext — проверено по файлу"),
    ("niksosov", "C2A-LANG-GRAPH"): ("TP", "тела CFC переносятся как есть; оракул P1 импортирует их без ошибок"),
    ("niksosov", "C2A-TASK001"): ("TP", "info: приоритеты уже допустимы для цели с резервированием — без изменений"),
    ("niksosov", "C2A-RED001"): (
        "TP",
        "info: напоминание о лимите синхронизируемых данных при резервировании; объём — грубая оценка по типам",
    ),
    ("sp18", "C2A-FMT001"): ("TP", "в экспорте нет interfaceasplaintext — проверено по файлу"),
    ("sp18", "C2A-LANG-GRAPH"): ("TP", "LD/FBD/CFC как есть; оракул sp18-speedtests собирает их в обеих IDE"),
    ("sp18", "C2A-TASK001"): (
        "TP",
        "приоритет 1 на REGUL — уровень синхронизируемой задачи резервирования, 16 и 31 выше максимума 15 "
        "(профиль tasks.*, руководство Astra.IDE с. 46)",
    ),
    ("sp18", "C2A-LIB002"): ("TP", "MemoryUtils в коде не вызывается; оракул собирает проект без неё, 0 ошибок"),
    ("s7-chain", "C2A-RET001"): ("TP", "4 переменные RETAIN во входе; поведение RETAIN на REGUL отличается"),
    ("s7-chain", "C2A-MARK"): ("TP", "маркер s7conv действительно стоит во входе (строка указана)"),
    ("s7-chain", "C2A-IO001"): ("TP", "AT %M во входе; память %M на REGUL есть — исход info верен"),
}


def runs() -> list[tuple[str, list[dict[str, Any]], str]]:
    opts = Options(source_date="1970-01-01T00:00:00")
    out: list[tuple[str, list[dict[str, Any]], str]] = []
    niks = REPO / ".cache" / "niksosov" / "AstraRegul_stand.xml"
    if not niks.is_file():
        raise SystemExit("нет .cache/niksosov: python tools/fetch_samples.py niksosov")
    res = api.run(niks.read_bytes(), niks.name, spec_text=NIKSOSOV_SPEC, options=opts)
    out.append(("niksosov", res.report["findings"], "AstraRegul_stand.xml @ 851ac49, цель R500 71-W с резервированием"))
    srci = REPO / "corpus" / "srci" / "RobotLibrarySysDep_3S.xml"
    res = api.run(srci.read_bytes(), srci.name, options=opts)
    out.append(("srci", res.report["findings"], "RobotLibrarySysDep_3S.xml @ 67fd773, цель по умолчанию"))
    sp18 = REPO / "corpus" / "sp18-speedtests" / "codesys_code_execution_speedTests.xml"
    res = api.run(sp18.read_bytes(), sp18.name, options=opts)
    out.append(("sp18", res.report["findings"], "codesys_code_execution_speedTests.xml @ d3abcf4, цель по умолчанию"))
    corpus = REPO / "corpus" / "s7-chain"
    s7 = {p.relative_to(corpus).as_posix(): p.read_text(encoding="utf-8") for p in sorted(corpus.rglob("*.st"))}
    res = api.run(api.layout_to_xml(s7, "s7-chain"), "s7-chain.xml", options=opts)
    out.append(("s7-chain", res.report["findings"], "выход s7-to-codesys 1.0 @ 2285760, цель по умолчанию"))
    return out


def render() -> tuple[str, int]:
    data = runs()
    total = sum(len(f) for _c, f, _d in data)
    unlabeled = 0
    counts: Counter[tuple[str, str]] = Counter()
    lines = [
        "# Разметка находок TP/FP",
        "",
        "Файл пишет `python tools/fp_labels.py` (руками не правится). Набор — niksosov, SRCI, sp18, s7-chain (ТЗ §8).",
        "Метка ставится по правилу разметки «образец + правило» из `tools/fp_labels.py`; правило — итог ручного",
        "разбора всех находок этого правила на образце. Находка без правила разметки валит прогон.",
        "",
        "## Итог",
        "",
        "| Образец | Вход | Находок | TP | FP |",
        "|---|---|---:|---:|---:|",
    ]
    detail: list[str] = []
    fp_total = 0
    for case, findings, desc in data:
        tp = fp = 0
        detail += [f"## {case}", "", f"{desc}. Находок: {len(findings)}.", ""]
        if findings:
            detail += ["| Правило | Исход | Объект:строка | Сообщение | Метка | Причина |", "|---|---|---|---|---|---|"]
        for f in findings:
            label, why = LABELS.get((case, f["rule"]), ("?", "нет правила разметки"))
            if label == "?":
                unlabeled += 1
            tp += label == "TP"
            fp += label == "FP"
            counts[(f["rule"], label)] += 1
            o = f["origin"]
            where = f"{o.get('object', '') or '—'}:{o.get('line', '') or '—'}"
            msg = f["message"].replace("|", "\\|")
            if len(msg) > 110:
                msg = msg[:107] + "…"
            detail.append(f"| {f['rule']} | {f['outcome']} | {where} | {msg} | {label} | {why} |")
        detail.append("")
        fp_total += fp
        lines.append(f"| {case} | {desc} | {len(findings)} | {tp} | {fp} |")
    share = 100.0 * fp_total / total if total else 0.0
    lines += [
        f"| **всего** | | **{total}** | **{total - fp_total - unlabeled}** | **{fp_total}** |",
        "",
        f"Доля FP: {fp_total} из {total} = {share:.1f} % (порог ТЗ — не больше 5 %; находок не меньше 30, порог "
        "применяется)."
        if total >= 30
        else f"Находок {total} < 30 — порог не применяется, приведена таблица.",
        "",
        "Чего разметка не показывает: пропуски (FN). SRCI даёт 0 находок — это библиотека без задач, устройств, "
        "AT и вызовов ОВЕН; полноту правил проверяет корпус pos/neg `cds2astra/tests/corpus/` (52 случая).",
        "niksosov размечен со своей целью (R500 71-W, резервирование, MAIN_TASK синхронизируемая). С целью по "
        "умолчанию (R500 61 без резервирования) C2A-TASK001 даёт 2 находки check: MAIN_TASK 1 -> 2 и TASK_DIAGN "
        "10 -> 3 — для такой цели они верны, но к образцу не относятся.",
        "",
        "## По правилам",
        "",
        "| Правило | Метка | Находок |",
        "|---|---|---:|",
    ]
    lines += [f"| {r} | {lbl} | {n} |" for (r, lbl), n in sorted(counts.items())]
    lines += ["", *detail]
    return "\n".join(lines).rstrip() + "\n", unlabeled


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="разметка TP/FP -> docs/FP_LABELS.md")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text, unlabeled = render()
    if args.check:
        same = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("FP_LABELS.md актуален" if same else "FP_LABELS.md устарел: python tools/fp_labels.py")
        return 0 if same and not unlabeled else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"docs/FP_LABELS.md: без разметки {unlabeled}")
    return 1 if unlabeled else 0


if __name__ == "__main__":
    sys.exit(main())
