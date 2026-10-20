"""Командная строка cds2astra.

    cds2astra inventory FILE [--format text|json]
    cds2astra analyze FILE [--target astra-1.7.2.2] [--target-spec F] [--format text|json|md|html] [--fail-on todo|check|never]
    cds2astra migrate FILE --out DIR [--mode astra|preserve] [--form pous|resource] [--io keep-modbus|local]
                     [--io-list F] [--target-spec F] [--zip F] [--source-option utf8-strings]
    cds2astra downgrade FILE --out DIR        (то же, что migrate: правила SP18+ включены всегда)
    cds2astra explain ID
    cds2astra profiles list | show ID | diff A B
    cds2astra probe [--ide-profile PROFILE.xml ...] [--out DIR]
    cds2astra build-errors parse FILE [--trace trace.json] [--report MIGRATION_REPORT.json] | status FILE

FILE — PLCopen XML или каталог раскладки plc-repo-template (с src/). Коды выхода: 0 — успех; 1 — находки не
ниже --fail-on; 2 — ошибка ввода.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import TOOL_NAME, __version__, api, profiles
from .emit.report import source_label
from .findings import at_least
from .importers import plcopen
from .owner import build_errors, probe
from .rules import RULES
from .session import Options
from .xmltree import XmlError

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT = 2


def _read_input(path: str) -> tuple[bytes, str]:
    p = Path(path)
    if p.is_dir():
        files = {}
        for f in sorted((p / "src").rglob("*.st")):
            files[f.relative_to(p).as_posix()] = f.read_text(encoding="utf-8")
        if not files:
            raise ValueError(f"{path}: каталог без src/*.st")
        return api.layout_to_xml(files, p.name), p.name + ".xml"
    return p.read_bytes(), p.name


def _source_date() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if epoch.isdigit():
        import datetime as dt

        return dt.datetime.fromtimestamp(int(epoch), tz=dt.UTC).strftime("%Y-%m-%dT%H:%M:%S")
    return "1970-01-01T00:00:00"


def _session(args: argparse.Namespace, data: bytes, name: str) -> api.Session:
    p = api.load_project(data, name)
    if getattr(args, "layout", False):
        p.source_kind = "st-layout"
    spec = Path(args.target_spec).read_text(encoding="utf-8") if getattr(args, "target_spec", None) else None
    io_list = Path(args.io_list).read_text(encoding="utf-8") if getattr(args, "io_list", None) else None
    target_text = None
    target = getattr(args, "target", api.DEFAULT_TARGET)
    if target and target.endswith(".toml") and Path(target).is_file():
        target_text = Path(target).read_text(encoding="utf-8")
    utf8 = None
    if "utf8-strings" in (getattr(args, "source_option", None) or []):
        utf8 = True
    opts = Options(
        mode=getattr(args, "mode", "astra"),
        form=getattr(args, "form", "pous"),
        namespace=getattr(args, "namespace", "tc6_0200"),
        io=getattr(args, "io", "keep-modbus"),
        utf8_strings=utf8,
        source_date=_source_date(),
    )
    return api.make_session(p, target, target_text, spec, io_list, opts)


def cmd_inventory(args: argparse.Namespace) -> int:
    data, name = _read_input(args.file)
    inv = api.inventory(api.load_project(data, name))
    if args.format == "json":
        print(json.dumps(inv, ensure_ascii=False, indent=2))
    else:
        print(
            f"{name}: {source_label({'ide': inv['product'], 'ide_version': inv['product_version']})} "
            f"({inv['namespace']}, {', '.join(inv['placements'])})"
        )
        print(
            f"  POU {inv['pous']}, интерфейсов {inv['interfaces']}, действий {inv['actions']}, методов {inv['methods']}, "
            f"свойств {inv['properties']}, переходов {inv['transitions']}"
        )
        print(f"  тела: {', '.join(f'{k} {v}' for k, v in inv['bodies'].items())}")
        print(
            f"  GVL {inv['gvls']}, DUT {inv['duts']}, библиотек {inv['libraries']}, устройств {inv['devices']} "
            f"(привязок {inv['device_mappings']})"
        )
        tasks = ", ".join(f"{t['name']}={t['priority']} ({t['interval_ms']} мс)" for t in inv["tasks"])
        print(f"  задачи: {tasks or 'нет'}")
        print(
            f"  тексты объявлений: {'есть' if inv['plaintext'] else 'нет (C2A-FMT001)'}; неизвестных addData {inv['unknown_adddata']}"
        )
    return EXIT_OK


def cmd_analyze(args: argparse.Namespace) -> int:
    data, name = _read_input(args.file)
    s = api.analyze(_session(args, data, name))
    res = api.migrate(s)
    if args.format == "json":
        sys.stdout.write(res.files["MIGRATION_REPORT.json"].decode("utf-8"))
    elif args.format == "md":
        sys.stdout.write(res.files["MIGRATION_REPORT.md"].decode("utf-8"))
    elif args.format == "html":
        sys.stdout.write(res.files["MIGRATION_REPORT.html"].decode("utf-8"))
    else:
        oc = res.report["outcomes"]
        print(
            f"{name}: авто {oc['auto']}, сверить {oc['check']}, вручную {oc['todo']}, невозможно {oc['impossible']}, "
            f"сведения {oc['info']}; P50 {res.report['effort']['p50_h']} ч, P90 {res.report['effort']['p90_h']} ч (модель)"
        )
        for f in sorted(s.findings, key=lambda x: x.sort_key):
            if f.outcome == "info" and not args.verbose:
                continue
            where = f"{f.pou}:" if f.pou else ""
            print(f"  {f.rule:<14} {f.outcome:<6} {where}{f.line} {f.message}")
    worst = [f for f in s.findings if at_least(f.outcome, args.fail_on)]
    return EXIT_FINDINGS if worst else EXIT_OK


def cmd_migrate(args: argparse.Namespace, downgrade: bool = False) -> int:
    data, name = _read_input(args.file)
    s = api.analyze(_session(args, data, name))
    res = api.migrate(s)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for rel, blob in sorted(res.files.items()):
        (out / rel).write_bytes(blob)
    if args.zip:
        Path(args.zip).parent.mkdir(parents=True, exist_ok=True)
        Path(args.zip).write_bytes(api.to_zip(res.files))
    oc = res.report["outcomes"]
    print(
        f"{TOOL_NAME} {__version__}: {name} -> {out.as_posix()}/ ({len(res.files)} файлов)"
        + (f", zip {args.zip}" if args.zip else "")
    )
    print(
        f"  авто {oc['auto']}, сверить {oc['check']}, вручную {oc['todo']}, невозможно {oc['impossible']}, "
        f"сведения {oc['info']}; P50 {res.report['effort']['p50_h']} ч, P90 {res.report['effort']['p90_h']} ч (модель)"
    )
    worst = [f for f in s.findings if at_least(f.outcome, args.fail_on)]
    return EXIT_FINDINGS if worst else EXIT_OK


def cmd_explain(args: argparse.Namespace) -> int:
    info = RULES.get(args.id.upper())
    if info is None:
        print(f"нет правила {args.id}; есть: {', '.join(sorted(RULES))}", file=sys.stderr)
        return EXIT_INPUT
    print(
        f"{info.id} — {info.title}\n\n{info.explanation}\n\nИсходы: {', '.join(info.outcomes)}\n"
        f"Автоправка: {info.autofix}\nИсточник: {info.source}"
    )
    return EXIT_OK


def cmd_profiles(args: argparse.Namespace) -> int:
    if args.action == "list":
        for p in profiles.all_builtin():
            print(f"{p.id:<22} {p.kind:<7} {p.title} ({len(p.values)} значений)")
        return EXIT_OK
    if args.action == "show":
        p = profiles.load_builtin(args.ids[0])
        for k, v in sorted(p.values.items()):
            print(f"{k:<36} {v.value!s:<28} {v.status:<18} {v.source[:80]}")
        return EXIT_OK
    a, b = (profiles.load_builtin(x) for x in args.ids[:2])
    for key, va, vb in profiles.diff(a, b):
        print(f"{key:<36} {va!s:<28} {vb!s}")
    return EXIT_OK


def cmd_probe(args: argparse.Namespace) -> int:
    target = profiles.load_builtin(api.DEFAULT_TARGET)
    code = EXIT_OK
    for path in args.ide_profile or []:
        found = profiles.probe_profile_xml(Path(path).read_bytes())
        problems = profiles.check_probe(target, found)
        print(
            f"{path}: компилятор {found.get('compiler')}, PLCopenXML {found.get('plcopenxml')} — "
            + ("совпадает с профилем" if not problems else "; ".join(problems))
        )
        code = code or (EXIT_FINDINGS if problems else EXIT_OK)
    if args.out:
        files = probe.package()
        out = Path(args.out)
        for rel, blob in files.items():
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
        print(f"пакет проб: {out.as_posix()}/ ({len(files)} файлов)")
    return code


def cmd_build_errors(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8")
    if args.action == "status":
        st_ = build_errors.status(text)
        print(json.dumps(st_, ensure_ascii=False, indent=2))
        return EXIT_OK
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8")) if args.trace else None
    msgs = build_errors.parse(text)
    rows = build_errors.suggest(msgs, trace)
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(
                f"{r['severity']:<8} {r.get('code') or '—':<6} {r.get('object') or '—'} {r.get('position') or ''}: {r['text']}"
            )
            print(f"         -> {r['suggestion']}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog=TOOL_NAME, description="Перенос проектов CODESYS 3.5 в Astra.IDE 1.7 (REGUL)")
    ap.add_argument("--version", action="version", version=f"{TOOL_NAME} {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inventory", help="состав проекта")
    p.add_argument("file")
    p.add_argument("--format", choices=["text", "json"], default="text")

    def common(q: argparse.ArgumentParser) -> None:
        q.add_argument("file")
        q.add_argument("--target", default=api.DEFAULT_TARGET, help="id профиля цели или путь к TOML профиля")
        q.add_argument("--target-spec", help="target.toml: ЦП, шина, резервирование")
        q.add_argument("--io-list", help="io.toml/.json — модули ОВЕН без дерева устройств")
        q.add_argument("--source-option", action="append", choices=["utf8-strings"], help="опции компилятора источника")
        q.add_argument("--fail-on", choices=["todo", "check", "never"], default="todo")

    p = sub.add_parser("analyze", help="находки и отчёт без записи файлов")
    common(p)
    p.add_argument("--format", choices=["text", "json", "md", "html"], default="text")
    p.add_argument("-v", "--verbose", action="store_true", help="и находки info")

    for name in ("migrate", "downgrade"):
        p = sub.add_parser(name, help="перенос: astra-import.xml, отчёт, io-map, IMPORT_STEPS")
        common(p)
        p.add_argument("--out", required=True)
        p.add_argument("--mode", choices=["astra", "preserve"], default="astra")
        p.add_argument("--form", choices=["pous", "resource"], default="pous")
        p.add_argument("--namespace", choices=["tc6_0200", "tc6_0201"], default="tc6_0200")
        p.add_argument("--io", choices=["keep-modbus", "local"], default="keep-modbus")
        p.add_argument("--zip")

    p = sub.add_parser("explain", help="описание правила")
    p.add_argument("id")

    p = sub.add_parser("profiles", help="профили IDE")
    p.add_argument("action", choices=["list", "show", "diff"])
    p.add_argument("ids", nargs="*")

    p = sub.add_parser("probe", help="сверка профилей IDE и пакет проб для владельца")
    p.add_argument("--ide-profile", action="append", help="Profiles/*.profile.xml CODESYS или Astra.IDE")
    p.add_argument("--out", help="каталог пакета проб (E5, E7, E8, раскладка)")

    p = sub.add_parser("build-errors", help="разбор сообщений Astra.IDE / CODESYS")
    p.add_argument("action", choices=["parse", "status"])
    p.add_argument("file")
    p.add_argument("--trace")
    p.add_argument("--format", choices=["text", "json"], default="text")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "inventory":
            return cmd_inventory(args)
        if args.cmd == "analyze":
            return cmd_analyze(args)
        if args.cmd in ("migrate", "downgrade"):
            return cmd_migrate(args, args.cmd == "downgrade")
        if args.cmd == "explain":
            return cmd_explain(args)
        if args.cmd == "profiles":
            if args.action in ("show", "diff") and len(args.ids) < (1 if args.action == "show" else 2):
                print("profiles show ID | diff A B", file=sys.stderr)
                return EXIT_INPUT
            return cmd_profiles(args)
        if args.cmd == "probe":
            return cmd_probe(args)
        return cmd_build_errors(args)
    except (OSError, ValueError, XmlError, plcopen.ImportError_, profiles.ProfileError) as exc:
        print(f"{TOOL_NAME}: {exc}", file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    sys.exit(main())
