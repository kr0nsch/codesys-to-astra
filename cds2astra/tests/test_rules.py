"""Правила C2A-*: корпус pos/neg, реестр, документация, отдельные случаи."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from c2a_helpers import CORPUS, REPO, case_session

from cds2astra import api
from cds2astra.rules import RULES, is_sp18plus
from cds2astra.session import Options

CASES = sorted(p.parent for p in CORPUS.rglob("case.toml"))
META_RULES = {"C2A-EDIT"}  # правило-сторож пересекающихся правок: проверяется отдельным тестом


@pytest.mark.parametrize("case_dir", CASES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_rule_corpus(case_dir: Path) -> None:
    meta = tomllib.loads((case_dir / "case.toml").read_text(encoding="utf-8"))
    s = case_session(case_dir)
    hits = [f for f in s.findings if f.rule == meta["rule"]]
    if meta["kind"] == "pos":
        assert hits, f"{meta['rule']}: нет находки на pos"
        assert {f.outcome for f in hits} <= set(meta["outcomes"]), [f.outcome for f in hits]
    else:
        if meta.get("allow_info"):
            hits = [f for f in hits if f.outcome != "info"]
        assert not hits, f"{meta['rule']}: лишняя находка на neg: {[f.message for f in hits]}"


def test_every_rule_has_corpus_and_docs() -> None:
    docs = (REPO / "docs" / "RULES.md").read_text(encoding="utf-8")
    for rid, info in RULES.items():
        assert info.title and info.explanation and info.source and info.outcomes and info.autofix, rid
        assert f"`{rid}`" in docs or f"## {rid}" in docs, f"{rid} не описано в docs/RULES.md"
        if rid in META_RULES:
            continue
        assert (CORPUS / rid / "pos" / "case.toml").is_file(), f"{rid}: нет корпуса pos"
        assert (CORPUS / rid / "neg" / "case.toml").is_file(), f"{rid}: нет корпуса neg"


def test_findings_use_registered_rules(boiler_session: api.Session) -> None:
    assert {f.rule for f in boiler_session.findings} <= set(RULES)


def test_boiler_mvp_rules(boiler_session: api.Session) -> None:
    """Вертикальный срез: IO001, LIB001, TASK001, MB001 на котельной."""
    got = {(f.rule, f.outcome) for f in boiler_session.findings}
    for need in [
        ("C2A-IO001", "check"),
        ("C2A-LIB001", "check"),
        ("C2A-TASK001", "check"),
        ("C2A-MB001", "check"),
        ("C2A-IO002", "check"),
        ("C2A-IO003", "check"),
        ("C2A-LIB001", "todo"),
    ]:
        assert need in got, need
    io = [r for r in boiler_session.io_map if r["rule"] == "C2A-IO003"]
    assert any(r.get("register") == 4000 for r in io)


def test_family_outcome_mapping(boiler_session: api.Session) -> None:
    for f in boiler_session.findings:
        if f.outcome == "check":
            assert f.family in ("review", "verify")
        if f.outcome == "todo":
            assert f.family == "manual"
    word = [f for f in boiler_session.findings if f.rule == "C2A-IO003" and "FLOAT32" in f.message]
    assert word and all(f.family == "verify" for f in word)  # порядок слов unknown -> verify


@pytest.mark.network
def test_task001_neg_niksosov_with_its_target_spec() -> None:
    """Neg-фикстура C2A-TASK001: образец niksosov (резервирование, MAIN_TASK — синхронизируемая) — находок check нет."""
    from c2a_helpers import sample

    p = api.load_project(sample("niksosov").read_bytes(), "n.xml")
    spec = 'cpu = "REGUL R500 71-W"\ncpu_type = "I"\nbus = "RegulBus OS"\nredundancy = true\nsync_task = "MAIN_TASK"\n'
    s = api.analyze(api.make_session(p, spec_text=spec))
    assert not [f for f in s.findings if f.rule == "C2A-TASK001" and f.outcome != "info"]


def test_sp18_detection() -> None:
    assert is_sp18plus("CODESYS V3.5 SP18 Patch 2")
    assert is_sp18plus("CODESYS V3.5 SP21")
    assert not is_sp18plus("CODESYS V3.5 SP17 Patch 3")
    assert not is_sp18plus("Astra.IDE V1.7.0.0")
    assert not is_sp18plus(None)


def test_sp18_utf8_non_ascii_variants() -> None:
    files = {
        "src/POUs/PRG_A/PRG_A.decl.st": "// Назначение: x\nPROGRAM PRG_A\nVAR\n    s : STRING;\nEND_VAR\n",
        "src/POUs/PRG_A/PRG_A.impl.st": "s := UTF8#'Привет';\ns := 'Котёл';\n",
    }
    p = api.load_project(api.layout_to_xml(files, "u"), "u.xml")
    s = api.analyze(api.make_session(p, options=Options(utf8_strings=True)))
    outs = sorted(f.outcome for f in s.findings if f.rule == "C2A-SP18-UTF8")
    assert outs == ["check", "todo"]


def test_sp19_partial_read_rewrites_and_write_todo() -> None:
    files = {
        "src/POUs/PRG_A/PRG_A.decl.st": "// Назначение: x\nPROGRAM PRG_A\nVAR\n    w : WORD;\n    b : BYTE;\nEND_VAR\n",
        "src/POUs/PRG_A/PRG_A.impl.st": "b := w.%B1;\nw.%B0 := b;\n",
    }
    p = api.load_project(api.layout_to_xml(files, "b"), "b.xml")
    s = api.analyze(api.make_session(p))
    res = api.migrate(s)
    outs = sorted(f.outcome for f in s.findings if f.rule == "C2A-SP19-BIT")
    assert outs == ["auto", "todo"]
    assert b"TO_BYTE(SHR(w, 8))" in res.files["astra-import.xml"]


def test_io001_moves_variable_and_renames_references(boiler_session: api.Session) -> None:
    res = api.migrate(boiler_session)
    xml = res.files["astra-import.xml"].decode("utf-8")
    assert "GVL_IO.xBurner1Fault" in xml
    assert "GVL_Hw.xBurner1Fault" not in xml
    assert re.search(r"xBurner1Fault : BOOL; // было: AT %IX0.0", xml)
    assert "wHmiStatus AT %MW10" in xml  # %M остаётся


def test_markers_on_one_line_merged_no_edit_conflicts(boiler_session: api.Session) -> None:
    res = api.migrate(boiler_session)
    assert not [f for f in boiler_session.findings if f.rule == "C2A-EDIT"]
    xml = res.files["astra-import.xml"].decode("utf-8")
    assert xml.count("MIGRATION-CHECK(C2A-LIB001): OSU.CONCAT4") == 1


def test_edit_conflict_reported() -> None:
    files = {
        "src/POUs/PRG_A/PRG_A.decl.st": "// Назначение: x\nPROGRAM PRG_A\nVAR\n    x : BOOL;\nEND_VAR\n",
        "src/POUs/PRG_A/PRG_A.impl.st": "x := TRUE;\n",
    }
    p = api.load_project(api.layout_to_xml(files, "e"), "e.xml")
    s = api.make_session(p)
    pou = p.find_pou("PRG_A")
    assert pou is not None and pou.body is not None and pou.body.code is not None
    s.edit(pou.body.code, 0, 4, "y", "R1")
    s.edit(pou.body.code, 2, 6, "z", "R2")
    s.resolve()
    assert [f.rule for f in s.findings] == ["C2A-EDIT", "C2A-EDIT"]
