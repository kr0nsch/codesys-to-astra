#!/usr/bin/env python3
"""Пробы A0 (P1–P6, P8) в Astra.IDE 1.7.2.2 и CODESYS 3.5.17.30 скриптом без интерфейса.

Каждая проба — случай оракула `tools/codesys/xml_oracle_ide.py`: новый проект (с устройством — цель app,
без — pool), библиотеки, импорт PLCopen XML, дерево объектов, задачи, сборка, обратный экспорт.
Сырые итоги — `build/probes/<ide>-result.json`, сводка — `probe/RESULTS.csv` (столбцы семейства,
00-INDEX §4.9) пишет `--write-results` по ручному разбору (docs/PROBES.md).

    python tools/probes.py --ide astra codesys [--only P2 P4] [--lang-matrix]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "codesys"))
sys.path.insert(0, str(REPO))

from cds2astra.importers.layout import st_to_plcopen as S  # noqa: E402
from cds2astra.importers.layout import stlayout as L  # noqa: E402
from cdshost import ide_env  # noqa: E402

WORK = REPO / "build" / "probes"
SCRIPT = REPO / "tools" / "codesys" / "xml_oracle_ide.py"


def constructs_xml() -> Path:
    """P8: фикстура ООП kns @ 6262d0f -> PLCopen XML (tc6_0200) тем же конвертером раскладки."""
    root = REPO / ".cache" / "kns-constructs" / "tools" / "plcopen" / "tests" / "fixtures" / "constructs"
    if not (root / "src").is_dir():
        raise SystemExit("нет .cache/kns-constructs: python tools/fetch_samples.py --kns <kns-port-domestic>")
    opts = S.Options(namespace=S.NS_0200, project_name="constructs", timestamp="2026-10-20T00:00:00")
    placed, _issues = S.collect_objects(str(root), [("src", [])])
    res = S.convert_objects(placed, opts)
    out = WORK / "p8_constructs.xml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(res.xml, encoding="utf-8", newline="\n")
    # пул: Persistent Variables -> обычный GVL (в пул PVL не вставить — kns docs/plcopen.md)
    pool_placed = []
    for obj, folder in placed:
        if obj.kind == "pvl":
            import re

            decl = re.sub(r"\s+PERSISTENT\b", "", obj.decl, flags=re.IGNORECASE)
            obj = L.StObject("gvl", obj.name, decl, obj.folder, subdir=obj.subdir)
        pool_placed.append((obj, folder))
    pool = WORK / "p8_constructs-pool.xml"
    pool.write_text(S.convert_objects(pool_placed, opts).xml, encoding="utf-8", newline="\n")
    return out


def cases(ide: str, only: set[str], lang_matrix: bool) -> list[dict[str, Any]]:
    dev = ide_env.ide(ide)["device"]
    proj = WORK / "projects"
    out: list[dict[str, Any]] = []

    def add(pid: str, name: str, xml: Path, target: str, export: bool = False, build: bool = True) -> None:
        if only and pid not in only:
            return
        out.append(
            {
                "name": f"{pid}-{name}-{target}",
                "probe": pid,
                "xml": str(xml),
                "target": target,
                "device": dev if target == "app" else None,
                "project": str(proj / f"{ide}-{pid}-{name}-{target}.project"),
                "export": str(WORK / "export" / f"{ide}-{pid}-{name}-{target}.xml") if export else None,
                "build": build,
            }
        )

    niks = REPO / ".cache" / "niksosov" / "AstraRegul_stand.xml"
    if niks.is_file():
        add("P1", "niksosov", niks, "app")
        add("P1", "niksosov", niks, "pool")
    add("P2", "resource", REPO / "probe" / "p2_resource_form.xml", "app", export=True)
    add("P2", "resource", REPO / "probe" / "p2_resource_form.xml", "pool")
    add("P3", "libraries", REPO / "probe" / "p3_libraries.xml", "app", export=True)
    add("P3", "libraries", REPO / "probe" / "p3_libraries.xml", "pool")
    add("P4", "il", REPO / "probe" / "p4_il.xml", "app", export=True)
    add("P4", "il", REPO / "probe" / "p4_il.xml", "pool", export=True)
    if lang_matrix or "P5" in only:
        lm = REPO / "corpus" / "lang-matrix" / "source.handmade.xml"
        add("P5", "langmatrix", lm, "app", export=True)
        add("P5", "langmatrix", lm, "pool", export=True)
    if not only or "P8" in only:
        p8 = constructs_xml()
        add("P8", "constructs", p8, "app")
        add("P8", "constructs", p8.with_name("p8_constructs-pool.xml"), "pool")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Пробы A0 в Astra.IDE / CODESYS")
    ap.add_argument("--ide", nargs="+", default=["astra", "codesys"], choices=sorted(ide_env.IDES))
    ap.add_argument("--only", nargs="*", default=[], help="P1 P2 P3 P4 P5 P8")
    ap.add_argument("--lang-matrix", action="store_true", help="P5: рукописный TC6 матрицы языков")
    ap.add_argument("--introspect", action="store_true", help="dir() объектов ScriptEngine (P3/P4)")
    args = ap.parse_args(argv)
    only = set(args.only)
    for ide in args.ide:
        if not ide_env.available(ide):
            print(f"[probe] {ide}: IDE не найдена — пропуск")
            continue
        job = {
            "repository": "System",
            "libraries": [ide_env.standard_spec(), ide_env.placeholder_spec("Util")],
            "introspect": args.introspect,
            "cases": cases(ide, only, args.lang_matrix),
        }
        print(f"[probe] {ide}: {len(job['cases'])} случаев ...", flush=True)
        data = ide_env.run_ide_job(ide, SCRIPT, job, WORK, f"{ide}-probes")
        for c in data.get("cases", []):
            summ = c.get("summary") or {}
            imp = [m for m in c.get("import_messages", []) if m["level"] in ("error", "warning", "skipped")]
            print(
                f"  {c['name']}: ok={c.get('ok')} objects={len(c.get('objects', []))} "
                f"errors={summ.get('errors')} warnings={summ.get('warnings')} import_issues={len(imp)} "
                f"exc={c.get('import_exception', '')[:80]}"
            )
        if data.get("error"):
            print(data["error"])
        print(f"[probe] {ide}: {data.get('elapsed_s')} с -> {WORK / (ide + '-probes-result.json')}")
        (WORK / f"{ide}-summary.json").write_text(
            json.dumps(
                [{k: v for k, v in c.items() if k != "objects"} for c in data.get("cases", [])],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
