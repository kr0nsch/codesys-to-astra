"""Профили, таблица замен, сигнатуры AstraCompat, приоритеты задач (golden), модель трудоёмкости."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from c2a_helpers import REPO

from cds2astra import api, libmap, profiles, resources
from cds2astra.estimate import Lcg, estimate, triangular
from cds2astra.findings import Finding
from cds2astra.tasks import TaskIn, reassign

ASTRA = "astra-1.7.2.2"
PROFILE_XML = {
    "astra": Path(
        r"C:\Program Files\AstraRegul\Astra.IDE_64_1.7.2.2\Astra.IDE\Profiles\Astra.IDE_V1.7.2.2.profile.xml"
    ),
    "codesys": Path(r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Profiles\CODESYS V3.5 SP17 Patch 3.profile.xml"),
}


def test_profiles_load_and_documented_have_urls() -> None:
    allp = profiles.all_builtin()
    assert {p.id for p in allp} == {ASTRA, "owen-plc2xx-sp17", "codesys-sp18plus"}
    for p in allp:
        for v in p.values.values():
            if v.status == "documented":
                assert "http" in v.source, (p.id, v.key)


def test_profile_rejects_bad_status() -> None:
    with pytest.raises(profiles.ProfileError):
        profiles.parse('id="x"\nkind="target"\ntitle="t"\n[a]\nvalue=1\nstatus="maybe"\nsource="s"\ndate="d"\n')
    with pytest.raises(profiles.ProfileError):
        profiles.parse(
            'id="x"\nkind="target"\ntitle="t"\n[a]\nvalue=1\nstatus="documented"\nsource="без ссылки"\ndate="d"\n'
        )


def test_profile_copy_changes_output_without_code() -> None:
    """Копия профиля с другим значением меняет вывод без правки кода (полоса приоритетов)."""
    text = resources.read_text("profiles", "astra-ide-1.7.2.2_dev-11.7.2.60.toml")
    changed = text.replace("[tasks.band_start]\nvalue = 2", "[tasks.band_start]\nvalue = 6")
    assert changed != text
    xml = (REPO / "corpus" / "boiler-plc210" / "export.xml").read_bytes()
    base = api.analyze(api.make_session(api.load_project(xml, "b.xml")))
    alt = api.analyze(api.make_session(api.load_project(xml, "b.xml"), ASTRA, changed))
    assert [r["after"] for r in base.task_table] == [2, 3, 4]
    assert [r["after"] for r in alt.task_table] == [6, 7, 8]


@pytest.mark.parametrize("ide", ["astra", "codesys"])
def test_probe_profile_xml_matches_profile(ide: str) -> None:
    path = PROFILE_XML[ide]
    if not path.is_file():
        pytest.skip(f"{ide}: IDE не установлена")
    found = profiles.probe_profile_xml(path.read_bytes())
    assert profiles.check_probe(profiles.load_builtin(ASTRA), found) == []


def test_profile_diff() -> None:
    a = profiles.load_builtin(ASTRA)
    b = profiles.load_builtin("owen-plc2xx-sp17")
    keys = {k for k, _a, _b in profiles.diff(a, b)}
    assert "memory.input" in keys


def test_libmap_rows_have_urls_and_kinds() -> None:
    lm = libmap.load()
    assert lm.entries
    for e in lm.entries:
        assert e.source_url.startswith("http"), e
        assert e.kind in libmap.KINDS
        if e.kind in ("map", "wrap"):
            assert e.target
    assert lm.by_namespace()["osu"] == "OwenStringUtils"


def _decl_pins(text: str) -> list[tuple[str, str]]:
    pins = []
    section = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(("VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT")):
            section = s.split()[0]
            continue
        if s.startswith(("VAR", "END_VAR")):
            section = None if s.startswith("END_VAR") else section if s == "VAR_INPUT" else None
            continue
        if section in ("VAR_INPUT", "VAR_OUTPUT"):
            m = re.match(r"(\w+)\s*:\s*([^;:=/]+)", s)
            if m:
                pins.append((m.group(1), m.group(2).strip()))
    return pins


def test_wrap_signatures_match_owen_documents() -> None:
    """Тест сигнатур: пины обёрток AstraCompat совпадают по именам и типам с документацией ОВЕН."""
    lm = libmap.load()
    for e in lm.entries:
        if e.kind != "wrap":
            continue
        sig = lm.signature(e.library, e.source)
        assert sig is not None, f"{e.source}: нет сигнатуры в owen_signatures.toml"
        decl = REPO / "src" / "POUs" / str(e.target) / f"{e.target}.decl.st"
        assert decl.is_file(), decl
        text = decl.read_text(encoding="utf-8")
        ours = _decl_pins(text)
        want = [(n, t) for n, t, d in sig["pins"] if d in ("in", "out")]
        got = {n.lower(): t.upper().replace(" ", "") for n, t in ours}
        for name, typ in want:
            assert name.lower() in got, f"{e.target}: нет пина {name}"
            t_want = typ.upper().replace(" ", "")
            if t_want == "DECIMAL_SEPARATOR":
                t_want = "E_C2ADECIMALSEPARATOR"
            assert got[name.lower()] == t_want, f"{e.target}.{name}: {got[name.lower()]} != {typ}"
        ret = [t for _n, t, d in sig["pins"] if d == "ret"]
        if ret:
            header = next(line for line in text.splitlines() if line.startswith("FUNCTION "))
            assert header.split(":")[1].strip().upper() == ret[0].upper(), header


# --------------------------------------------------------------------------- приоритеты (golden ≥ 12 случаев)
def T(*specs: tuple[str, int | None]) -> list[TaskIn]:
    return [TaskIn(n, p) for n, p in specs]


GOLDEN = [
    ("уже в полосе — без изменений", T(("A", 5), ("B", 10)), {}, [5, 10]),
    ("0 и 1 -> полоса", T(("Fast", 0), ("Main", 1), ("Slow", 15)), {}, [2, 3, 4]),
    ("визуализация -> 15", T(("Main", 1), ("VISU_TASK", 31)), {}, [2, 15]),
    (
        "0..31 сжатие (16 уровней в 12)",
        T(*[(f"T{i:02d}", i * 2) for i in range(16)]),
        {},
        [2, 2, 3, 4, 5, 5, 6, 7, 8, 8, 9, 10, 11, 11, 12, 13],
    ),
    ("коллизия одинаковых уровней", T(("A", 3), ("B", 3)), {}, [3, 3]),
    ("None -> умолчание 2", T(("A", None), ("B", 20)), {}, [2, 3]),
    ("резерв, ЦП I: синхронизируемая -> 1", T(("Main", 1), ("Diag", 10)), {"redundancy": True}, [1, 10]),
    (
        "резерв, ЦП II: синхронизируемая -> 4, полоса 5–13",
        T(("Main", 1), ("Diag", 2)),
        {"redundancy": True, "cpu_type": "II"},
        [4, 5],
    ),
    ("резерв, явная sync_task", T(("Fast", 0), ("Main", 3)), {"redundancy": True, "sync_task": "Main"}, [2, 1]),
    ("RegulBus OS, без резерва, 20 и 31", T(("Main", 20), ("Slow", 31)), {}, [2, 3]),
    (
        "вход Astra (niksosov): MAIN_TASK 1 sync, TASK_DIAGN 10",
        T(("MAIN_TASK", 1), ("TASK_DIAGN", 10)),
        {"redundancy": True, "sync_task": "MAIN_TASK"},
        [1, 10],
    ),
    ("один уровень вне полосы", T(("A", 31)), {}, [2]),
    ("ЦП II без резерва — обычная полоса", T(("A", 0), ("B", 1)), {"cpu_type": "II"}, [2, 3]),
]


@pytest.mark.parametrize(("label", "tasks", "kw", "want"), GOLDEN, ids=[g[0] for g in GOLDEN])
def test_task_priority_golden(label: str, tasks: list[TaskIn], kw: dict[str, object], want: list[int]) -> None:
    out = reassign(tasks, profiles.load_builtin(ASTRA), **kw)  # type: ignore[arg-type]
    assert [o.after for o in out] == want, label


def test_priority_collision_flag() -> None:
    out = reassign(T(*[(f"T{i:02d}", i * 2) for i in range(16)]), profiles.load_builtin(ASTRA))
    assert any(o.collision for o in out)


# --------------------------------------------------------------------------- модель трудоёмкости
def test_lcg_and_triangular_deterministic() -> None:
    a = [Lcg(20261019).random() for _ in range(3)]
    b = [Lcg(20261019).random() for _ in range(3)]
    assert a == b and all(0 <= x < 1 for x in a)
    assert triangular(0.0, 1, 2, 3) == 1
    assert triangular(1.0, 1, 2, 3) == pytest.approx(3)
    assert triangular(0.5, 5, 5, 5) == 5


def test_estimate_same_seed_same_numbers() -> None:
    fs = [Finding("C2A-LIB001", "todo", "ST", "m", "f", 1), Finding("C2A-IO001", "check", "DECL", "m", "f", 2)]
    e1 = estimate(fs, runs=2000)
    e2 = estimate(fs, runs=2000)
    assert (e1.p50_h, e1.p90_h) == (e2.p50_h, e2.p90_h)
    assert e1.p90_h >= e1.p50_h > 0
    assert e1.calibrated
