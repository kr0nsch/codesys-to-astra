"""Лексер ST без потерь и правки по диапазонам токенов.

Основа — лексер раскладки `stlayout.tokenize` (вложенные комментарии `(* (* *) *)`, `//`, `/* */`,
прагмы `{...}`, строки с `$`, типизированные литералы `T#5s`, `16#FF`, `%`-адреса). Поверх него
склеиваются конструкции SP18+: `UTF8#'…'` — один токен `utf8`, частичный доступ к битам
`.%X3`/`.%B0`/`.%W1`/`.%D0`/`.%L0` — токен `partial` (точка остаётся отдельным оператором).
Склейка токенов в исходный текст даёт его побайтно (тест-свойство).

Правки: `Edit(start, end, text, rule)` в символах текста. Пересекающиеся правки не применяются:
`apply_edits` возвращает их как конфликты (правило ставит `todo`).
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..importers.layout import stlayout as L

Token = L.Token
TK_IDENT = L.TK_IDENT
TK_OP = L.TK_OP
TK_STRING = L.TK_STRING
TK_WSTRING = L.TK_WSTRING
TK_TYPED = L.TK_TYPED
TK_ADDRESS = L.TK_ADDRESS
TK_NUMBER = L.TK_NUMBER
TK_COMMENT = L.TK_COMMENT
TK_PRAGMA = L.TK_PRAGMA
TK_WS = L.TK_WS
TK_UTF8 = "utf8"
TK_PARTIAL = "partial"
TRIVIA = (TK_WS, TK_COMMENT, TK_PRAGMA)

_PARTIAL_RE = re.compile(r"[XBWDLxbwdl][0-9]+\Z")


def tokenize(text: str) -> list[Token]:
    """Токены без потерь; `''.join(t.text for t in tokenize(s)) == s`."""
    raw = L.tokenize(text)
    out: list[Token] = []
    i = 0
    n = len(raw)
    while i < n:
        tok = raw[i]
        # UTF8#'...' (SP18): ident UTF8, оператор #, строка
        if (
            tok.kind == TK_IDENT
            and tok.text.upper() == "UTF8"
            and i + 2 < n
            and raw[i + 1].kind == TK_OP
            and raw[i + 1].text == "#"
            and raw[i + 2].kind in (TK_STRING, TK_WSTRING)
        ):
            text_ = tok.text + "#" + raw[i + 2].text
            out.append(Token(TK_UTF8, text_, tok.pos, tok.line, tok.col))
            i += 3
            continue
        # .%X3 / .%B0 (SP19): после точки — оператор % и ident X3
        if (
            tok.kind == TK_OP
            and tok.text == "%"
            and out
            and out[-1].kind == TK_OP
            and out[-1].text == "."
            and i + 1 < n
            and raw[i + 1].kind == TK_IDENT
            and _PARTIAL_RE.match(raw[i + 1].text)
        ):
            out.append(Token(TK_PARTIAL, "%" + raw[i + 1].text, tok.pos, tok.line, tok.col))
            i += 2
            continue
        out.append(tok)
        i += 1
    return out


def significant(tokens: Sequence[Token]) -> list[int]:
    return [i for i, t in enumerate(tokens) if t.kind not in TRIVIA]


def is_ident(tok: Token, *words: str) -> bool:
    return tok.kind == TK_IDENT and (not words or tok.text.upper() in words)


@dataclass(frozen=True)
class Edit:
    """Правка текста: заменить символы [start, end) на text. rule — ID правила."""

    start: int
    end: int
    text: str
    rule: str


def apply_edits(text: str, edits: Sequence[Edit]) -> tuple[str, list[Edit], list[Edit]]:
    """Применить непересекающиеся правки. Возвращает (текст, применённые, конфликтные).

    Порядок правок во входе не влияет на результат: правки сортируются по (start, end, rule, text);
    при пересечении обе правки конфликта не применяются (детерминированно).
    """
    ordered = sorted(set(edits), key=lambda e: (e.start, e.end, e.rule, e.text))
    conflicts: set[Edit] = set()
    for a, b in itertools.pairwise(ordered):
        if b.start < a.end or (a.start == a.end == b.start == b.end and a != b):
            conflicts.add(a)
            conflicts.add(b)
    applied = [e for e in ordered if e not in conflicts]
    out: list[str] = []
    pos = 0
    for e in applied:
        out.append(text[pos : e.start])
        out.append(e.text)
        pos = e.end
    out.append(text[pos:])
    return "".join(out), applied, sorted(conflicts, key=lambda e: (e.start, e.end, e.rule))


def line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def line_indent(text: str, pos: int) -> str:
    start = line_start(text, pos)
    i = start
    while i < len(text) and text[i] in " \t":
        i += 1
    return text[start:i]


def comment_safe(text: str) -> str:
    """Текст для вставки внутрь (* *): закрывающая скобка комментария разбивается."""
    return text.replace("*)", "* )").replace("(*", "( *")


def parse_var_blocks(text: str) -> list[L.VarBlock]:
    return L.parse_var_blocks(text)


def parse_header(text: str) -> L.DeclHeader | None:
    return L.parse_header(text)
