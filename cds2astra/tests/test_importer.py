"""Импорт PLCopen XML: три размещения, шесть языков, ловушка CFC, задачи, библиотеки, устройства."""

from __future__ import annotations

import pytest
from c2a_helpers import REPO, sample

from cds2astra import api
from cds2astra.importers import plcopen

LM = REPO / "corpus" / "lang-matrix"


@pytest.mark.network
def test_inventory_astra_sample_niksosov() -> None:
    """Критерий этапа A: 5 POU, 7 действий, 4 тела CFC, 12 устройств, MAIN_TASK=1, TASK_DIAGN=10."""
    p = api.load_project(sample("niksosov").read_bytes(), "AstraRegul_stand.xml")
    inv = api.inventory(p)
    assert inv["pous"] == 5
    assert inv["actions"] == 7
    assert inv["cfc_bodies"] == 4
    assert inv["devices"] == 12
    assert {t["name"]: t["priority"] for t in inv["tasks"]} == {"MAIN_TASK": 1, "TASK_DIAGN": 10}
    assert {t["name"]: t["interval_ms"] for t in inv["tasks"]} == {"MAIN_TASK": 100.0, "TASK_DIAGN": 1000.0}
    assert p.placements == ["resource"]
    assert not p.has_plaintext
    assert any(lib.placeholder and lib.title == "PsIoDrvRegulBus_OS" for lib in p.libraries)
    assert p.product_version == "Astra.IDE V1.7.0.0"


@pytest.mark.network
def test_cfc_trap_empty_st_with_cfc_adddata() -> None:
    """Тело с пустым ST/xhtml и addData cfc — это CFC, а не пустой ST (в образце niksosov таких 4)."""
    p = api.load_project(sample("niksosov").read_bytes(), "n.xml")
    cfc = [x for x in p.all_pous() if x.body and x.body.language == "CFC"]
    assert len(cfc) == 4
    assert all(x.body is not None and x.body.code is None for x in cfc)


@pytest.mark.network
def test_sp18_and_srci_samples() -> None:
    sp18 = api.load_project(sample("sp18").read_bytes(), "sp18.xml")
    langs = {x.body.language for x in sp18.all_pous() if x.body}
    assert {"ST", "LD", "FBD", "CFC"} <= langs
    assert len(sp18.tasks) == 36
    srci = api.load_project(sample("srci").read_bytes(), "srci.xml")
    assert srci.has_plaintext and len(srci.pous) == 5


def test_lang_matrix_six_languages() -> None:
    p = api.load_project((LM / "source.handmade.xml").read_bytes(), "lm.xml")
    langs = {x.name: x.body.language for x in p.all_pous() if x.body}
    assert langs["PRG_LangSt"] == "ST"
    assert langs["PRG_LangFbd"] == "FBD"
    assert langs["PRG_LangLd"] == "LD"
    assert langs["PRG_LangCfc"] == "CFC"
    assert langs["PRG_LangSfc"] == "SFC"
    assert langs["PRG_LangIl"] == "IL"
    fbd = p.find_pou("PRG_LangFbd")
    assert fbd is not None and fbd.body is not None
    assert fbd.body.networks == 4
    assert any(r.kind == "block" and r.name == "OSU.WORD_TO_HEX_STR" for r in fbd.body.refs)
    sfc = p.find_pou("PRG_LangSfc")
    assert sfc is not None and sfc.body is not None
    assert {r.kind for r in sfc.body.refs} >= {"step", "action", "jump"}


def test_codesys_export_application_placement() -> None:
    """Экспорт узла Application CODESYS 3.5.17.30: project/addData/data[application]/resource."""
    p = api.load_project((LM / "export.codesys.xml").read_bytes(), "e.xml")
    assert "application" in p.placements
    assert p.has_plaintext
    assert len([x for x in p.pous if x.kind == "program"]) == 6  # IL не импортировался (проба P4)


def test_boiler_devices_tasks_libraries() -> None:
    p = api.load_project((REPO / "corpus" / "boiler-plc210" / "export.xml").read_bytes(), "b.xml")
    assert [t.priority for t in p.tasks] == [0, 1, 15]
    assert {d.name for d in p.all_devices()} >= {"OwenRTC", "Watchdog", "MV210_101_K3", "MU210_402_K3"}
    rtc = next(d for d in p.all_devices() if d.name == "OwenRTC")
    assert rtc.mappings[0].variable == "Application.GVL_Clock.dtNow"
    assert any(lib.title == "OwenStringUtils" for lib in p.libraries)
    hw = next(g for g in p.gvls if g.name == "GVL_Hw")
    at = {v.name: v.address for v in hw.vars}
    assert at["xBurner1Fault"] == "%IX0.0" and at["wHmiStatus"] == "%MW10"


def test_plaintext_copies_recorded() -> None:
    p = api.load_project((LM / "export.codesys.xml").read_bytes(), "e.xml")
    st = p.find_pou("PRG_LangSt")
    assert st is not None and st.decl is not None
    assert len(st.decl_copies) >= 1
    assert all(c.text == st.decl.text for c in st.decl_copies)


def test_interval_parsing() -> None:
    assert plcopen.parse_interval_ms("100", "ms") == 100.0
    assert plcopen.parse_interval_ms("t#1000ms") == 1000.0
    assert plcopen.parse_interval_ms("T#1s500ms") == 1500.0
    assert plcopen.parse_interval_ms("PT0.1S") == 100.0
    assert plcopen.parse_interval_ms("500", "us") == 0.5
    assert plcopen.parse_interval_ms("bogus") is None
    assert plcopen.parse_interval_ms(None) is None


def test_libname_parsing() -> None:
    assert plcopen.parse_libname("#Standard") == ("Standard", None, None)
    assert plcopen.parse_libname("PsTechEE, 1.7.0.4 (RegLab)") == ("PsTechEE", "1.7.0.4", "RegLab")


def test_not_plcopen_rejected() -> None:
    with pytest.raises(plcopen.ImportError_):
        api.load_project(b"<html><body/></html>", "x.xml")
    with pytest.raises(plcopen.ImportError_):
        api.load_project(b'<project xmlns="urn:other"/>', "x.xml")


def test_twincat_recognition_issue() -> None:
    raw = (
        b'<project xmlns="http://www.plcopen.org/xml/tc6_0200"><fileHeader productName="TwinCAT PLC Control" '
        b'productVersion="3.5.10.30"/><types><dataTypes/><pous/></types><addData>'
        b'<data name="http://www.3s-software.com/plcopenxml/application"><resource name="R"><addData>'
        b'<data name="http://www.3s-software.com/plcopenxml/pou"><pou name="P" pouType="program"><body><ST>'
        b'<xhtml xmlns="http://www.w3.org/1999/xhtml">;</xhtml></ST></body></pou></data></addData></resource></data>'
        b"</addData></project>"
    )
    p = api.load_project(raw, "tc.xml")
    assert "application" in p.placements
    assert any(i.code == "C2A-IMP-TC" for i in p.issues)


def test_unknown_adddata_preserved_and_reported() -> None:
    raw = (
        b'<project xmlns="http://www.plcopen.org/xml/tc6_0201"><types><dataTypes/><pous/></types>'
        b'<addData><data name="urn:vendor/secret" handleUnknown="preserve"><X/></data></addData></project>'
    )
    p = api.load_project(raw, "u.xml")
    assert [u.name for u in p.unknown] == ["urn:vendor/secret"]


def test_layout_input_s7_style(tmp_path: object) -> None:
    files = {
        "src/POUs/PRG_Main/PRG_Main.decl.st": "// Назначение: x\nPROGRAM PRG_Main\nVAR\n    x : BOOL;\nEND_VAR\n",
        "src/POUs/PRG_Main/PRG_Main.impl.st": "x := NOT x;\n",
    }
    p = api.load_project(api.layout_to_xml(files, "lay"), "lay.xml")
    assert p.find_pou("PRG_Main") is not None and p.has_plaintext
