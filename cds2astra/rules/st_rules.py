"""Правила по текстам ST и объявлениям: LIB001, IO001, SP18/SP19, RET001, SYM001, PTR001, RED001, MARK, OOP."""

from __future__ import annotations

import re

from ..ir import st
from ..ir.model import Body, CodeText, GRef, Gvl, Pou, Var
from ..libmap import Entry
from ..session import Session, all_codes
from .common import GraphMarkers, lex

_KNS_MARK = re.compile(r"//\s*PORT:\s*\[")
_S7_MARK = re.compile(r"//\s*MIGRATION-(CHECK|TODO)\s*:")
_C2A_MARK = re.compile(r"MIGRATION-(CHECK|TODO)\(C2A-")
_ADDR_RE = re.compile(r"%([IQM])([XBWDL]?)(\*|\d+(?:\.\d+)*)", re.I)
_SIZE = {"X": 1, "B": 1, "W": 2, "D": 4, "L": 8, "": 1}
PARTIAL_BITS = {"B": 8, "W": 16, "D": 32, "L": 64}
PARTIAL_TYPES = {"B": "BYTE", "W": "WORD", "D": "DWORD", "L": "LWORD"}


# --------------------------------------------------------------------------- LIB001
def _apply_entry(
    s: Session, code: CodeText, start: int, end: int, name: str, entry: Entry | None, pou: str | None, lang: str
) -> None:
    line = code.line_of(start)
    if entry is None:
        s.marker(code, start, "TODO", "C2A-LIB001", f"{name}: нет строки в таблице замен (data/libmap)")
        s.add("C2A-LIB001", "todo", lang, f"{name}: нет строки в таблице замен", line, pou, data={"source": name})
        return
    data = {
        "source": name,
        "library": entry.library,
        "target": entry.target,
        "kind": entry.kind,
        "url": entry.source_url,
    }
    if entry.kind in ("map", "wrap") and entry.target:
        s.edit(code, start, end, entry.target, "C2A-LIB001")
        if entry.kind == "wrap":
            note = f" — {entry.note}" if entry.note else ""
            s.marker(code, start, "CHECK", "C2A-LIB001", f"{name} -> {entry.target} (AstraCompat){note}")
        s.add(
            "C2A-LIB001",
            entry.outcome,
            lang,
            f"{name} -> {entry.target} ({entry.kind})",
            line,
            pou,
            source_ref=entry.source_url,
            data=data,
        )
    else:
        note = f": {entry.note}" if entry.note else ""
        s.marker(code, start, "TODO", "C2A-LIB001", f"{name} — аналога в Astra.IDE нет{note}")
        s.add(
            "C2A-LIB001",
            "todo",
            lang,
            f"{name}: аналога нет ({entry.kind})",
            line,
            pou,
            source_ref=entry.source_url,
            data=data,
        )


def lib001(s: Session) -> None:
    ns_map = s.libmap.by_namespace()
    referenced = {s.libmap.vendor_library(lib.title) for lib in s.project.libraries} - {None}
    for code, pou, kind in all_codes(s.project):
        lang = "DECL" if kind == "decl" else ("IL" if kind == "il" else "ST")
        owner = pou.path if pou else code.owner
        t = lex(code)
        n = len(t.sig)
        j = 0
        while j < n:
            tok = t.at(j)
            assert tok is not None
            prev = t.at(j - 1)
            if tok.kind == st.TK_IDENT and not (prev is not None and prev.kind == st.TK_OP and prev.text == "."):
                dot, nxt = t.at(j + 1), t.at(j + 2)
                if (
                    dot is not None
                    and nxt is not None
                    and dot.kind == st.TK_OP
                    and dot.text == "."
                    and nxt.kind == st.TK_IDENT
                    and tok.text.lower() in ns_map
                ):
                    lib = ns_map[tok.text.lower()]
                    entry = s.libmap.find(lib, nxt.text)
                    _apply_entry(s, code, tok.pos, nxt.end, f"{tok.text}.{nxt.text}", entry, owner, lang)
                    j += 3
                    continue
                if referenced:
                    entry = s.libmap.find_unqualified(tok.text)
                    after = t.at(j + 1)
                    is_call = after is not None and after.kind == st.TK_OP and after.text == "("
                    is_type = kind == "decl" and prev is not None and prev.kind == st.TK_OP and prev.text == ":"
                    if entry is not None and entry.library in referenced and (is_call or is_type):
                        _apply_entry(s, code, tok.pos, tok.end, tok.text, entry, owner, lang)
            j += 1
    _lib001_graphics(s, ns_map)


def _lib001_graphics(s: Session, ns_map: dict[str, str]) -> None:
    gm: GraphMarkers = s.__dict__.setdefault("_gm", GraphMarkers())
    for pou in s.project.all_pous():
        body = pou.body
        if body is None or not body.refs:
            continue
        lang = body.language if body.language in ("FBD", "LD", "CFC", "SFC") else "FBD"
        for ref in body.refs:
            if ref.kind != "block" or "." not in ref.name:
                continue
            ns, _, name = ref.name.partition(".")
            if ns.lower() not in ns_map:
                continue
            entry = s.libmap.find(ns_map[ns.lower()], name)
            line = ref.elem.line
            if entry is not None and entry.kind in ("map", "wrap") and entry.target:
                s.set_attr(ref.elem, "typeName", entry.target, "C2A-LIB001")
                _rename_return_pin(s, body, ref, name, entry.target)
                if entry.kind == "wrap":
                    gm.add(s, body, ref, "CHECK", "C2A-LIB001", f"{ref.name} -> {entry.target} (AstraCompat)")
                s.add(
                    "C2A-LIB001",
                    entry.outcome,
                    lang,
                    f"{ref.name} -> {entry.target} ({entry.kind}, typeName)",
                    line,
                    pou.path,
                    local_id=ref.local_id,
                    source_ref=entry.source_url,
                    data={
                        "source": ref.name,
                        "library": entry.library,
                        "target": entry.target,
                        "kind": entry.kind,
                        "url": entry.source_url,
                        "network": ref.network,
                    },
                )
            else:
                net = f" (сеть {ref.network})" if ref.network is not None else ""
                gm.add(s, body, ref, "TODO", "C2A-LIB001", f"{ref.name} — аналога нет{net}")
                s.add(
                    "C2A-LIB001",
                    "todo",
                    lang,
                    f"{ref.name}: аналога нет{net}",
                    line,
                    pou.path,
                    local_id=ref.local_id,
                    data={"source": ref.name, "network": ref.network},
                )


def _rename_return_pin(s: Session, body: Body, ref: GRef, old: str, new: str) -> None:
    """Выход-результат функции в графике назван именем функции (formalParameter="WORD_TO_HEX_STR"): при замене
    typeName он переименовывается вместе с соединениями на него (проба: C0038 в обеих IDE без этого)."""
    lid = ref.local_id
    for var in ref.elem.iter("variable"):
        if var.parent is not None and var.parent.tag == "outputVariables" and var.attrs.get("formalParameter") == old:
            s.set_attr(var, "formalParameter", new, "C2A-LIB001")
    root = body.lang_elem
    if root is None or lid is None:
        return
    for conn in root.iter("connection"):
        if conn.attrs.get("refLocalId") == lid and conn.attrs.get("formalParameter") == old:
            s.set_attr(conn, "formalParameter", new, "C2A-LIB001")


# --------------------------------------------------------------------------- IO001
def _addr_bytes(addr: str) -> int | None:
    m = _ADDR_RE.match(addr)
    if not m or m.group(3) == "*":
        return None
    size = m.group(2).upper()
    first = int(m.group(3).split(".")[0])
    width = _SIZE[size]
    return first * width + width


def io001(s: Session) -> None:
    gvl_io_names: set[str] = set()
    globals_: dict[str, str] = {}
    for gl in s.project.gvls:
        for gv in gl.vars:
            globals_.setdefault(gv.name.lower(), gl.name)
    if any(gl.name.lower() == "gvl_io" for gl in s.project.gvls):
        gvl_io_names = {gv.name.lower() for gl in s.project.gvls if gl.name.lower() == "gvl_io" for gv in gl.vars}
    marker_max = 0
    owners: list[tuple[Var, Gvl | None, Pou | None]] = []
    for gvl_obj in s.project.gvls:
        owners.extend((v, gvl_obj, None) for v in gvl_obj.vars if v.address)
    for pou_obj in s.project.all_pous():
        owners.extend((v, None, pou_obj) for v in pou_obj.vars if v.address)
    for v, g, p in owners:
        addr = v.address or ""
        area = addr[1:2].upper()
        owner_name = g.name if g else (p.path if p else "?")
        if area == "M":
            size = _addr_bytes(addr)
            if size:
                marker_max = max(marker_max, size)
            s.add(
                "C2A-IO001",
                "info",
                "DECL",
                f"{owner_name}.{v.name} AT {addr}: память %M на REGUL есть, AT остаётся",
                v.line,
                owner_name,
                status_key="memory.marker",
            )
            continue
        if g is not None and g.name.lower() == "gvl_io":
            continue
        in_fb = p is not None and p.kind in ("functionBlock", "function", "method")
        conflict = v.name.lower() in gvl_io_names or (p is not None and v.name.lower() in globals_)
        if in_fb or conflict or "*" in addr:
            why = "AT внутри ФБ/функции (%I*/%Q*)" if in_fb or "*" in addr else "конфликт имён с глобальными"
            if v.code is not None and v.decl_span is not None:
                s.marker(v.code, v.decl_span[0], "TODO", "C2A-IO001", f"{v.name} AT {addr}: {why} — привязать вручную")
            s.add("C2A-IO001", "todo", "DECL", f"{owner_name}.{v.name} AT {addr}: {why}", v.line, owner_name)
            continue
        init = f" := {v.init}" if v.init else ""
        s.gvl_io.append(f"    {v.name} : {v.type_text}{init}; // было: AT {addr} в {owner_name}")
        gvl_io_names.add(v.name.lower())
        direction = "вход" if area == "I" else "выход"
        s.io_map.append(
            {
                "source": f"{owner_name}.{v.name}",
                "variable": f"GVL_IO.{v.name}",
                "type": v.type_text,
                "owen": f"AT {addr}",
                "direction": direction,
                "regul": "канал модуля REGUL по мастеру конфигурации",
                "outcome": "check",
                "rule": "C2A-IO001",
            }
        )
        if v.code is not None and v.decl_span is not None:
            a, b = v.decl_span
            text = v.code.text
            ls = st.line_start(text, a)
            le = text.find("\n", b)
            le = len(text) if le < 0 else le + 1
            whole_line = (text[ls:a].strip() == "" and text[b:le].strip().startswith(("//", "(*"))) or text[
                b:le
            ].strip() == ""
            if whole_line:
                s.edit(v.code, ls, le, "", "C2A-IO001")
            else:
                s.edit(v.code, a, b, "", "C2A-IO001")
            if v.elem is None:
                _drop_structured_variable(s, g, p, v.name)
        elif v.elem is not None:
            s.set_attr(v.elem, "address", None, "C2A-IO001")
        s.renames[f"{owner_name.lower()}.{v.name.lower()}"] = f"GVL_IO.{v.name}"
        s.add(
            "C2A-IO001",
            "check",
            "DECL",
            f"{owner_name}.{v.name} AT {addr} -> GVL_IO.{v.name} (привязка по io-map)",
            v.line,
            owner_name,
            status_key="memory.input",
        )
    limit = s.target.value("memory.marker", 131072)
    if marker_max > int(limit):
        s.add(
            "C2A-IO001",
            "check",
            "PROJECT",
            f"%M занимает {marker_max} Б при {limit} Б на R500",
            0,
            None,
            status_key="memory.marker",
        )
    _apply_renames(s)


def _drop_structured_variable(s: Session, g: Gvl | None, p: Pou | None, name: str) -> None:
    """Структурная часть TC6 (<variable>) рядом с текстом объявления — убрать вместе с ним."""
    el = g.elem if g is not None else (p.elem if p is not None else None)
    if el is None:
        return
    raw = s.project.doc.raw
    for var in el.iter("variable"):
        if var.attrs.get("name", "").lower() == name.lower() and var.parent is not None and var.parent.tag != "struct":
            if var.parent.tag in ("globalVars", "localVars", "inputVars", "outputVars", "inOutVars", "tempVars"):
                ls = raw.rfind(b"\n", 0, var.start) + 1
                start = ls if raw[ls : var.start].strip() == b"" else var.start
                end = var.end
                if raw[end : end + 2] == b"\r\n":
                    pass
                s.byte_edits.append(
                    __import__("cds2astra.session", fromlist=["ByteEdit"]).ByteEdit(start, end, b"", "C2A-IO001")
                )
            break


def _apply_renames(s: Session) -> None:
    if not s.renames:
        return
    for code, _pou, _kind in all_codes(s.project):
        t = lex(code)
        for j in range(len(t.sig) - 2):
            a, dot, b = t.at(j), t.at(j + 1), t.at(j + 2)
            assert a is not None and dot is not None and b is not None
            if a.kind == st.TK_IDENT and dot.kind == st.TK_OP and dot.text == "." and b.kind == st.TK_IDENT:
                key = f"{a.text.lower()}.{b.text.lower()}"
                new = s.renames.get(key)
                if new:
                    s.edit(code, a.pos, b.end, new, "C2A-IO001")
    for pou in s.project.all_pous():
        if pou.body is None:
            continue
        for ref in pou.body.refs:
            if ref.text_elem is not None:
                new = s.renames.get(ref.name.lower())
                if new:
                    s.set_text(ref.text_elem, new, "C2A-IO001")


# --------------------------------------------------------------------------- SP18 / SP19
def sp18_utf8(s: Session, sp18plus: bool) -> None:
    utf8_opt = s.options.utf8_strings
    flag_all = utf8_opt is True or (utf8_opt is None and sp18plus)
    for code, pou, kind in all_codes(s.project):
        owner = pou.path if pou else code.owner
        lang = "DECL" if kind == "decl" else "ST"
        for tok in st.tokenize(code.text):
            if tok.kind == st.TK_UTF8:
                literal = tok.text[tok.text.index("#") + 1 :]
                line = code.line_of(tok.pos)
                if literal.isascii():
                    s.edit(code, tok.pos, tok.end, literal, "C2A-SP18-UTF8")
                    s.add("C2A-SP18-UTF8", "auto", lang, f"UTF8#: префикс снят у ASCII-литерала {literal}", line, owner)
                else:
                    s.marker(code, tok.pos, "TODO", "C2A-SP18-UTF8", "UTF8#-литерал с не-ASCII: STRING 3.5.17 не UTF-8")
                    s.add("C2A-SP18-UTF8", "todo", lang, "UTF8#-литерал с не-ASCII символами", line, owner)
            elif tok.kind == st.TK_STRING and flag_all and not tok.text.isascii():
                line = code.line_of(tok.pos)
                s.marker(
                    code, tok.pos, "CHECK", "C2A-SP18-UTF8", "не-ASCII STRING: на Astra — WSTRING/CP1251 (kns R23)"
                )
                s.add(
                    "C2A-SP18-UTF8", "check", lang, "не-ASCII литерал STRING при UTF-8-строках источника", line, owner
                )


def sp18_generic(s: Session) -> None:
    for code, pou, kind in all_codes(s.project):
        owner = pou.path if pou else code.owner
        t = lex(code)
        for j in range(len(t.sig)):
            tok = t.at(j)
            assert tok is not None
            if tok.kind == st.TK_IDENT and tok.text.upper() == "VAR_GENERIC":
                s.marker(code, tok.pos, "TODO", "C2A-SP18-GEN", "VAR_GENERIC CONSTANT — с 3.5.18; развернуть в размеры")
                s.add("C2A-SP18-GEN", "todo", "DECL", "VAR_GENERIC CONSTANT", code.line_of(tok.pos), owner)
            elif kind == "decl" and tok.kind == st.TK_IDENT:
                lt, num, gt = t.at(j + 1), t.at(j + 2), t.at(j + 3)
                prev = t.at(j - 1)
                if (
                    lt is not None
                    and num is not None
                    and gt is not None
                    and prev is not None
                    and prev.kind == st.TK_OP
                    and prev.text == ":"
                    and lt.kind == st.TK_OP
                    and lt.text == "<"
                    and gt.kind == st.TK_OP
                    and gt.text == ">"
                ):
                    s.marker(
                        code, tok.pos, "TODO", "C2A-SP18-GEN", f"{tok.text}<{num.text}>: обобщённый экземпляр SP18"
                    )
                    s.add("C2A-SP18-GEN", "todo", "DECL", f"{tok.text}<{num.text}>", code.line_of(tok.pos), owner)


def sp19_bit(s: Session) -> None:
    for code, pou, kind in all_codes(s.project):
        if kind == "decl":
            continue
        owner = pou.path if pou else code.owner
        t = lex(code)
        for j in range(len(t.sig)):
            tok = t.at(j)
            assert tok is not None
            if tok.kind != st.TK_PARTIAL:
                continue
            dot = t.at(j - 1)
            base = t.at(j - 2)
            nxt = t.at(j + 1)
            line = code.line_of(tok.pos)
            if dot is None or base is None:
                continue
            letter = tok.text[1].upper()
            n = int(tok.text[2:])
            is_write = nxt is not None and nxt.kind == st.TK_OP and nxt.text in (":=", "R=", "S=")
            before = t.at(j - 3)
            nested = before is not None and before.kind == st.TK_OP and before.text == "."
            adr = False
            k = j - 3
            while k >= 0:
                tk = t.at(k)
                if (
                    tk is None
                    or tk.kind not in (st.TK_IDENT, st.TK_OP)
                    or (tk.kind == st.TK_OP and tk.text not in (".", "("))
                ):
                    break
                if tk.kind == st.TK_IDENT and tk.text.upper() == "ADR":
                    adr = True
                    break
                k -= 1
            if letter == "X" and not adr:
                s.edit(code, dot.pos, tok.end, f".{n}", "C2A-SP19-BIT")
                s.add("C2A-SP19-BIT", "auto", "ST", f".%X{n} -> .{n}", line, owner)
            elif is_write or nested or adr:
                why = "запись" if is_write else ("вложенный доступ" if nested else "ADR от частичного доступа")
                s.marker(code, tok.pos, "TODO", "C2A-SP19-BIT", f"{why} {tok.text}: переписать сдвигами и масками")
                s.add("C2A-SP19-BIT", "todo", "ST", f"{why} {tok.text}", line, owner)
            else:
                bits = PARTIAL_BITS[letter]
                typ = PARTIAL_TYPES[letter]
                shift = bits * n
                expr = f"TO_{typ}(SHR({base.text}, {shift}))" if shift else f"TO_{typ}({base.text})"
                s.edit(code, base.pos, tok.end, expr, "C2A-SP19-BIT")
                s.add("C2A-SP19-BIT", "auto", "ST", f"{base.text}.{tok.text} -> {expr}", line, owner)


# --------------------------------------------------------------------------- RET001 / SYM001 / PTR001 / RED001
def _retain_vars(s: Session) -> dict[str, Var]:
    out: dict[str, Var] = {}
    for g in s.project.gvls:
        for v in g.vars:
            if v.retain or v.persistent or g.persistent:
                out[v.name.lower()] = v
    return out


def ret001(s: Session) -> None:
    rv = _retain_vars(s)
    if not rv:
        return
    s.add(
        "C2A-RET001",
        "info",
        "DECL",
        f"RETAIN/PERSISTENT: {len(rv)} переменных; на REGUL RETAIN сбрасывается при загрузке, сохранение — "
        "saveretain/restoreretain («Оболочка ПЛК»)",
        0,
        None,
        status_key="memory.retain",
    )
    for code, pou, kind in all_codes(s.project):
        if kind != "body":
            continue
        t = lex(code)
        depth = 0
        for j in range(len(t.sig)):
            tok = t.at(j)
            assert tok is not None
            if tok.kind == st.TK_IDENT:
                up = tok.text.upper()
                if up in ("IF", "CASE", "WHILE", "FOR", "REPEAT"):
                    depth += 1
                elif up in ("END_IF", "END_CASE", "END_WHILE", "END_FOR", "END_REPEAT"):
                    depth = max(0, depth - 1)
            if depth == 0 and tok.kind == st.TK_IDENT and tok.text.lower() in rv:
                nxt = t.at(j + 1)
                prev = t.at(j - 1)
                qualified_ok = prev is None or prev.kind != st.TK_OP or prev.text != "."
                if nxt is not None and nxt.kind == st.TK_OP and nxt.text == ":=" and qualified_ok:
                    s.marker(
                        code,
                        tok.pos,
                        "CHECK",
                        "C2A-RET001",
                        f"запись RETAIN {tok.text} в каждом цикле: на REGUL — запись ФС при каждом изменении",
                    )
                    s.add(
                        "C2A-RET001",
                        "check",
                        "ST",
                        f"запись RETAIN {tok.text} в каждом цикле",
                        code.line_of(tok.pos),
                        pou.path if pou else None,
                        status_key="memory.retain",
                    )


def sym001(s: Session) -> None:
    for code, pou, kind in all_codes(s.project):
        if kind != "decl":
            continue
        text = code.text
        pou_symbol = re.search(r"\{\s*attribute\s+'symbol'", text, re.I) is not None
        owner = pou.path if pou else code.owner
        vars_ = pou.vars if pou is not None else next((g.vars for g in s.project.gvls if g.decl is code), [])
        for v in vars_:
            typ = v.type_text.upper()
            is_ptr = typ.startswith("POINTER TO") or typ.startswith("REFERENCE TO")
            marked = any("symbol" in a.lower() or "opc" in a.lower() for a in v.attributes)
            if is_ptr and (pou_symbol or marked):
                if v.decl_span:
                    s.marker(
                        code,
                        v.decl_span[0],
                        "CHECK",
                        "C2A-SYM001",
                        f"{v.name}: указатель/ссылка в символьной конфигурации запрещены с Astra.IDE 1.7.2.5",
                    )
                s.add(
                    "C2A-SYM001",
                    "check",
                    "DECL",
                    f"{owner}.{v.name}: {v.type_text} в символьной конфигурации",
                    v.line,
                    owner,
                    status_key="symbols.pointers_forbidden_since",
                )


def ptr001(s: Session) -> None:
    dword_vars: set[str] = set()
    for p in s.project.all_pous():
        for v in p.vars:
            if v.type_text.upper() in ("DWORD", "UDINT", "DINT"):
                dword_vars.add(v.name.lower())
    for g in s.project.gvls:
        for v in g.vars:
            if v.type_text.upper() in ("DWORD", "UDINT", "DINT"):
                dword_vars.add(v.name.lower())
    for code, pou, kind in all_codes(s.project):
        if kind != "body":
            continue
        t = lex(code)
        for j in range(len(t.sig)):
            tok = t.at(j)
            assert tok is not None
            if tok.kind != st.TK_IDENT:
                continue
            up = tok.text.upper()
            if up == "ADR":
                k = j - 1
                while k >= 0 and t.at(k) is not None and t.at(k).kind == st.TK_OP and t.at(k).text in ("(", "TO_DWORD"):  # type: ignore[union-attr]
                    k -= 1
                left = t.at(j - 2) if t.at(j - 1) is not None and t.at(j - 1).text == ":=" else None  # type: ignore[union-attr]
                if left is not None and left.kind == st.TK_IDENT and left.text.lower() in dword_vars:
                    s.marker(
                        code,
                        tok.pos,
                        "CHECK",
                        "C2A-PTR001",
                        "адрес в DWORD/UDINT: на x86 R500 разрядность указателя сверить (SIZEOF(POINTER))",
                    )
                    s.add(
                        "C2A-PTR001",
                        "check",
                        "ST",
                        f"адрес в {left.text}",
                        code.line_of(tok.pos),
                        pou.path if pou else None,
                        status_key="platform.pointer_size",
                    )
            elif up == "SIZEOF":
                nxt = t.at(j + 4)
                prv = t.at(j - 1)
                arith = (prv is not None and prv.kind == st.TK_OP and prv.text in ("+", "-", "*")) or (
                    nxt is not None and nxt.kind == st.TK_OP and nxt.text in ("+", "-", "*")
                )
                if arith:
                    s.marker(
                        code,
                        tok.pos,
                        "CHECK",
                        "C2A-PTR001",
                        "SIZEOF в смещении: pack-mode = 8 на R500 — сверить раскладку",
                    )
                    s.add(
                        "C2A-PTR001",
                        "check",
                        "ST",
                        "SIZEOF в арифметике смещений",
                        code.line_of(tok.pos),
                        pou.path if pou else None,
                        status_key="platform.pack_mode",
                    )


def red001(s: Session) -> None:
    if not s.spec.redundancy:
        return
    limit_key = "redundancy.sync_limit_type2" if s.spec.cpu_type == "II" else "redundancy.sync_limit_type13"
    total = 0
    sizes = {
        "BOOL": 1,
        "BYTE": 1,
        "SINT": 1,
        "USINT": 1,
        "INT": 2,
        "UINT": 2,
        "WORD": 2,
        "DINT": 4,
        "UDINT": 4,
        "DWORD": 4,
        "REAL": 4,
        "TIME": 4,
        "LREAL": 8,
        "LINT": 8,
        "ULINT": 8,
        "LWORD": 8,
        "LTIME": 8,
    }
    for g in s.project.gvls:
        for v in g.vars:
            typ = v.type_text.upper()
            total += sizes.get(typ, 4)
            if typ.startswith(("POINTER TO", "REFERENCE TO")):
                if v.code is not None and v.decl_span:
                    s.marker(
                        v.code,
                        v.decl_span[0],
                        "TODO",
                        "C2A-RED001",
                        f"{v.name}: указатель в синхронизируемых данных резервирования запрещён",
                    )
                s.add(
                    "C2A-RED001",
                    "todo",
                    "DECL",
                    f"{g.name}.{v.name}: {v.type_text} в синхронизируемых данных",
                    v.line,
                    g.name,
                    status_key="redundancy.pointers_forbidden",
                )
    limit = int(s.target.value(limit_key, 512000))
    s.add(
        "C2A-RED001",
        "info",
        "PROJECT",
        f"глобальные данные ≈ {total} Б (оценка по типам) при лимите {limit} Б",
        0,
        None,
        status_key=limit_key,
        data={"bytes": total, "limit": limit},
    )


# --------------------------------------------------------------------------- MARK / OOP
def mark(s: Session) -> None:
    for code, pou, _kind in all_codes(s.project):
        for i, line in enumerate(code.text.split("\n")):
            kind = None
            if _KNS_MARK.search(line):
                kind = "kns"
            elif _S7_MARK.search(line):
                kind = "s7conv"
            elif _C2A_MARK.search(line):
                s.existing_markers += 1
                continue
            if kind:
                s.add(
                    "C2A-MARK",
                    "info",
                    "ST",
                    f"маркер {kind} во входе: {line.strip()[:100]}",
                    code.elem.line + i,
                    pou.path if pou else code.owner,
                    data={"marker": kind},
                )


OOP_FLAGS = {
    "EXTENDS": "oop.extends",
    "SUPER^": "oop.super",
    "ABSTRACT": "oop.abstract",
    "PRIVATE": "oop.access",
    "PROTECTED": "oop.access",
    "INTERNAL": "oop.access",
}


def oop(s: Session) -> None:
    for code, pou, kind in all_codes(s.project):
        t = lex(code)
        for j in range(len(t.sig)):
            tok = t.at(j)
            assert tok is not None
            if tok.kind != st.TK_IDENT:
                continue
            up = tok.text.upper()
            key = None
            nxt = t.at(j + 1)
            if up == "SUPER" and nxt is not None and nxt.text == "^":
                key = "oop.super"
                up = "SUPER^"
            elif up in OOP_FLAGS and kind == "decl":
                key = OOP_FLAGS[up]
            if key is None:
                continue
            if s.target.status(key) == "unknown":
                s.marker(
                    code, tok.pos, "CHECK", "C2A-LANG-OOP", f"{up}: поддержка в Astra.IDE не подтверждена (проба P8)"
                )
                s.add(
                    "C2A-LANG-OOP",
                    "check",
                    "DECL" if kind == "decl" else "ST",
                    f"{up}: флаг {key} unknown",
                    code.line_of(tok.pos),
                    pou.path if pou else None,
                    status_key=key,
                )
