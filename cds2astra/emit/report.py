"""MIGRATION_REPORT.{json,md,html}: ядро семейства (schemas/report-core.schema.json) + расширения проекта."""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from typing import Any

from .. import TOOL_NAME, __version__
from ..estimate import Effort, minutes_for, table
from ..findings import FAMILY, OUTCOMES, Finding
from ..session import Session

LANG_ORDER = ("ST", "IL", "LD", "FBD", "CFC", "SFC", "DECL", "PROJECT")
OUTCOME_RU = {"auto": "авто", "check": "сверить", "todo": "вручную", "impossible": "невозможно", "info": "сведения"}


def _counts(findings: list[Finding], family: bool) -> dict[str, int]:
    keys = FAMILY if family else OUTCOMES
    c = Counter(f.family if family else f.outcome for f in findings)
    return {k: int(c.get(k, 0)) for k in keys}


def replacements(findings: list[Finding]) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for f in findings:
        if f.rule != "C2A-LIB001":
            continue
        src = str(f.data.get("source", ""))
        key = (src.lower(), str(f.data.get("kind", "")))
        row = rows.setdefault(
            key,
            {
                "source": src,
                "target": f.data.get("target"),
                "kind": f.data.get("kind", "none"),
                "count": 0,
                "url": f.data.get("url"),
                "outcome": f.outcome,
            },
        )
        row["count"] += 1
    return sorted(rows.values(), key=lambda r: (r["source"].lower(), r["kind"]))


def build_json(s: Session, effort: Effort, objects: list[dict[str, str]]) -> dict[str, Any]:
    findings = sorted(s.findings, key=lambda f: f.sort_key)
    eff = table()
    by_lang: dict[str, dict[str, int]] = {}
    matrix: dict[str, dict[str, int]] = {}
    for lang in LANG_ORDER:
        fl = [f for f in findings if f.language == lang]
        if fl:
            by_lang[lang] = _counts(fl, True)
            matrix[lang] = _counts(fl, False)
    out_findings = []
    for f in findings:
        lo, mode, hi = minutes_for(f, eff)
        origin: dict[str, Any] = {"file": f.file.replace("\\", "/").rsplit("/", 1)[-1]}
        if f.line:
            origin["line"] = f.line
        if f.column:
            origin["column"] = f.column
        if f.local_id:
            origin["local_id"] = str(f.local_id)
        item: dict[str, Any] = {
            "rule": f.rule,
            "outcome": f.outcome,
            "family_outcome": f.family,
            "language": f.language,
            "origin": origin,
            "message": f.message,
            "minutes": {"min": lo, "mode": mode, "max": hi},
        }
        if f.pou:
            item["pou"] = f.pou
        if f.related:
            item["related"] = list(f.related)
        if f.source_ref:
            item["source_ref"] = f.source_ref
        out_findings.append(item)
    p = s.project
    report: dict[str, Any] = {
        "format": "plc-migration-report/1",
        "tool": {"name": TOOL_NAME, "version": __version__},
        "source": {
            "kind": p.source_kind,
            "sha256": hashlib.sha256(p.doc.raw).hexdigest(),
            **({"ide": p.product} if p.product else {}),
            **({"ide_version": p.product_version} if p.product_version else {}),
        },
        "target": {"profile": s.target.id, "version": str(s.target.meta.get("ide_version", ""))},
        "totals": {"by_outcome": _counts(findings, True), "by_language": by_lang},
        "findings": out_findings,
        "effort": {
            "model": effort.model,
            "runs": effort.runs,
            "seed": effort.seed,
            "p50_h": effort.p50_h,
            "p90_h": effort.p90_h,
            "calibrated": effort.calibrated,
            "calibration": effort.calibration,
        },
        "outcomes": _counts(findings, False),
        "matrix": matrix,
        "tasks": s.task_table,
        "io_map": s.io_map,
        "replacements": replacements(findings),
        "objects": objects,
        "import": {"form": s.options.form, "mode": s.options.mode, "libraries": s.libraries_out},
        "markers_existing": s.existing_markers,
        "notes": s.notes,
        "effort_by_pou": {k: {"p50_h": v[0], "p90_h": v[1]} for k, v in effort.by_pou.items()},
        "effort_by_rule_minutes": effort.by_rule_minutes,
    }
    return report


def source_label(source: dict[str, Any]) -> str:
    """«CODESYS V3.5 SP17 Patch 3» без повтора имени продукта, если версия его уже содержит."""
    ide = str(source.get("ide") or "")
    ver = str(source.get("ide_version") or "")
    if ide and ver.startswith(ide):
        return ver
    return " ".join(x for x in (ide, ver) if x) or "—"


def to_json_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")


def _md_table(head: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def build_md(report: dict[str, Any]) -> str:
    oc = report["outcomes"]
    eff = report["effort"]
    lines = [
        "# Отчёт о переносе в Astra.IDE",
        "",
        f"Создано {report['tool']['name']} {report['tool']['version']}. Источник: {source_label(report['source'])}"
        f", SHA-256 `{report['source']['sha256'][:16]}…`. "
        f"Цель: профиль `{report['target']['profile']}`.",
        "",
        "## Сводка",
        "",
        _md_table(
            ["авто", "сверить", "вручную", "невозможно", "сведения"],
            [[str(oc["auto"]), str(oc["check"]), str(oc["todo"]), str(oc["impossible"]), str(oc["info"])]],
        ),
        "",
        f"Трудоёмкость (модель {eff['model']}, {eff['runs']} проб, seed {eff['seed']}): P50 = {eff['p50_h']} ч, "
        f"P90 = {eff['p90_h']} ч. "
        + (f"Модель, калибрована по {eff['calibration']}." if eff["calibrated"] else "Модель, не калибрована."),
        "",
        "## Языки × исходы",
        "",
    ]
    rows = []
    for lang, c in report["matrix"].items():
        rows.append([lang] + [str(c.get(k, 0)) for k in ("auto", "check", "todo", "impossible", "info")])
    lines.append(
        _md_table(["язык", "авто", "сверить", "вручную", "невозможно", "сведения"], rows) if rows else "нет находок"
    )
    if report["tasks"]:
        lines += ["", "## Задачи: приоритеты до и после", ""]
        lines.append(
            _md_table(
                ["задача", "тип", "интервал, мс", "было", "стало", "почему"],
                [
                    [
                        t["task"],
                        str(t.get("kind", "")),
                        str(t.get("interval_ms", "")),
                        str(t["before"]),
                        str(t["after"]),
                        str(t.get("reason", "")),
                    ]
                    for t in report["tasks"]
                ],
            )
        )
    if report["replacements"]:
        lines += ["", "## Замены библиотек", ""]
        lines.append(
            _md_table(
                ["источник", "замена", "вид", "мест", "документ"],
                [
                    [r["source"], str(r.get("target") or "—"), r["kind"], str(r["count"]), str(r.get("url") or "")]
                    for r in report["replacements"]
                ],
            )
        )
    if report["io_map"]:
        lines += ["", "## Карта каналов (io-map)", ""]
        lines.append(
            _md_table(
                ["переменная", "ОВЕН", "REGUL", "исход"],
                [
                    [r["variable"], r["owen"], r["regul"], OUTCOME_RU.get(r["outcome"], r["outcome"])]
                    for r in report["io_map"]
                ],
            )
        )
    lines += ["", "## Находки", ""]
    lines.append(
        _md_table(
            ["правило", "исход", "семейство", "язык", "объект", "строка", "сообщение"],
            [
                [
                    f["rule"],
                    f["outcome"],
                    f["family_outcome"],
                    f["language"],
                    f.get("pou", "—"),
                    str(f["origin"].get("line", "")),
                    f["message"],
                ]
                for f in report["findings"]
            ],
        )
    )
    if report["notes"]:
        lines += ["", "## Заметки", ""] + [f"- {n}" for n in report["notes"]]
    lines += [
        "",
        "Компиляция в Astra.IDE не означает работы на контроллере REGUL: рантайм, драйверы и железо "
        "этим отчётом не проверяются.",
        "",
    ]
    return "\n".join(lines)


CSS = """
:root{--bg:#f6f7f9;--fg:#1b2736;--muted:#56677d;--card:#ffffff;--line:#d5dbe3;--acc:#c2410c;--ok:#2f7d4f;--warn:#b7791f;--bad:#b42318}
@media (prefers-color-scheme: dark){:root{--bg:#121a24;--fg:#e6ebf1;--muted:#9aa8b8;--card:#1b2736;--line:#2c3b4f;--acc:#ff7a1a;--ok:#5fbf86;--warn:#e0a84a;--bad:#ff6b5e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.sub{color:var(--muted)}.tiles{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;min-width:120px}
.tile b{display:block;font-size:22px}.tile.acc b{color:var(--acc)}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);font-size:13px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600}
.o-auto{color:var(--ok)}.o-check{color:var(--warn)}.o-todo,.o-impossible{color:var(--bad)}.o-info{color:var(--muted)}
.wrap{overflow-x:auto}code{font-family:ui-monospace,Consolas,monospace;font-size:12px}
"""


def build_html(report: dict[str, Any]) -> str:
    e = html.escape
    oc = report["outcomes"]
    eff = report["effort"]

    def table_html(head: list[str], rows: list[list[str]], raw_cols: set[int] | None = None) -> str:
        raw_cols = raw_cols or set()
        hs = "".join(f"<th>{e(h)}</th>" for h in head)
        body = []
        for r in rows:
            cells = "".join(f"<td>{c if i in raw_cols else e(c)}</td>" for i, c in enumerate(r))
            body.append(f"<tr>{cells}</tr>")
        return f'<div class="wrap"><table><thead><tr>{hs}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'

    tiles = "".join(
        f'<div class="tile"><span class="o-{k}">{e(OUTCOME_RU[k])}</span><b>{oc[k]}</b></div>'
        for k in ("auto", "check", "todo", "impossible", "info")
    )
    tiles += f'<div class="tile acc"><span>P50 / P90, ч (модель)</span><b>{eff["p50_h"]} / {eff["p90_h"]}</b></div>'
    parts = [
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Отчёт о переносе — {e(report['tool']['name'])}</title><style>{CSS}</style></head><body><main>",
        "<h1>Отчёт о переносе в Astra.IDE</h1>",
        f'<div class="sub">{e(report["tool"]["name"])} {e(report["tool"]["version"])} · источник '
        f"{e(source_label(report['source']))} · профиль "
        f"<code>{e(report['target']['profile'])}</code></div>",
        f'<div class="tiles">{tiles}</div>',
        '<div class="sub">Часы — модель (треугольное распределение, Монте-Карло'
        f" {eff['runs']} проб); {e('калибрована по ' + eff['calibration'] if eff['calibrated'] else 'не калибрована')}.</div>",
        "<h2>Языки × исходы</h2>",
        table_html(
            ["язык", "авто", "сверить", "вручную", "невозможно", "сведения"],
            [
                [lang] + [str(c.get(k, 0)) for k in ("auto", "check", "todo", "impossible", "info")]
                for lang, c in report["matrix"].items()
            ],
        ),
    ]
    if report["tasks"]:
        parts += [
            "<h2>Задачи</h2>",
            table_html(
                ["задача", "интервал, мс", "было", "стало", "почему"],
                [
                    [
                        t["task"],
                        str(t.get("interval_ms", "")),
                        str(t["before"]),
                        str(t["after"]),
                        str(t.get("reason", "")),
                    ]
                    for t in report["tasks"]
                ],
            ),
        ]
    if report["replacements"]:
        parts += [
            "<h2>Замены библиотек</h2>",
            table_html(
                ["источник", "замена", "вид", "мест"],
                [
                    [r["source"], str(r.get("target") or "—"), r["kind"], str(r["count"])]
                    for r in report["replacements"]
                ],
            ),
        ]
    if report["io_map"]:
        parts += [
            "<h2>Карта каналов</h2>",
            table_html(
                ["переменная", "ОВЕН", "REGUL", "исход"],
                [
                    [
                        r["variable"],
                        r["owen"],
                        r["regul"],
                        f'<span class="o-{e(r["outcome"])}">{e(OUTCOME_RU.get(r["outcome"], r["outcome"]))}</span>',
                    ]
                    for r in report["io_map"]
                ],
                {3},
            ),
        ]
    parts += [
        "<h2>Находки</h2>",
        table_html(
            ["правило", "исход", "язык", "объект", "строка", "сообщение"],
            [
                [
                    f["rule"],
                    f'<span class="o-{e(f["outcome"])}">{e(f["outcome"])}</span>',
                    f["language"],
                    f.get("pou", "—"),
                    str(f["origin"].get("line", "")),
                    f["message"],
                ]
                for f in report["findings"]
            ],
            {1},
        ),
    ]
    parts.append(
        '<p class="sub">Компиляция в Astra.IDE не означает работы на контроллере REGUL.</p></main></body></html>\n'
    )
    return "".join(parts)
