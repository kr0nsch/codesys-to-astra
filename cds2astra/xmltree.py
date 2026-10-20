"""Разбор XML без потерь: дерево элементов с байтовыми смещениями, строками и столбцами.

Основа импорта и эмиттера. `xml.parsers.expat` даёт для каждого элемента байтовое смещение начала
(`CurrentByteIndex`, с учётом BOM), по нему находятся границы открывающего и закрывающего тегов в
исходных байтах. Эмиттер правит файл сшивкой исходных байтов по этим смещениям: нетронутые узлы
копируются байт в байт, а пересериализация ElementTree (она меняет пространство имён по умолчанию на
`ns0:` и форму пустых элементов) не используется вовсе.

Безопасность: DTD, объявления сущностей и внешние сущности запрещены — документ с `<!DOCTYPE>`
отклоняется до разбора содержимого («billion laughs», XXE). Ссылки на стандартные сущности
(`&lt;`, `&#1071;`) разрешены.
"""

from __future__ import annotations

import xml.parsers.expat as expat
from collections.abc import Iterator
from dataclasses import dataclass, field

BOM = b"\xef\xbb\xbf"
XHTML_NS = "http://www.w3.org/1999/xhtml"


class XmlError(ValueError):
    """Ошибка разбора: файл не XML или повреждён. `line`/`column` — позиция (с 1)."""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        super().__init__(message)
        self.line = line
        self.column = column


class XmlSecurityError(XmlError):
    """Запрещённая конструкция: DTD, объявление сущности, внешняя сущность."""


@dataclass(eq=False)
class Elem:
    """Элемент: локальное имя, пространство имён, атрибуты и границы в исходных байтах.

    `start` — смещение `<`; `head_end` — сразу после `>` открывающего тега; `tail_start` — смещение
    `</` закрывающего тега (у пустого элемента `<a/>` равно `head_end`); `end` — сразу после `>`
    закрывающего тега. Строка и столбец — с 1.
    """

    tag: str
    ns: str
    attrs: dict[str, str]
    start: int
    line: int
    column: int
    parent: Elem | None = None
    head_end: int = 0
    tail_start: int = 0
    end: int = 0
    empty: bool = False
    children: list[Elem] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Текст элемента (только собственные символьные данные, без детей), сущности раскрыты."""
        return "".join(self.text_parts)

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    def child(self, tag: str) -> Elem | None:
        for c in self.children:
            if c.tag == tag:
                return c
        return None

    def kids(self, tag: str) -> list[Elem]:
        return [c for c in self.children if c.tag == tag]

    def iter(self, tag: str | None = None) -> Iterator[Elem]:
        """Обход в глубину (сам элемент и потомки) в порядке документа."""
        stack: list[Elem] = [self]
        while stack:
            node = stack.pop()
            if tag is None or node.tag == tag:
                yield node
            stack.extend(reversed(node.children))

    def path(self) -> str:
        parts: list[str] = []
        node: Elem | None = self
        while node is not None:
            label = node.tag
            name = node.attrs.get("name")
            if node.tag == "data" and name:
                label += f"[{name.rsplit('/', 1)[-1]}]"
            parts.append(label)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def data(self, suffix: str) -> Elem | None:
        """Первый `addData/data` с именем, оканчивающимся на suffix (`/pou`, `Device`, ...)."""
        add = self.child("addData")
        if add is None:
            return None
        for d in add.kids("data"):
            name = d.attrs.get("name", "")
            if name == suffix or name.endswith("/" + suffix):
                return d
        return None

    def datas(self, suffix: str) -> list[Elem]:
        add = self.child("addData")
        if add is None:
            return []
        out = []
        for d in add.kids("data"):
            name = d.attrs.get("name", "")
            if name == suffix or name.endswith("/" + suffix):
                out.append(d)
        return out


@dataclass
class Document:
    """Разобранный документ: исходные байты, корень, BOM, кодировка объявления."""

    raw: bytes
    root: Elem
    has_bom: bool
    newline: str  # "\r\n" или "\n" — преобладающий перевод строк исходника

    def slice(self, start: int, end: int) -> bytes:
        return self.raw[start:end]

    def content_raw(self, el: Elem) -> bytes:
        """Сырые байты содержимого элемента (между тегами)."""
        return self.raw[el.head_end : el.tail_start]


def _find_tag_end(raw: bytes, pos: int) -> int:
    """Смещение сразу после `>` тега, начинающегося в pos (кавычки в атрибутах учитываются)."""
    quote = 0
    n = len(raw)
    i = pos + 1
    while i < n:
        b = raw[i]
        if quote:
            if b == quote:
                quote = 0
        elif b in (0x22, 0x27):  # " '
            quote = b
        elif b == 0x3E:  # >
            return i + 1
        i += 1
    raise XmlError(f"не закрыт тег в позиции {pos}")


def _reject(*_args: object) -> None:
    raise XmlSecurityError("DTD и объявления сущностей запрещены (защита от billion laughs и XXE)")


def parse(raw: bytes) -> Document:
    """Разобрать XML (UTF-8, с BOM или без). Ошибки — XmlError / XmlSecurityError."""
    if not isinstance(raw, bytes | bytearray):
        raise TypeError("ожидаются байты")
    raw = bytes(raw)
    parser = expat.ParserCreate(namespace_separator=" ")
    parser.buffer_text = False
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    stack: list[Elem] = []
    roots: list[Elem] = []

    def on_start(name: str, attrs: dict[str, str]) -> None:
        if " " in name:
            ns, tag = name.split(" ", 1)
        else:
            ns, tag = "", name
        clean = {}
        for k, v in attrs.items():
            clean[k.split(" ", 1)[1] if " " in k else k] = v
        pos = parser.CurrentByteIndex
        el = Elem(tag, ns, clean, pos, parser.CurrentLineNumber, parser.CurrentColumnNumber + 1)
        el.head_end = _find_tag_end(raw, pos)
        el.empty = raw[el.head_end - 2 : el.head_end] == b"/>"
        if el.empty:
            el.tail_start = el.end = el.head_end
        if stack:
            el.parent = stack[-1]
            stack[-1].children.append(el)
        else:
            roots.append(el)
        stack.append(el)

    def on_end(_name: str) -> None:
        el = stack.pop()
        if not el.empty:
            pos = parser.CurrentByteIndex
            el.tail_start = pos
            el.end = _find_tag_end(raw, pos)

    def on_chars(data: str) -> None:
        if stack:
            stack[-1].text_parts.append(data)

    def on_external(*_args: object) -> int:
        raise XmlSecurityError("внешние сущности запрещены")

    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    parser.CharacterDataHandler = on_chars
    parser.StartDoctypeDeclHandler = _reject
    parser.EntityDeclHandler = _reject
    parser.UnparsedEntityDeclHandler = _reject
    parser.NotationDeclHandler = _reject
    parser.ExternalEntityRefHandler = on_external
    try:
        parser.Parse(raw, True)
    except expat.ExpatError as exc:
        raise XmlError(f"XML: {expat.errors.messages[exc.code]}", exc.lineno, exc.offset + 1) from exc
    if not roots:
        raise XmlError("пустой документ")
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n")
    newline = "\r\n" if crlf and crlf * 2 >= lf else "\n"
    return Document(raw, roots[0], raw.startswith(BOM), newline)


# ---------------------------------------------------------------------------
# Текст элемента: декодирование с картой смещений (для точечных правок внутри xhtml)
# ---------------------------------------------------------------------------

_NAMED = {"lt": "<", "gt": ">", "amp": "&", "quot": '"', "apos": "'"}


@dataclass
class TextMap:
    """Декодированный текст содержимого элемента и карта «позиция символа → байтовое смещение».

    `offsets[i]` — смещение (в исходных байтах документа) начала i-го символа текста; последний элемент —
    конец содержимого. Правка символов [a, b) текста — замена байтов [offsets[a], offsets[b]).
    """

    text: str
    offsets: list[int]


def text_map(doc: Document, el: Elem) -> TextMap:
    """Текст элемента без детей (xhtml тела ST) с картой смещений. CDATA, сущности, CRLF учитываются."""
    raw = doc.raw
    pos = el.head_end
    stop = el.tail_start
    chars: list[str] = []
    offs: list[int] = []
    while pos < stop:
        if raw.startswith(b"<![CDATA[", pos):
            end = raw.index(b"]]>", pos)
            seg = raw[pos + 9 : end].decode("utf-8")
            p = pos + 9
            for ch in seg:
                chars.append(ch)
                offs.append(p)
                p += len(ch.encode("utf-8"))
            pos = end + 3
            continue
        if raw[pos] == 0x3C:  # дочерний элемент или комментарий — текст только собственный
            if raw.startswith(b"<!--", pos):
                pos = raw.index(b"-->", pos) + 3
                continue
            raise XmlError("text_map: у элемента есть дочерние элементы")
        if raw[pos] == 0x26:  # &
            semi = raw.index(b";", pos)
            ref = raw[pos + 1 : semi].decode("ascii")
            if ref.startswith("#x") or ref.startswith("#X"):
                ch = chr(int(ref[2:], 16))
            elif ref.startswith("#"):
                ch = chr(int(ref[1:]))
            else:
                ch = _NAMED[ref]
            chars.append(ch)
            offs.append(pos)
            pos = semi + 1
            continue
        if raw[pos] == 0x0D:  # \r\n и одиночный \r -> \n (нормализация XML)
            chars.append("\n")
            offs.append(pos)
            pos += 2 if raw[pos + 1 : pos + 2] == b"\n" else 1
            continue
        b = raw[pos]
        width = 1 if b < 0x80 else 2 if b < 0xE0 else 3 if b < 0xF0 else 4
        chars.append(raw[pos : pos + width].decode("utf-8"))
        offs.append(pos)
        pos += width
    offs.append(stop)
    return TextMap("".join(chars), offs)


def escape_text(text: str, newline: str = "\n") -> bytes:
    """Текст -> байты содержимого элемента в стиле CODESYS (экранируются только & < >)."""
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if newline != "\n":
        out = out.replace("\n", newline)
    return out.encode("utf-8")


def escape_attr(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
