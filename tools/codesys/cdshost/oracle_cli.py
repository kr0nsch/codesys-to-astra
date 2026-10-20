"""Командная строка xml_oracle.py (Python 3.11+)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import ide_env, oracle


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="xml_oracle.py", description="Оракул импорта astra-import.xml в Astra.IDE/CODESYS")
    ap.add_argument("xml", help="astra-import.xml (рядом — MIGRATION_REPORT.json)")
    ap.add_argument("--ide", required=True, choices=sorted(ide_env.IDES))
    ap.add_argument("--target", nargs="+", default=["app"], choices=["app", "pool"])
    ap.add_argument("--form", default="pous", choices=["pous"], help="форма импорта (resource не импортируется — P1/P2)")
    ap.add_argument("--case", help="имя случая (по умолчанию — имя каталога XML)")
    ap.add_argument("--report", help="MIGRATION_REPORT.json (по умолчанию рядом с XML)")
    ap.add_argument("--timeout", type=float, default=1800.0)
    args = ap.parse_args(argv)
    xml = Path(args.xml).resolve()
    report = Path(args.report).resolve() if args.report else xml.with_name("MIGRATION_REPORT.json")
    if not xml.is_file() or not report.is_file():
        print(f"[oracle] нет {xml} или {report}", file=sys.stderr)
        return 2
    if not ide_env.available(args.ide):
        print(f"[oracle] {args.ide}: IDE не найдена — пропуск", file=sys.stderr)
        return 3
    case = args.case or xml.parent.name
    try:
        results = oracle.run(args.ide, xml, report, args.target, case, args.timeout)
    except RuntimeError as exc:
        print(f"[oracle] {exc}", file=sys.stderr)
        return 3
    ok = True
    for r in results:
        verdict = "OK" if r["ok"] else "ОШИБКА"
        print(
            f"[oracle] {r['ide_title']} {r['target']}: объектов {r['objects_expected']} (в дереве {r['objects_found']}), "
            f"нет {len(r['missing'])}, ошибок импорта {len(r['import_errors'])}, ошибок сборки {len(r['errors'])} "
            f"(вне todo {len(r['errors_unexpected'])}), предупреждений {len(r['warnings'])} — {verdict}"
        )
        if r.get("summary_line"):
            print(f"         {r['summary_line']}")
        for line in r["missing"][:20]:
            print(f"         нет объекта: {line}")
        for line in (r["import_errors"] + r["errors_unexpected"] + ([r["error"]] if r.get("error") else []))[:30]:
            print(f"         {line}")
        ok = ok and r["ok"]
    return 0 if ok else 1
