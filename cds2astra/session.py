"""Сеанс переноса: IR, профили, таблица замен и накопитель правок и находок.

Правки бывают трёх видов, и все сводятся к байтовым сшивкам исходного файла:
- текстовые (`edit`, `marker`) — внутри текста ST/IL/объявления; символы переводятся в байты по карте
  `TextMap`, заменяемый текст экранируется как у CODESYS;
- правки объявления (`edit_decl`) — одна правка для всех копий текста объявления (CODESYS кладёт
  `interfaceasplaintext` в несколько списков переменных одного POU);
- элементные (`replace_elem`, `insert_before`, `set_attr`).
Пересекающиеся правки не применяются и дают находку `todo` (C2A-EDIT).
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import xmltree as X
from .findings import Finding
from .ir import st
from .ir.model import CodeText, Pou, Project
from .libmap import LibMap
from .profiles import Profile

MARK_RE = re.compile(r"MIGRATION-(CHECK|TODO)\((C2A-[A-Z0-9-]+)\)")


@dataclass(frozen=True)
class ByteEdit:
    start: int
    end: int
    data: bytes
    rule: str


@dataclass
class TargetSpec:
    """Цель: ЦП и его тип, шина, резервирование, синхронизируемая задача, «-W»."""

    cpu: str = "REGUL R500 61"
    cpu_type: str = "I"  # I | II | III
    bus: str = "RegulBus OS"
    redundancy: bool = False
    sync_task: str | None = None
    webvisu: bool = False
    crates: int = 1
    bus_cycle_ms: float = 1.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TargetSpec:
        ts = cls()
        for k in ("cpu", "cpu_type", "bus", "sync_task"):
            if k in d:
                setattr(ts, k, str(d[k]))
        for k in ("redundancy", "webvisu"):
            if k in d:
                setattr(ts, k, bool(d[k]))
        if "crates" in d:
            ts.crates = int(d["crates"])
        if "bus_cycle_ms" in d:
            ts.bus_cycle_ms = float(d["bus_cycle_ms"])
        if ts.cpu_type not in ("I", "II", "III"):
            raise ValueError(f"target-spec: cpu_type {ts.cpu_type!r} — I, II или III")
        return ts


@dataclass
class Options:
    mode: str = "astra"  # astra | preserve
    form: str = "pous"  # pous | resource
    namespace: str = "tc6_0200"
    io: str = "keep-modbus"  # keep-modbus | local
    utf8_strings: bool | None = None  # --source-option utf8-strings; None — не указано
    source_date: str = "1970-01-01T00:00:00"


@dataclass
class TraceEntry:
    target: str  # объект/строка цели
    source: str  # объект источника
    line: int
    rules: list[str]


@dataclass
class Session:
    project: Project
    target: Profile
    sources: list[Profile]
    libmap: LibMap
    spec: TargetSpec = field(default_factory=TargetSpec)
    options: Options = field(default_factory=Options)
    io_list: dict[str, Any] | None = None
    findings: list[Finding] = field(default_factory=list)
    _text_edits: dict[int, tuple[CodeText, list[st.Edit]]] = field(default_factory=dict)
    _decl_groups: dict[int, list[CodeText]] = field(default_factory=dict)
    _markers: dict[tuple[int, int], tuple[CodeText, list[str]]] = field(default_factory=dict)
    byte_edits: list[ByteEdit] = field(default_factory=list)
    # новые объекты режима astra
    gvl_io: list[str] = field(default_factory=list)  # строки объявлений GVL_IO
    io_update_decl: list[str] = field(default_factory=list)  # VAR PRG_C2aIoUpdate
    io_update_body: list[str] = field(default_factory=list)  # тело PRG_C2aIoUpdate
    io_map: list[dict[str, Any]] = field(default_factory=list)
    task_table: list[dict[str, Any]] = field(default_factory=list)
    libraries_out: list[dict[str, str]] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)
    renames: dict[str, str] = field(default_factory=dict)  # GVL_X.var -> GVL_IO.var (нижний регистр ключа)
    existing_markers: int = 0
    dropped_objects: set[int] = field(default_factory=set)  # id(Elem) объектов, не попадающих в выход
    replaced_bodies: dict[int, bytes] = field(default_factory=dict)  # id(<body>) -> новые байты тела
    notes: list[str] = field(default_factory=list)

    # -- находки -------------------------------------------------------------
    def add(
        self,
        rule: str,
        outcome: str,
        language: str,
        message: str,
        line: int = 0,
        pou: str | None = None,
        *,
        column: int = 0,
        local_id: str | None = None,
        status_key: str | None = None,
        source_ref: str = "",
        data: dict[str, Any] | None = None,
    ) -> Finding:
        described = True
        if status_key is not None:
            described = self.target.described(status_key)
        f = Finding(
            rule,
            outcome,
            language,
            message,
            self.project.file,
            line,
            column,
            pou,
            local_id,
            described,
            source_ref=source_ref,
            data=dict(data or {}),
        )
        self.findings.append(f)
        return f

    # -- текстовые правки ----------------------------------------------------
    def edit(self, code: CodeText, start: int, end: int, text: str, rule: str) -> None:
        group = self._decl_groups.get(id(code))
        targets = group if group else [code]
        for ct in targets:
            slot = self._text_edits.setdefault(id(ct), (ct, []))
            slot[1].append(st.Edit(start, end, text, rule))

    def register_decl_copies(self, copies: Sequence[CodeText]) -> None:
        """Копии одного текста объявления правятся вместе (если тексты совпадают)."""
        if len(copies) < 2:
            return
        primary = copies[0]
        same = [c for c in copies if c.text == primary.text]
        for c in same:
            self._decl_groups[id(c)] = same

    def has_marker(self, code: CodeText, pos: int, rule: str) -> bool:
        text = code.text
        ls = st.line_start(text, pos)
        # подряд идущие строки маркеров над оператором
        cur = ls
        while cur > 0:
            prev = st.line_start(text, cur - 1)
            line = text[prev : cur - 1].strip()
            if not line.startswith("// MIGRATION-"):
                break
            if f"({rule})" in line:
                return True
            cur = prev
        return False

    def marker(self, code: CodeText, pos: int, level: str, rule: str, message: str) -> None:
        """Строка `// MIGRATION-CHECK(ID): …` перед строкой с pos (повторно не ставится).

        Маркеры одной строки собираются в одну вставку: две вставки в одну точку — конфликт правок.
        """
        pos = statement_start(code.text, pos)
        if self.has_marker(code, pos, rule):
            return
        text = code.text
        ls = st.line_start(text, pos)
        indent = st.line_indent(text, pos)
        body = message.replace("\n", " ")
        line = f"{indent}// MIGRATION-{level}({rule}): {body}\n"
        for ct in self._decl_groups.get(id(code)) or [code]:
            slot = self._markers.setdefault((id(ct), ls), (ct, []))
            if line not in slot[1]:
                slot[1].append(line)

    # -- элементные правки ---------------------------------------------------
    def replace_elem(self, el: X.Elem, data: bytes, rule: str) -> None:
        self.byte_edits.append(ByteEdit(el.start, el.end, data, rule))

    def insert_before(self, el: X.Elem, data: bytes, rule: str) -> None:
        self.byte_edits.append(ByteEdit(el.start, el.start, data, rule))

    def set_attr(self, el: X.Elem, name: str, value: str | None, rule: str) -> None:
        """Заменить (или удалить при value=None) значение атрибута в открывающем теге."""
        raw = self.project.doc.raw
        head = raw[el.start : el.head_end]
        m = re.search(rb"(\s+)" + re.escape(name.encode()) + rb'\s*=\s*(["\'])(.*?)\2', head, re.S)
        if m is None:
            if value is None:
                return
            pos = el.head_end - (2 if el.empty else 1)
            self.byte_edits.append(ByteEdit(pos, pos, f' {name}="{X.escape_attr(value)}"'.encode(), rule))
            return
        if value is None:
            self.byte_edits.append(ByteEdit(el.start + m.start(), el.start + m.end(), b"", rule))
        else:
            vs = el.start + m.start(3)
            ve = el.start + m.end(3)
            self.byte_edits.append(ByteEdit(vs, ve, X.escape_attr(value).encode(), rule))

    def set_text(self, el: X.Elem, text: str, rule: str) -> None:
        """Текст элемента без детей (expression, variable, Extends)."""
        self.byte_edits.append(ByteEdit(el.head_end, el.tail_start, X.escape_text(text), rule))

    # -- сведение ------------------------------------------------------------
    def resolve(self) -> list[ByteEdit]:
        """Все правки -> байтовые сшивки; пересечения -> todo C2A-EDIT, правки не применяются."""
        out = list(self.byte_edits)
        nl = self.project.doc.newline
        for (_cid, ls), (ct, lines) in sorted(self._markers.items(), key=lambda kv: kv[0]):
            slot = self._text_edits.setdefault(id(ct), (ct, []))
            slot[1].append(st.Edit(ls, ls, "".join(lines), "MARKER"))
        self._markers.clear()
        for ct, edits in self._text_edits.values():
            _text, applied, conflicts = st.apply_edits(ct.text, edits)
            for c in conflicts:
                self.add(
                    "C2A-EDIT",
                    "todo",
                    "ST",
                    f"пересекающиеся правки ({c.rule}) в {ct.owner}: правка не применена",
                    ct.line_of(c.start),
                    ct.owner,
                )
            for e in applied:
                bs = ct.tmap.offsets[e.start]
                be = ct.tmap.offsets[e.end]
                out.append(ByteEdit(bs, be, X.escape_text(e.text, nl), e.rule))
        out = sorted(set(out), key=lambda b: (b.start, b.end, b.rule, b.data))
        bad: set[ByteEdit] = set()
        for a, b in itertools.pairwise(out):
            if b.start < a.end:
                bad.add(a)
                bad.add(b)
        for b in sorted(bad, key=lambda e: (e.start, e.rule)):
            line = self.project.doc.raw.count(b"\n", 0, b.start) + 1
            self.add("C2A-EDIT", "todo", "PROJECT", f"пересекающиеся байтовые правки ({b.rule})", line)
        return [b for b in out if b not in bad]


_BOUNDARY_WORDS = {
    "THEN",
    "ELSE",
    "DO",
    "REPEAT",
    "END_IF",
    "END_FOR",
    "END_WHILE",
    "END_REPEAT",
    "END_CASE",
    "END_VAR",
    "VAR",
    "VAR_INPUT",
    "VAR_OUTPUT",
    "VAR_IN_OUT",
    "VAR_GLOBAL",
    "VAR_TEMP",
    "VAR_STAT",
    "VAR_INST",
    "VAR_EXTERNAL",
    "CONSTANT",
    "RETAIN",
    "PERSISTENT",
    "STRUCT",
    "UNION",
}


def statement_start(text: str, pos: int) -> int:
    """Начало оператора или объявления, в котором стоит pos: маркер ставится перед ним, а не внутри
    многострочного выражения."""
    toks = st.tokenize(text)
    best = 0
    for i, tok in enumerate(toks):
        if tok.pos >= pos:
            break
        if tok.kind in st.TRIVIA:
            continue
        if (tok.kind == st.TK_OP and tok.text == ";") or (
            tok.kind == st.TK_IDENT and tok.text.upper() in _BOUNDARY_WORDS
        ):
            j = i + 1
            while j < len(toks) and toks[j].kind in st.TRIVIA:
                j += 1
            best = toks[j].pos if j < len(toks) else pos
    return min(best, pos)


def apply_bytes(raw: bytes, edits: Iterable[ByteEdit], start: int = 0, end: int | None = None) -> bytes:
    """Сшивка raw[start:end] с правками, целиком попадающими в диапазон."""
    stop = len(raw) if end is None else end
    parts: list[bytes] = []
    pos = start
    for e in sorted(edits, key=lambda b: (b.start, b.end)):
        if e.start < start or e.end > stop:
            continue
        if e.start < pos:
            continue
        parts.append(raw[pos : e.start])
        parts.append(e.data)
        pos = e.end
    parts.append(raw[pos:stop])
    return b"".join(parts)


def all_codes(project: Project) -> list[tuple[CodeText, Pou | None, str]]:
    """Все тексты: (CodeText, POU или None для GVL, вид body/decl/il)."""
    out: list[tuple[CodeText, Pou | None, str]] = []
    for pou in project.all_pous():
        if pou.decl is not None:
            out.append((pou.decl, pou, "decl"))
        if pou.body is not None and pou.body.code is not None:
            out.append((pou.body.code, pou, pou.body.code.kind))
    for g in project.gvls:
        if g.decl is not None:
            out.append((g.decl, None, "decl"))
    return out
