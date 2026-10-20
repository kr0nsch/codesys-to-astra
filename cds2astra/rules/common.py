"""Общее для правил: обход токенов, графические маркеры, ссылки на POU."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import xmltree as X
from ..ir import st
from ..ir.model import Body, CodeText, GRef, Pou
from ..session import Session

NS_XHTML = X.XHTML_NS
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass
class Tok:
    tokens: list[st.Token]
    sig: list[int]

    def at(self, j: int) -> st.Token | None:
        if 0 <= j < len(self.sig):
            return self.tokens[self.sig[j]]
        return None


def lex(code: CodeText) -> Tok:
    toks = st.tokenize(code.text)
    return Tok(toks, st.significant(toks))


def language_of(pou: Pou | None, kind: str) -> str:
    if kind == "decl":
        return "DECL"
    if kind == "il":
        return "IL"
    return "ST"


def graph_language(body: Body) -> str:
    lang = body.language
    return lang if lang in ("FBD", "LD", "CFC", "SFC") else "FBD"


class GraphMarkers:
    """Маркеры в графических телах: TC6-элемент comment перед элементом (FBD/LD/CFC/SFC)."""

    def __init__(self) -> None:
        self._next: dict[int, int] = {}

    def _local_id(self, body: Body, ref: GRef) -> str:
        root = body.lang_elem
        key = id(root)
        if key not in self._next:
            ids = []
            if root is not None:
                for el in root.iter():
                    lid = el.attrs.get("localId")
                    if lid and lid.isdigit() and int(lid) < 2_000_000_000:
                        ids.append(int(lid))
            self._next[key] = (max(ids) if ids else 0) + 1
        if ref.network is not None and ref.local_id and len(ref.local_id) > 10:
            # сеть FBD/LD: localId внутри диапазона сети (сеть·10^10 + номер)
            base = ref.network * 10**10 + 9_000_000_000
            value = base + self._next[key]
        else:
            value = self._next[key]
        self._next[key] += 1
        return str(value)

    def add(self, s: Session, body: Body, ref: GRef, level: str, rule: str, message: str) -> None:
        raw = s.project.doc.raw
        line_start = raw.rfind(b"\n", 0, ref.elem.start) + 1
        indent = raw[line_start : ref.elem.start].decode("utf-8", "replace")
        if indent.strip():
            indent = ""
        text = X.escape_text(f"MIGRATION-{level}({rule}): {message}").decode("utf-8")
        nl = s.project.doc.newline
        lid = self._local_id(body, ref)
        block = (
            f'<comment localId="{lid}" height="0" width="0">{nl}'
            f'{indent}  <position x="0" y="0" />{nl}'
            f"{indent}  <content>{nl}"
            f'{indent}    <xhtml xmlns="{NS_XHTML}">{text}</xhtml>{nl}'
            f"{indent}  </content>{nl}"
            f"{indent}</comment>{nl}{indent}"
        )
        s.insert_before(ref.elem, block.encode("utf-8"), rule)


def is_ident(text: str) -> bool:
    return bool(_IDENT_RE.match(text))
