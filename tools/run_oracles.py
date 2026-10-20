#!/usr/bin/env python3
"""Корпус -> cds2astra migrate -> оракулы Astra.IDE 1.7.2.2 и CODESYS 3.5.17.30 (цели app и pool).

Итог — docs/oracle-results.json (коммитится как свидетельство прогона, с датой и версиями) и строки для
docs/TEST_REPORT.md. Локально; в CI IDE нет — пропуск.

    python tools/run_oracles.py [--ide astra codesys] [--case boiler-plc210 lang-matrix s7-chain sp18-speedtests]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "codesys"))

from cdshost import ide_env, oracle  # noqa: E402

CASES = {
    "boiler-plc210": (
        ["corpus/boiler-plc210/export.xml", "--target-spec", "corpus/boiler-plc210/target.toml"],
        "synthetic",
    ),
    "lang-matrix": (["corpus/lang-matrix/source.handmade.xml"], "handmade -> ide-roundtrip"),
    "s7-chain": (["corpus/s7-chain"], "ide-export (s7-to-codesys 1.0 @ 2285760)"),
    "sp18-speedtests": (
        ["corpus/sp18-speedtests/codesys_code_execution_speedTests.xml"],
        "ide-export (SP18 Patch 2, MIT)",
    ),
}
OUT = REPO / "docs" / "oracle-results.json"


def migrate(case: str) -> Path:
    args, _cls = CASES[case]
    out = REPO / "out" / case
    cmd = [sys.executable, "-m", "cds2astra", "migrate", *args, "--out", str(out), "--fail-on", "never"]
    subprocess.run(cmd, cwd=REPO, check=True, env={"SOURCE_DATE_EPOCH": "0", **_env()})
    return out / "astra-import.xml"


def _env() -> dict[str, str]:
    import os

    return dict(os.environ)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="оракулы импорта и сборки по корпусу")
    ap.add_argument("--ide", nargs="+", default=["astra", "codesys"], choices=sorted(ide_env.IDES))
    ap.add_argument("--case", nargs="+", default=list(CASES), choices=list(CASES))
    args = ap.parse_args(argv)
    results = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {"runs": {}}
    ok_all = True
    for case in args.case:
        xml = migrate(case)
        for ide in args.ide:
            if not ide_env.available(ide):
                print(f"[oracles] {ide}: нет IDE — пропуск")
                continue
            res = oracle.run(ide, xml, xml.with_name("MIGRATION_REPORT.json"), ["app", "pool"], case)
            for r in res:
                key = f"{case}/{ide}/{r['target']}"
                results["runs"][key] = {
                    "case": case,
                    "fixture_class": CASES[case][1],
                    "ide": r["ide_title"],
                    "device": ide_env.ide(ide)["device"]["title"] if r["target"] == "app" else "— (пул POU)",
                    "target": r["target"],
                    "date": r["date"],
                    "ok": r["ok"],
                    "objects": r["objects_expected"],
                    "missing": len(r["missing"]),
                    "import_errors": len(r["import_errors"]),
                    "errors": len(r["errors"]),
                    "errors_outside_todo": len(r["errors_unexpected"]),
                    "warnings": len(r["warnings"]),
                    "allowed_objects": r["allowed_objects"],
                    "summary_line": r["summary_line"],
                    "libraries_missing": [m.get("library") for m in r.get("libraries_missing", [])],
                }
                ok_all = ok_all and r["ok"]
                print(f"[oracles] {key}: {'OK' if r['ok'] else 'ОШИБКА'} — {r['summary_line']}")
    results["updated"] = time.strftime("%Y-%m-%d")
    results["runs"] = dict(sorted(results["runs"].items()))
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
