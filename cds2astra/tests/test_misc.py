"""IL -> ST, разбор сообщений IDE, пакет проб, CLI, чистота ядра, устойчивость к мутациям XML, генераторы корпусов."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from c2a_helpers import REPO
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as hs

from cds2astra import api, cli, iltost, xmltree
from cds2astra.importers import plcopen
from cds2astra.owner import build_errors, probe

KNS_LINES = """Error       C0077 Неизвестный тип: 'PsModbusSerialMaster.ChannelStatus' [Regul.PRG_ModbusMap_Regul, Строка 23 (Объявл.)]
Error       C0032 Невозможно конвертировать тип 'X' в тип 'ANY' [Regul.PRG_ModbusMap_Regul, Строка 38, Столбец 1 (Реализ.)]
Warning     C0100 Библиотека CmpCodeMeter не добавлена в Менеджер библиотек, либо не найдено корректной лицензии [Library Manager]
Error C0046 Identifier 'F_X' not defined [PRG_Main, Line 4, Column 1 (Impl)]
Компиляция завершена -- 8 ошибок, 1 предупреждений
"""


def test_il_to_st_subset() -> None:
    r = iltost.translate("LD xA\nAND xB\nST xQ\nCAL fbTon(IN := xQ, PT := T#1S)\nLD fbTon.Q\nST xDone\n")
    assert r.ok
    assert r.st.splitlines() == ["xQ := xA AND xB;", "fbTon(IN := xQ, PT := T#1S);", "xDone := fbTon.Q;"]


def test_il_to_st_jumps_labels_and_ops() -> None:
    r = iltost.translate("LD i\nGT 10\nJMPC big\nLD 0\nST i\nbig: LD i\nADD 1\nST i\nLDN x\nS y\nR z\nRETC\n")
    assert r.ok
    assert "IF i > 10 THEN JMP big; END_IF;" in r.st
    assert "big:" in r.st and "i := i + 1;" in r.st
    assert "IF NOT x THEN y := TRUE; END_IF;" in r.st
    assert "IF NOT x THEN RETURN; END_IF;" in r.st


def test_il_unsupported_parentheses() -> None:
    r = iltost.translate("LD a\nAND( b\nOR c\n)\nST q\n")
    assert not r.ok and r.unsupported


def test_build_errors_parse_ru_en() -> None:
    msgs = build_errors.parse(KNS_LINES)
    assert len(msgs) == 4
    assert (
        msgs[0].code == "C0077"
        and msgs[0].object == "PRG_ModbusMap_Regul"
        and msgs[0].line == 23
        and msgs[0].part == "decl"
    )
    assert msgs[1].column == 1 and msgs[1].part == "impl"
    assert msgs[2].severity == "Warning" and msgs[2].object == "Library Manager"
    assert msgs[3].object == "PRG_Main" and msgs[3].part == "impl"


def test_build_errors_suggest_with_trace(boiler_session: api.Session) -> None:
    import json

    trace = json.loads(api.migrate(boiler_session).files["trace.json"])
    rows = build_errors.suggest(
        build_errors.parse("Error C0077 Неизвестный тип: 'OPR.ON_OFF_HIST_REG' [PRG_Backup, Строка 8 (Объявл.)]"), trace
    )
    assert "todo" in rows[0]["suggestion"] and "C2A-LIB001" in rows[0]["rules"]


def test_build_errors_status() -> None:
    text = "### Итерация 1 — x\n| 1.1 | ошибка | C0077 | P | | | | | исправлено в `abc` |\n### Итерация 2 — y\n"
    st = build_errors.status(text)
    assert st["iterations"] == 2 and st["statuses"].get("исправлено") == 1


def test_probe_package() -> None:
    files = probe.package()
    assert set(files) == {"layout-probe.xml", "E5.md", "E7.md", "E8.md", "RESULTS.csv"}
    p = api.load_project(files["layout-probe.xml"], "lp.xml")
    assert p.find_pou("PRG_C2aLayoutProbe") is not None
    assert files["RESULTS.csv"].decode().startswith("probe_id,construct,file,expected,observed")


def test_cli_inventory_analyze_migrate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    boiler = REPO / "corpus" / "boiler-plc210"
    assert cli.main(["inventory", str(boiler / "export.xml")]) == 0
    assert "задачи: FastTask=0" in capsys.readouterr().out
    assert cli.main(["analyze", str(boiler / "export.xml"), "--fail-on", "never", "--format", "json"]) == 0
    assert cli.main(["analyze", str(boiler / "export.xml"), "--target-spec", str(boiler / "target.toml")]) == 1
    out = tmp_path / "o"
    code = cli.main(
        [
            "migrate",
            str(boiler / "export.xml"),
            "--target-spec",
            str(boiler / "target.toml"),
            "--out",
            str(out),
            "--zip",
            str(tmp_path / "o.zip"),
            "--fail-on",
            "never",
        ]
    )
    assert code == 0 and (out / "astra-import.xml").is_file() and (tmp_path / "o.zip").is_file()
    assert cli.main(["explain", "C2A-IO001"]) == 0
    assert cli.main(["explain", "C2A-NOPE"]) == 2
    assert cli.main(["profiles", "list"]) == 0
    assert cli.main(["profiles", "show", "astra-1.7.2.2"]) == 0
    assert cli.main(["profiles", "diff", "astra-1.7.2.2", "owen-plc2xx-sp17"]) == 0
    assert cli.main(["profiles", "show"]) == 2
    assert cli.main(["probe", "--out", str(tmp_path / "probe")]) == 0
    bad = tmp_path / "bad.xml"
    bad.write_text("<x", encoding="utf-8")
    assert cli.main(["inventory", str(bad)]) == 2
    errs = tmp_path / "errs.txt"
    errs.write_text(KNS_LINES, encoding="utf-8")
    assert cli.main(["build-errors", "parse", str(errs), "--trace", str(out / "trace.json")]) == 0
    assert cli.main(["build-errors", "status", str(errs)]) == 0


def test_cli_layout_directory_input(tmp_path: Path) -> None:
    src = tmp_path / "proj" / "src" / "POUs" / "PRG_A"
    src.mkdir(parents=True)
    (src / "PRG_A.decl.st").write_text(
        "// Назначение: x\nPROGRAM PRG_A\nVAR\n    s : STRING;\nEND_VAR\n", encoding="utf-8"
    )
    (src / "PRG_A.impl.st").write_text("s := OSU.After('a=b', '=');\n", encoding="utf-8")
    assert cli.main(["migrate", str(tmp_path / "proj"), "--out", str(tmp_path / "o"), "--fail-on", "never"]) == 0
    assert b"F_C2aAfter" in (tmp_path / "o" / "astra-import.xml").read_bytes()


def test_python_m_entrypoint() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "cds2astra", "--version"], capture_output=True, text=True, cwd=REPO, check=False
    )
    assert out.returncode == 0 and "cds2astra 0.1.0" in out.stdout


FORBIDDEN = {"subprocess", "socket", "urllib", "http", "requests", "ctypes"}


def test_core_has_no_network_or_processes() -> None:
    """Ядро работает в Pyodide: без subprocess, socket, urllib (кроме cli.py и tests/)."""
    pkg = REPO / "cds2astra"
    for path in pkg.rglob("*.py"):
        rel = path.relative_to(pkg).as_posix()
        if rel.startswith("tests/") or rel == "cli.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            assert not (set(names) & FORBIDDEN), f"{rel}: {names}"


def test_stlayout_copy_in_sync_with_template() -> None:
    a = (REPO / "tools" / "codesys" / "stlayout.py").read_bytes()
    b = (REPO / "cds2astra" / "importers" / "layout" / "stlayout.py").read_bytes()
    assert a == b


BASE = (REPO / "corpus" / "boiler-plc210" / "export.xml").read_bytes()


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(hs.integers(0, len(BASE) - 1), hs.integers(1, 40), hs.binary(max_size=12))
def test_xml_mutations_give_errors_not_crashes(pos: int, n: int, junk: bytes) -> None:
    data = BASE[:pos] + junk + BASE[pos + n :]
    try:
        p = api.load_project(data, "m.xml")
    except (xmltree.XmlError, plcopen.ImportError_, UnicodeDecodeError):
        return
    s = api.analyze(api.make_session(p))
    api.migrate(s)


@pytest.mark.parametrize(
    "script",
    [
        "tools/corpus/build_lang_matrix.py",
        "tools/corpus/owen_overlay.py",
        "tools/corpus/make_rule_corpus.py",
        "tools/gen_docs.py",
    ],
)
def test_generated_files_up_to_date(script: str) -> None:
    out = subprocess.run(
        [sys.executable, str(REPO / script), "--check"], capture_output=True, text=True, cwd=REPO, check=False
    )
    assert out.returncode == 0, out.stdout + out.stderr
