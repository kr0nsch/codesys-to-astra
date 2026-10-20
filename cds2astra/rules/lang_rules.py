"""Правила языков: LANG-IL0, LANG-IL (IL -> ST), LANG-SFC, LANG-GRAPH, SP20-LD."""

from __future__ import annotations

from .. import xmltree as X
from ..iltost import translate
from ..ir import st
from ..session import Session

BODY_KINDS = ("program", "functionBlock", "function", "action", "method", "get", "set", "transition")


def lang(s: Session) -> None:
    nl = s.project.doc.newline
    for pou in s.project.all_pous():
        body = pou.body
        if body is None or pou.kind not in BODY_KINDS:
            continue
        if pou.parent is not None and pou.parent.kind == "interface":
            continue
        line = body.elem.line if body.elem is not None else 0
        lng = body.language
        if lng == "ST" and body.code is not None and not body.code.text.strip() and pou.kind not in ("get", "set"):
            s.add(
                "C2A-LANG-IL0",
                "todo",
                "ST",
                f"{pou.path}: пустое тело ST — возможно, POU на IL экспортирован при выключенном IL; переэкспорт с IL",
                line,
                pou.path,
            )
        elif lng == "IL" and body.code is not None and body.lang_elem is not None:
            res = translate(body.code.text)
            if res.ok:
                original = st.comment_safe(body.code.text.rstrip())
                text = (
                    "// MIGRATION-CHECK(C2A-LANG-IL): тело переписано из IL в ST (cds2astra); исходный IL — ниже\n"
                    + res.st
                    + "(* исходный IL:\n"
                    + original
                    + "\n*)\n"
                )
                raw = s.project.doc.raw
                ls = raw.rfind(b"\n", 0, body.lang_elem.start) + 1
                indent = raw[ls : body.lang_elem.start].decode("utf-8", "replace")
                indent = indent if not indent.strip() else ""
                new = (
                    f'<ST>{nl}{indent}  <xhtml xmlns="{X.XHTML_NS}">'.encode()
                    + X.escape_text(text, nl)
                    + f"</xhtml>{nl}{indent}</ST>".encode()
                )
                s.replace_elem(body.lang_elem, new, "C2A-LANG-IL")
                s.add(
                    "C2A-LANG-IL",
                    "check",
                    "IL",
                    f"{pou.path}: IL -> ST ({len(res.st.splitlines())} строк ST); импорт <IL> не работает (P4)",
                    line,
                    pou.path,
                    status_key="import.il",
                )
            else:
                first = res.unsupported[0]
                s.add(
                    "C2A-LANG-IL",
                    "todo",
                    "IL",
                    f"{pou.path}: IL не переведён (строка {first[0]}: {first[1]!r}) — импорт <IL> не работает (P4)",
                    line,
                    pou.path,
                    status_key="import.il",
                )
        elif lng == "SFC":
            s.add(
                "C2A-LANG-SFC",
                "check",
                "SFC",
                f"{pou.path}: SFC как есть; IecSfc и неявные переменные шагов сверить",
                line,
                pou.path,
                status_key="import.graphics",
            )
        elif lng in ("FBD", "LD", "CFC"):
            s.add(
                "C2A-LANG-GRAPH",
                "info",
                lng,
                f"{pou.path}: {lng} как есть ({len(body.refs)} ссылок, сетей {body.networks})",
                line,
                pou.path,
                status_key="import.graphics",
            )
        elif lng == "LD20":
            s.add(
                "C2A-SP20-LD",
                "todo",
                "LD",
                f"{pou.path}: новый LD SP20 ({body.vendor}) — перевести в классический LD/FBD или ST в исходной IDE",
                line,
                pou.path,
            )
        elif lng == "UNKNOWN":
            s.add(
                "C2A-SP20-LD",
                "todo",
                "LD",
                f"{pou.path}: тело в неизвестном формате ({body.vendor}) сохранено как есть",
                line,
                pou.path,
            )
