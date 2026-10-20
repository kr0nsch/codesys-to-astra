#!/usr/bin/env python3
"""Копия `tools/st_to_plcopen.py` из kr0nsch/kns-port-domestic @ 6262d0fdc065ceb9d891c1ac3ab150010dc75ef1
(MIT, тот же автор) — атрибуция в docs/ARCHITECTURE.md. Изменения копии: импорт раскладки из соседнего
`stlayout.py`, без загрузки XSD по сети и без командной строки (ядро cds2astra не ходит в сеть; схему
качает `tools/fetch_samples.py`). Остальной код не менялся.

Конвертер раскладки src/ в PLCopen XML (TC6 2.01, вариант CODESYS) и обратно.

Для сред на базе CODESYS V3.5, которые импортируют PLCopenXML: Astra.IDE (РегЛаб, ПЛК REGUL; основа —
CODESYS 3.5.17, исследование `_research/port/astra_ide.md`, факты F43–F47) и сам CODESYS 3.5.17.30.
Раскладка читается через `tools/codesys/stlayout.py` (контракт — docs/LAYOUT.md).

Что пишется (форма «объекты», как экспорт CODESYS выбранных объектов):

- `types/dataTypes` — структуры (`STRUCT`, `STRUCT EXTENDS`), перечисления (со значениями и базовым типом),
  псевдонимы (в том числе поддиапазоны и строки с длиной);
- `types/pous` — программы, функции, функциональные блоки: интерфейс по секциям `VAR*`, тело на ST;
  методы и свойства ФБ и программ — в расширении CODESYS `addData` (`.../plcopenxml/method`, `.../property`);
- `addData` проекта — списки глобальных переменных (`.../globalvars`), Persistent Variables (тот же элемент
  с `persistent="true"`), интерфейсы с методами и свойствами (`.../interface`), объединения (`.../union`),
  папки проекта (`.../projectstructure`).

Каждый объект дополнительно несёт исходный текст объявления (`.../interfaceasplaintext`, как экспорт CODESYS
с флагом «объявления как обычный текст»). Импорт CODESYS берёт этот текст, а не структурное описание,
поэтому объявления переносятся без потерь: комментарии, прагмы, `VAR_IN_OUT CONSTANT`, `ARRAY[*]`,
`VAR_INST`, `ABSTRACT`, модификаторы доступа. Структурная часть TC6 нужна для проверки по XSD и для сред,
которые читают только стандарт; `--no-plaintext` пишет только её. Чего в ней нет — README, раздел о PLCopen XML.

Пространство имён по умолчанию — `tc6_0201` (версия 2.01, файл проверяется официальной схемой без замен);
`--namespace tc6_0200` — как пишут экспорт CODESYS 3.5 и Astra.IDE. Импорт обоих вариантов в CODESYS 3.5.17.30
проверен скриптом `tools/plcopen/verify_codesys.py` (импорт, сборка, сравнение текстов, обратный экспорт).

Обратное направление (`--reverse`): PLCopen XML с текстами объявлений (наш файл или экспорт CODESYS/Astra.IDE
с флагом «объявления как обычный текст», в том числе экспорт приложения целиком) -> раскладка. Им же тесты
проверяют цикл раскладка -> XML -> раскладка.

Коды выхода: 0 — успех, 1 — ошибки раскладки, преобразования или проверки по XSD, 2 — неверные аргументы.
"""

from __future__ import annotations

import hashlib
import importlib
import re
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import stlayout as L

__version__ = "0.1.0"

PRODUCT_NAME = "cds2astra (layout, kns-port-domestic st_to_plcopen @ 6262d0f)"

NS_0200 = "http://www.plcopen.org/xml/tc6_0200"
NS_0201 = "http://www.plcopen.org/xml/tc6_0201"
NAMESPACES = {"tc6_0200": NS_0200, "tc6_0201": NS_0201}
NS_XHTML = "http://www.w3.org/1999/xhtml"

# Расширения CODESYS (имена data в addData) — проверены экспортом CODESYS 3.5.17.30
CDS = "http://www.3s-software.com/plcopenxml/"
CDS_PLAINTEXT = CDS + "interfaceasplaintext"
CDS_OBJECTID = CDS + "objectid"
CDS_ATTRIBUTES = CDS + "attributes"
CDS_GLOBALVARS = CDS + "globalvars"
CDS_MIXED = CDS + "mixedattrsvarlist"
CDS_INTERFACE = CDS + "interface"
CDS_UNION = CDS + "union"
CDS_METHOD = CDS + "method"
CDS_PROPERTY = CDS + "property"
CDS_POU_INHERITANCE = CDS + "pouinheritance"
CDS_DUT_INHERITANCE = CDS + "datatypeinheritance"
CDS_ACCESS = CDS + "accessmodifiers"
CDS_STRUCTURE = CDS + "projectstructure"

# Пространство имён UUID5 для детерминированных ObjectId (одинаковый вход — одинаковый XML)
_OBJECT_ID_NAMESPACE = uuid.UUID("5d3f6c1e-8a42-4b8e-9f1d-2c7a0b6e4d93")

DEFAULT_ACCESSOR_DECL = "VAR\nEND_VAR\n"  # объявление аксессора свойства ФБ без файла <P>.get.decl.st

ELEMENTARY_TYPES = frozenset(
    (
        "BOOL",
        "BYTE",
        "WORD",
        "DWORD",
        "LWORD",
        "SINT",
        "INT",
        "DINT",
        "LINT",
        "USINT",
        "UINT",
        "UDINT",
        "ULINT",
        "REAL",
        "LREAL",
        "TIME",
        "DATE",
        "DT",
        "TOD",
    )
)
TYPE_SYNONYMS = {"DATE_AND_TIME": "DT", "TIME_OF_DAY": "TOD"}
UNSIGNED_TYPES = frozenset(("USINT", "UINT", "UDINT", "ULINT", "BYTE", "WORD", "DWORD", "LWORD"))

# Секции VAR* -> списки переменных TC6 (VAR_STAT — как у CODESYS: globalVars; VAR_INST в TC6 нет)
VAR_LISTS = {
    "VAR": "localVars",
    "VAR_TEMP": "tempVars",
    "VAR_INPUT": "inputVars",
    "VAR_OUTPUT": "outputVars",
    "VAR_IN_OUT": "inOutVars",
    "VAR_EXTERNAL": "externalVars",
    "VAR_STAT": "globalVars",
}
VAR_FLAGS = {"CONSTANT": "constant", "RETAIN": "retain", "PERSISTENT": "persistent", "NON_RETAIN": "nonretain"}
ACCESS_FLAGS = {"PRIVATE": "Private", "PROTECTED": "Protected", "INTERNAL": "Internal", "FINAL": "Final"}
POU_TYPES = {L.POU_PROGRAM: "program", L.POU_FUNCTION: "function", L.POU_FUNCTION_BLOCK: "functionBlock"}

_INVALID_XML_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_ATTRIBUTE_RE = re.compile(r"^\{\s*attribute\s+'([^']*)'\s*(?::=\s*'([^']*)'\s*)?\}$", re.IGNORECASE | re.DOTALL)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


# ---------------------------------------------------------------------------
# Узлы XML и запись (свой писатель: пространства имён по умолчанию — как у CODESYS)
# ---------------------------------------------------------------------------


class Node:
    """Элемент XML: тег, атрибуты в порядке добавления, дети или текст (не то и другое)."""

    __slots__ = ("attrs", "children", "tag", "text")

    def __init__(self, tag: str, attrs: Sequence[tuple[str, str]] = (), text: str | None = None) -> None:
        self.tag = tag
        self.attrs = list(attrs)
        self.children: list[Node] = []
        self.text = text

    def add(self, tag: str, attrs: Sequence[tuple[str, str]] = (), text: str | None = None) -> Node:
        child = Node(tag, attrs, text)
        self.children.append(child)
        return child

    def append(self, child: Node) -> Node:
        self.children.append(child)
        return child


def _escape_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    return _escape_text(text).replace('"', "&quot;").replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;")


def _write_node(node: Node, depth: int, out: list[str]) -> None:
    pad = "  " * depth
    attrs = "".join(f' {name}="{_escape_attr(value)}"' for name, value in node.attrs)
    if node.text is not None:
        if node.text:
            out.append(f"{pad}<{node.tag}{attrs}>{_escape_text(node.text)}</{node.tag}>\n")
        else:
            out.append(f"{pad}<{node.tag}{attrs} />\n")
        return
    if not node.children:
        out.append(f"{pad}<{node.tag}{attrs} />\n")
        return
    out.append(f"{pad}<{node.tag}{attrs}>\n")
    for child in node.children:
        _write_node(child, depth + 1, out)
    out.append(f"{pad}</{node.tag}>\n")


def serialize(root: Node) -> str:
    """Текст XML: объявление, отступ 2 пробела, LF; текст xhtml (код ST) — без изменений."""
    out = ['<?xml version="1.0" encoding="utf-8"?>\n']
    _write_node(root, 0, out)
    return "".join(out)


def xhtml(text: str) -> Node:
    return Node("xhtml", [("xmlns", NS_XHTML)], text)


def plaintext_node(text: str) -> Node:
    """<InterfaceAsPlainText><xhtml>текст</xhtml></InterfaceAsPlainText> — исходный текст объявления."""
    node = Node("InterfaceAsPlainText")
    node.append(xhtml(text))
    return node


def data_node(name: str, handle: str = "implementation") -> Node:
    return Node("data", [("name", name), ("handleUnknown", handle)])


def st_body(text: str | None) -> Node:
    body = Node("body")
    body.add("ST").append(xhtml(text or ""))
    return body


# ---------------------------------------------------------------------------
# Замечания
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Issue:
    """Замечание преобразования: уровень (error, warning), путь исходника, текст."""

    severity: str
    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.severity}: {self.message}"


# ---------------------------------------------------------------------------
# Типы и начальные значения ST -> структуры TC6
# ---------------------------------------------------------------------------


def _sig_tokens(text: str) -> list[L.Token]:
    tokens = L.tokenize(text)
    return [tokens[i] for i in L.significant_indices(tokens)]


def _join(tokens: Sequence[L.Token]) -> str:
    """Текст последовательности значимых токенов с пробелами только там, где они нужны."""
    out = ""
    prev: L.Token | None = None
    for tok in tokens:
        if prev is not None and _needs_space(prev, tok):
            out += " "
        out += tok.text
        prev = tok
    return out


def _needs_space(prev: L.Token, tok: L.Token) -> bool:
    word_kinds = (L.TK_IDENT, L.TK_NUMBER, L.TK_TYPED, L.TK_ADDRESS)
    if tok.kind not in word_kinds:
        return False
    return prev.kind in word_kinds or prev.is_op(")", "]")


def _split_top(tokens: Sequence[L.Token], sep: str = ",") -> list[list[L.Token]]:
    """Делит токены по разделителю sep на верхнем уровне скобок."""
    parts: list[list[L.Token]] = [[]]
    depth = 0
    for tok in tokens:
        if tok.is_op("(", "["):
            depth += 1
        elif tok.is_op(")", "]"):
            depth -= 1
        if depth == 0 and tok.is_op(sep):
            parts.append([])
            continue
        parts[-1].append(tok)
    return parts


def _find_top(tokens: Sequence[L.Token], op: str) -> int:
    depth = 0
    for i, tok in enumerate(tokens):
        if tok.is_op("(", "["):
            depth += 1
        elif tok.is_op(")", "]"):
            depth -= 1
        elif depth == 0 and tok.is_op(op):
            return i
    return -1


def type_node(text: str, tag: str = "type") -> Node:
    """Элемент <type> (или baseType/returnType) для типа ST. Неразобранный тип — <derived name="текст"/>."""
    node = Node(tag)
    tokens = _sig_tokens(text)
    inner = _parse_type(tokens)
    node.append(inner if inner is not None else Node("derived", [("name", _join(tokens) or text)]))
    return node


def _parse_type(tokens: Sequence[L.Token]) -> Node | None:
    if not tokens:
        return None
    first = tokens[0]
    word = first.upper if first.kind == L.TK_IDENT else ""
    if word == "ARRAY":
        return _parse_array(tokens)
    if word == "POINTER" and len(tokens) > 2 and tokens[1].is_ident("TO"):
        base = _parse_type(tokens[2:])
        if base is None:
            return None
        node = Node("pointer")
        node.add("baseType").append(base)
        return node
    if word == "REFERENCE" and len(tokens) > 2 and tokens[1].is_ident("TO"):
        # в TC6 ссылок нет; так их пишет и экспорт CODESYS
        return Node("derived", [("name", "REFERENCE TO " + _join(tokens[2:]))])
    if word in ("STRING", "WSTRING"):
        tag = word.lower()
        if len(tokens) == 1:
            return Node(tag)
        if len(tokens) >= 3 and tokens[1].is_op("(", "[") and tokens[-1].is_op(")", "]"):
            return Node(tag, [("length", _join(tokens[2:-1]))])
        return None
    name = TYPE_SYNONYMS.get(word, word)
    if name in ELEMENTARY_TYPES:
        if len(tokens) == 1:
            return Node(name)
        if len(tokens) >= 5 and tokens[1].is_op("(") and tokens[-1].is_op(")"):
            range_tokens = list(tokens[2:-1])
            dots = _find_top(range_tokens, "..")
            if dots > 0:
                tag = "subrangeUnsigned" if name in UNSIGNED_TYPES else "subrangeSigned"
                node = Node(tag)
                node.add("range", [("lower", _join(range_tokens[:dots])), ("upper", _join(range_tokens[dots + 1 :]))])
                node.add("baseType").append(Node(name))
                return node
        return None
    if first.kind == L.TK_IDENT and all(t.kind == L.TK_IDENT or t.is_op(".") for t in tokens):
        return Node("derived", [("name", _join(tokens))])
    return None


def _parse_array(tokens: Sequence[L.Token]) -> Node | None:
    if len(tokens) < 5 or not tokens[1].is_op("["):
        return None
    depth = 0
    close = -1
    for i in range(1, len(tokens)):
        if tokens[i].is_op("(", "["):
            depth += 1
        elif tokens[i].is_op(")", "]"):
            depth -= 1
            if depth == 0:
                close = i
                break
    if close < 0 or close + 2 > len(tokens) - 1 or not tokens[close + 1].is_ident("OF"):
        return None
    dims = _split_top(tokens[2:close])
    if any(len(dim) == 1 and dim[0].is_op("*") for dim in dims):
        # ARRAY[*] (массив переменной длины): в TC6 такого нет — как REFERENCE TO, текстом в derived
        return Node("derived", [("name", _join(tokens))])
    node = Node("array")
    for dim in dims:
        dots = _find_top(dim, "..")
        if dots <= 0:
            return None
        node.add("dimension", [("lower", _join(dim[:dots])), ("upper", _join(dim[dots + 1 :]))])
    base = _parse_type(tokens[close + 2 :])
    if base is None:
        base = Node("derived", [("name", _join(tokens[close + 2 :]))])
    node.add("baseType").append(base)
    return node


def value_node(text: str, tag: str = "initialValue") -> Node:
    """Начальное значение: simpleValue, arrayValue ([...], повтор n(x)), structValue ((a := 1, ...))."""
    node = Node(tag)
    node.append(_value_content(_sig_tokens(text), text))
    return node


def _value_content(tokens: Sequence[L.Token], raw: str) -> Node:
    if len(tokens) >= 2 and tokens[0].is_op("[") and tokens[-1].is_op("]"):
        array = Node("arrayValue")
        for item in _split_top(tokens[1:-1]):
            if not item:
                continue
            value = Node("value")
            if (
                len(item) >= 4
                and item[0].kind == L.TK_NUMBER
                and item[1].is_op("(")
                and item[-1].is_op(")")
                and _find_top(item[1:], ",") < 0
            ):
                value.attrs.append(("repetitionValue", item[0].text))
                inner = item[2:-1]
                value.append(_value_content(inner, _join(inner)))
            else:
                value.append(_value_content(item, _join(item)))
            array.append(value)
        return array
    if len(tokens) >= 2 and tokens[0].is_op("(") and tokens[-1].is_op(")"):
        members = _split_top(tokens[1:-1])
        if members and all(len(m) >= 3 and m[0].kind == L.TK_IDENT and m[1].is_op(":=") for m in members):
            struct = Node("structValue")
            for member in members:
                value = struct.add("value", [("member", member[0].text)])
                value.append(_value_content(member[2:], _join(member[2:])))
            return struct
    text = _join(tokens) if tokens else raw.strip()
    return Node("simpleValue", [("value", text)])


# ---------------------------------------------------------------------------
# Комментарии и прагмы рядом с объявлениями
# ---------------------------------------------------------------------------


def _comment_body(text: str) -> str:
    if text.startswith("//"):
        return text[2:]
    if text.startswith("(*") and text.endswith("*)"):
        return text[2:-2]
    if text.startswith("/*") and text.endswith("*/"):
        return text[2:-2]
    return text


def _follows_code(tokens: Sequence[L.Token], index: int) -> bool:
    """Комментарий или прагма index стоит в строке после кода (хвост предыдущего объявления)."""
    i = index - 1
    while i >= 0 and tokens[i].kind == L.TK_WS and "\n" not in tokens[i].text:
        i -= 1
    if i < 0 or tokens[i].kind == L.TK_WS:
        return False
    if tokens[i].kind in (L.TK_COMMENT, L.TK_PRAGMA):
        return _follows_code(tokens, i)
    return True


def _leading_trivia(tokens: Sequence[L.Token], index: int) -> tuple[list[str], list[str]]:
    """Прагмы и комментарии непосредственно перед токеном index (до предыдущего значимого).

    Комментарий в конце строки предыдущего объявления (`a : INT; // про a`) к следующему не относится.
    """
    pragmas: list[str] = []
    comments: list[str] = []
    i = index - 1
    while i >= 0 and tokens[i].kind in (L.TK_WS, L.TK_COMMENT, L.TK_PRAGMA):
        tok = tokens[i]
        if tok.kind != L.TK_WS and _follows_code(tokens, i):
            break
        if tok.kind == L.TK_PRAGMA:
            pragmas.append(tok.text)
        elif tok.kind == L.TK_COMMENT:
            comments.append(_comment_body(tok.text))
        i -= 1
    pragmas.reverse()
    comments.reverse()
    return pragmas, comments


def _trailing_comment(tokens: Sequence[L.Token], index: int) -> str | None:
    """Комментарий в той же строке после токена index (обычно ';' объявления)."""
    line = tokens[index].line
    i = index + 1
    while i < len(tokens) and tokens[i].kind in (L.TK_WS, L.TK_COMMENT):
        tok = tokens[i]
        if tok.kind == L.TK_WS and "\n" in tok.text:
            return None
        if tok.kind == L.TK_COMMENT and tok.line == line:
            return _comment_body(tok.text)
        i += 1
    return None


def parse_attributes(pragmas: Iterable[str]) -> list[tuple[str, str]]:
    """{attribute 'имя'} и {attribute 'имя' := 'значение'} -> [(имя, значение)]; прочие прагмы пропускаются."""
    found: list[tuple[str, str]] = []
    for pragma in pragmas:
        match = _ATTRIBUTE_RE.match(pragma.strip())
        if match:
            found.append((match.group(1), match.group(2) or ""))
    return found


def attributes_data(attributes: Sequence[tuple[str, str]]) -> Node:
    data = data_node(CDS_ATTRIBUTES)
    box = data.add("Attributes")
    for name, value in attributes:
        box.add("Attribute", [("Name", name), ("Value", value)])
    return data


def documentation_node(lines: Sequence[str]) -> Node | None:
    text = "\n".join(line.rstrip() for line in lines).strip("\n")
    if not text.strip():
        return None
    doc = Node("documentation")
    doc.append(xhtml(text))
    return doc


# ---------------------------------------------------------------------------
# Разбор объявления: заголовок, секции переменных, комментарии
# ---------------------------------------------------------------------------


@dataclass
class Decl:
    """Разобранное объявление объекта или члена."""

    text: str
    tokens: list[L.Token]
    header: L.DeclHeader | None
    blocks: list[L.VarBlock]
    attributes: list[tuple[str, str]]
    doc: list[str]


def parse_decl(text: str) -> Decl:
    tokens = L.tokenize(text)
    header = L.parse_header(text, tokens)
    blocks = L.parse_var_blocks(text, tokens)
    attributes: list[tuple[str, str]] = []
    doc: list[str] = []
    if header is not None:
        pragmas, comments = _leading_trivia(tokens, header.keyword_index)
        attributes = parse_attributes(pragmas)
        doc = comments
    return Decl(text, tokens, header, blocks, attributes, doc)


def variable_nodes(decl: Decl, var: L.VarDecl) -> list[Node]:
    """Элементы <variable> для объявления (a, b : INT -> две переменные)."""
    tokens = decl.tokens
    address = tokens[var.address_index].text if var.address_index is not None else None
    pragmas, comments = _leading_trivia(tokens, var.first_index)
    attributes = parse_attributes(pragmas)
    trailing = _trailing_comment(tokens, var.semi_index) if var.semi_index is not None else None
    doc_lines = [trailing] if trailing is not None else comments
    nodes = []
    for name in var.name_list:
        attrs = [("name", name)]
        if address:
            attrs.append(("address", address))
        node = Node("variable", attrs)
        node.append(type_node(var.type_text or "BOOL"))
        if var.init_text:
            node.append(value_node(var.init_text))
        if attributes:
            node.add("addData").append(attributes_data(attributes))
        doc = documentation_node(doc_lines)
        if doc is not None:
            node.append(doc)
        nodes.append(node)
    return nodes


def var_list_node(decl: Decl, block: L.VarBlock, tag: str, name: str | None = None) -> Node:
    attrs: list[tuple[str, str]] = []
    if name is not None:
        attrs.append(("name", name))
    for modifier in block.modifiers:
        flag = VAR_FLAGS.get(modifier)
        if flag and (flag, "true") not in attrs:
            attrs.append((flag, "true"))
    node = Node(tag, attrs)
    for var in block.decls:
        for child in variable_nodes(decl, var):
            node.append(child)
    return node


# ---------------------------------------------------------------------------
# Преобразование объектов
# ---------------------------------------------------------------------------


@dataclass
class Options:
    """Параметры преобразования."""

    namespace: str = NS_0201
    project_name: str = "project"
    timestamp: str = "2000-01-01T00:00:00"
    folders: bool = True
    company: str = ""
    plaintext: bool = True


@dataclass
class _Placed:
    obj: L.StObject
    folder: list[str]
    object_id: str
    member_ids: list[tuple[str, str]] = field(default_factory=list)


class Converter:
    """Объекты раскладки -> дерево PLCopen XML (элемент project)."""

    def __init__(self, options: Options) -> None:
        self.options = options
        self.issues: list[Issue] = []
        self._placed: list[_Placed] = []
        self._pvl_seen: str | None = None

    # --- служебное -----------------------------------------------------------

    def warn(self, obj: L.StObject, message: str) -> None:
        self.issues.append(Issue("warning", obj.main_path(), message))

    def error(self, obj: L.StObject, message: str) -> None:
        self.issues.append(Issue("error", obj.main_path(), message))

    def _id(self, *parts: str) -> str:
        return str(uuid.uuid5(_OBJECT_ID_NAMESPACE, "/".join(parts)))

    def _check_text(self, obj: L.StObject, text: str | None) -> str:
        if text is None:
            return ""
        match = _INVALID_XML_CHARS.search(text)
        if match:
            self.error(obj, f"недопустимый в XML символ U+{ord(match.group(0)):04X} — уберите его из исходника")
            return _INVALID_XML_CHARS.sub("", text)
        return text

    def _objectid_data(self, object_id: str) -> Node:
        data = data_node(CDS_OBJECTID, "discard")
        data.add("ObjectId", text=object_id)
        return data

    def _add_plaintext_data(self, add: Node, obj: L.StObject, text: str) -> None:
        """addData/data[interfaceasplaintext] — текст объявления объекта (кроме режима «только TC6»)."""
        if not self.options.plaintext:
            return
        data = add.add("data", [("name", CDS_PLAINTEXT), ("handleUnknown", "implementation")])
        data.append(plaintext_node(self._check_text(obj, text)))

    def _add_plaintext(self, node: Node, obj: L.StObject, text: str) -> None:
        """Прямой <InterfaceAsPlainText> метода, свойства, аксессора, интерфейса (кроме режима «только TC6»)."""
        if self.options.plaintext:
            node.append(plaintext_node(self._check_text(obj, text)))

    # --- точка входа ----------------------------------------------------------

    def convert(self, placed: Sequence[tuple[L.StObject, list[str]]]) -> Node:
        opts = self.options
        root = Node("project", [("xmlns", opts.namespace)])
        root.add(
            "fileHeader",
            [
                ("companyName", opts.company),
                ("productName", PRODUCT_NAME),
                ("productVersion", __version__),
                ("creationDateTime", opts.timestamp),
            ],
        )
        content = root.add("contentHeader", [("name", opts.project_name), ("modificationDateTime", opts.timestamp)])
        coords = content.add("coordinateInfo")
        for lang in ("fbd", "ld", "sfc"):
            coords.add(lang).add("scaling", [("x", "1"), ("y", "1")])
        types = root.add("types")
        data_types = types.add("dataTypes")
        pous = types.add("pous")
        root.add("instances").add("configurations")
        extra: list[Node] = []
        for obj, folder in placed:
            item = _Placed(obj, list(folder), self._id(obj.kind, *folder, obj.name))
            self._placed.append(item)
            if obj.kind == L.KIND_DUT:
                node = self.dut(item)
                if node is not None and node.tag == "dataType":
                    data_types.append(node)
                elif node is not None:
                    extra.append(node)
            elif obj.kind in (L.KIND_GVL, L.KIND_PVL):
                extra.append(self.gvl(item))
            elif obj.kind == L.KIND_ITF:
                extra.append(self.interface(item))
            elif obj.kind == L.KIND_POU:
                pous.append(self.pou(item))
        add_data = Node("addData")
        for node in extra:
            add_data.append(node)
        if opts.folders and self._placed:
            add_data.append(self.structure())
        if add_data.children:
            root.append(add_data)
        return root

    # --- DUT ------------------------------------------------------------------

    def dut(self, item: _Placed) -> Node | None:
        obj = item.obj
        decl = parse_decl(obj.decl)
        tdecl = L.parse_type_decl(obj.decl, decl.tokens)
        if tdecl is None or tdecl.kind is None:
            self.error(obj, "не удалось разобрать TYPE ... END_TYPE")
            return None
        if tdecl.kind == "union":
            union = Node("union", [("name", obj.name)])
            for var in tdecl.members:
                for child in variable_nodes(decl, var):
                    union.append(child)
            add = union.add("addData")
            if decl.attributes:
                add.append(attributes_data(decl.attributes))
            self._add_plaintext_data(add, obj, obj.decl)
            add.append(self._objectid_data(item.object_id))
            doc = documentation_node(decl.doc)
            if doc is not None:
                union.append(doc)
            wrapper = data_node(CDS_UNION)
            wrapper.append(union)
            return wrapper
        node = Node("dataType", [("name", obj.name)])
        base = node.add("baseType")
        add_first: list[Node] = []
        if tdecl.kind == "struct":
            struct = base.add("struct")
            for var in tdecl.members:
                for child in variable_nodes(decl, var):
                    struct.append(child)
            if tdecl.header.extends:
                inh = data_node(CDS_DUT_INHERITANCE)
                box = inh.add("Inheritance")
                for name in tdecl.header.extends:
                    box.add("Extends", text=name)
                add_first.append(inh)
        elif tdecl.kind == "enum":
            enum = base.add("enum")
            values = enum.add("values")
            for name, value, _ in tdecl.enum_values:
                attrs = [("name", name)]
                if value is not None:
                    attrs.append(("value", value))
                values.add("value", attrs)
            if tdecl.enum_base_type:
                enum.append(type_node(tdecl.enum_base_type, "baseType"))
        else:
            alias, init = _alias_parts(decl.tokens)
            base.children = type_node(alias or (tdecl.alias_type or ""), "baseType").children
            if init:
                node.append(value_node(init))
        add = node.add("addData")
        for child in add_first:
            add.append(child)
        if decl.attributes:
            add.append(attributes_data(decl.attributes))
        self._add_plaintext_data(add, obj, obj.decl)
        add.append(self._objectid_data(item.object_id))
        doc = documentation_node(decl.doc)
        if doc is not None:
            node.append(doc)
        return node

    # --- GVL и Persistent Variables ---------------------------------------------

    def gvl(self, item: _Placed) -> Node:
        obj = item.obj
        decl = parse_decl(obj.decl)
        blocks = [b for b in decl.blocks if b.keyword == "VAR_GLOBAL"]
        is_pvl = obj.kind == L.KIND_PVL
        if is_pvl:
            if self._pvl_seen is not None:
                self.warn(
                    obj,
                    f"второй список Persistent Variables (первый — {self._pvl_seen}): в приложении CODESYS "
                    "такой список один, импорт второго откажет",
                )
            self._pvl_seen = obj.name
        elif any("PERSISTENT" in b.modifiers for b in blocks):
            self.warn(
                obj,
                "VAR_GLOBAL PERSISTENT в обычном GVL: импортируется как GVL (CODESYS предупредит C0244); "
                "для Persistent Variables используйте файл .pvl.st",
            )

        def make(block: L.VarBlock | None, with_vars: Sequence[L.VarBlock]) -> Node:
            attrs = [("name", obj.name)]
            modifiers = block.modifiers if block is not None else []
            for modifier in modifiers:
                flag = VAR_FLAGS.get(modifier)
                if flag == "persistent" and not is_pvl:
                    continue
                if flag and (flag, "true") not in attrs:
                    attrs.append((flag, "true"))
            if is_pvl and ("persistent", "true") not in attrs:
                attrs.append(("persistent", "true"))
            node = Node("globalVars", attrs)
            for blk in with_vars:
                for var in blk.decls:
                    for child in variable_nodes(decl, var):
                        node.append(child)
            return node

        main = make(blocks[0] if blocks else None, blocks)
        add = main.add("addData")
        if decl.attributes:
            add.append(attributes_data(decl.attributes))
        self._add_plaintext_data(add, obj, obj.decl)
        add.append(self._objectid_data(item.object_id))
        if len(blocks) > 1:
            mixed = data_node(CDS_MIXED)
            box = mixed.add("MixedAttrsVarList")
            for block in blocks:
                box.append(make(block, [block]))
            add.append(mixed)
        doc = documentation_node(decl.doc)
        if doc is not None:
            main.append(doc)
        wrapper = data_node(CDS_GLOBALVARS)
        wrapper.append(main)
        return wrapper

    # --- интерфейс POU и методов ---------------------------------------------

    def interface_node(
        self,
        obj: L.StObject,
        decl: Decl,
        return_type: str | None,
        extra_add: Sequence[Node] = (),
        tag: str = "interface",
    ) -> Node:
        node = Node(tag)
        if return_type:
            node.append(type_node(return_type, "returnType"))
        header = decl.header
        if not self.options.plaintext and header is not None and "ABSTRACT" in header.modifiers:
            self.warn(obj, f"ABSTRACT у {header.name} в структурной части TC6 не передаётся")
        for block in decl.blocks:
            list_tag = VAR_LISTS.get(block.keyword)
            if list_tag is None:
                if block.keyword != "VAR_INST" or not self.options.plaintext:
                    note = " (есть в тексте объявления)" if self.options.plaintext else ""
                    self.warn(obj, f"секция {block.keyword} в структурной части TC6 не передаётся{note}")
                continue
            # VAR_IN_OUT CONSTANT -> inOutVars constant="true" (в TC6 такого сочетания нет, точен текст объявления)
            node.append(var_list_node(decl, block, list_tag))
        add_children = list(extra_add)
        if decl.attributes:
            add_children.append(attributes_data(decl.attributes))
        access = self.access_flags(decl)
        if access:
            data = data_node(CDS_ACCESS)
            data.add("AccessModifiers", [(flag, "true") for flag in access])
            add_children.append(data)
        if add_children:
            add = node.add("addData")
            for child in add_children:
                add.append(child)
        doc = documentation_node(decl.doc)
        if doc is not None:
            node.append(doc)
        return node

    @staticmethod
    def access_flags(decl: Decl) -> list[str]:
        if decl.header is None:
            return []
        flags = [ACCESS_FLAGS[m] for m in decl.header.modifiers if m in ACCESS_FLAGS]
        return sorted(set(flags))

    # --- POU ------------------------------------------------------------------

    def pou(self, item: _Placed) -> Node:
        obj = item.obj
        decl = parse_decl(obj.decl)
        header = decl.header
        node = Node("pou", [("name", obj.name), ("pouType", POU_TYPES.get(obj.pou_kind or "", "program"))])
        inheritance: list[Node] = []
        if header is not None and (header.extends or header.implements):
            inh = data_node(CDS_POU_INHERITANCE)
            box = inh.add("Inheritance")
            for name in header.extends:
                box.add("Extends", text=name)
            for name in header.implements:
                box.add("Implements", text=name)
            inheritance.append(inh)
        return_type = header.return_type if header is not None and obj.pou_kind == L.POU_FUNCTION else None
        node.append(self.interface_node(obj, decl, return_type, inheritance))
        node.append(st_body(self._check_text(obj, obj.impl)))
        add = node.add("addData")
        for method in obj.methods:
            mid = self._id(obj.kind, *item.folder, obj.name, "method", method.name)
            item.member_ids.append((method.name, mid))
            add.append(self.method(obj, method, mid, with_body=True))
        for prop in obj.properties:
            pid = self._id(obj.kind, *item.folder, obj.name, "property", prop.name)
            item.member_ids.append((prop.name, pid))
            add.append(self.property(obj, prop, pid, in_interface=False))
        self._add_plaintext_data(add, obj, obj.decl)
        add.append(self._objectid_data(item.object_id))
        return node

    def method(self, obj: L.StObject, method: L.StMethod, object_id: str, with_body: bool) -> Node:
        decl = parse_decl(method.decl)
        return_type = decl.header.return_type if decl.header is not None else None
        node = Node("Method", [("name", method.name), ("ObjectId", object_id)])
        node.append(self.interface_node(obj, decl, return_type))
        if with_body:
            node.append(st_body(self._check_text(obj, method.impl)))
        self._add_plaintext(node, obj, method.decl)
        node.add("addData")
        if not with_body:
            return node
        wrapper = data_node(CDS_METHOD)
        wrapper.append(node)
        return wrapper

    def property(self, obj: L.StObject, prop: L.StProperty, object_id: str, in_interface: bool) -> Node:
        decl = parse_decl(prop.decl)
        return_type = decl.header.return_type if decl.header is not None else None
        node = Node("Property", [("name", prop.name), ("ObjectId", object_id)])
        itf = Node("interface")
        if return_type:
            itf.append(type_node(return_type, "returnType"))
        access = self.access_flags(decl)
        if access:
            data = data_node(CDS_ACCESS)
            data.add("AccessModifiers", [(flag, "true") for flag in access])
            itf.add("addData").append(data)
        doc = documentation_node(decl.doc)
        if doc is not None:
            itf.append(doc)
        node.append(itf)
        # порядок аксессоров — как в экспорте CODESYS: сначала Set, затем Get
        for present, tag, acc_decl, acc_impl in (
            (prop.has_set, "SetAccessor", prop.set_decl, prop.set_impl),
            (prop.has_get, "GetAccessor", prop.get_decl, prop.get_impl),
        ):
            if not present:
                continue
            acc = node.add(tag)
            if in_interface:
                self._add_plaintext(acc, obj, acc_decl or "")
                continue
            text = acc_decl if acc_decl is not None else DEFAULT_ACCESSOR_DECL
            acc.append(self.interface_node(obj, parse_decl(text), None))
            acc.append(st_body(self._check_text(obj, acc_impl)))
            self._add_plaintext(acc, obj, text)
            acc.add("addData")
        self._add_plaintext(node, obj, prop.decl)
        node.add("addData")
        if in_interface:
            return node
        wrapper = data_node(CDS_PROPERTY)
        wrapper.append(node)
        return wrapper

    # --- интерфейс ------------------------------------------------------------

    def interface(self, item: _Placed) -> Node:
        obj = item.obj
        decl = parse_decl(obj.decl)
        node = Node("Interface", [("name", obj.name), ("ObjectId", item.object_id)])
        if obj.methods:
            methods = node.add("Methods")
            for method in obj.methods:
                mid = self._id(obj.kind, *item.folder, obj.name, "method", method.name)
                item.member_ids.append((method.name, mid))
                methods.append(self.method(obj, method, mid, with_body=False))
        if obj.properties:
            props = node.add("Properties")
            for prop in obj.properties:
                pid = self._id(obj.kind, *item.folder, obj.name, "property", prop.name)
                item.member_ids.append((prop.name, pid))
                props.append(self.property(obj, prop, pid, in_interface=True))
        header = decl.header
        if header is not None and header.extends:
            box = node.add("Inheritance")
            for name in header.extends:
                box.add("Extends", text=name)
        self._add_plaintext(node, obj, obj.decl)
        doc = documentation_node(decl.doc)
        if doc is not None:
            node.append(doc)
        add = node.add("addData")
        if decl.attributes:
            add.append(attributes_data(decl.attributes))
        wrapper = data_node(CDS_INTERFACE)
        wrapper.append(node)
        return wrapper

    # --- папки ----------------------------------------------------------------

    def structure(self) -> Node:
        data = data_node(CDS_STRUCTURE, "discard")
        root = data.add("ProjectStructure")
        folders: dict[tuple[str, ...], Node] = {}
        for item in self._placed:
            parent = root
            for depth in range(1, len(item.folder) + 1):
                key = tuple(item.folder[:depth])
                if key not in folders:
                    folders[key] = parent.add("Folder", [("Name", key[-1])])
                parent = folders[key]
            obj_node = parent.add("Object", [("Name", item.obj.name), ("ObjectId", item.object_id)])
            for name, member_id in item.member_ids:
                obj_node.add("Object", [("Name", name), ("ObjectId", member_id)])
        return data


def _alias_parts(tokens: Sequence[L.Token]) -> tuple[str | None, str | None]:
    """Псевдоним TYPE T : <тип> [:= <значение>]; END_TYPE -> (тип, значение)."""
    sig = [t for t in tokens if t.kind not in (L.TK_WS, L.TK_COMMENT, L.TK_PRAGMA)]
    try:
        start = next(i for i, t in enumerate(sig) if t.is_op(":")) + 1
    except StopIteration:
        return None, None
    end = len(sig)
    for i in range(start, len(sig)):
        if sig[i].is_op(";") or sig[i].is_ident("END_TYPE"):
            end = i
            break
    part = sig[start:end]
    assign = _find_top(part, ":=")
    if assign < 0:
        return _join(part) or None, None
    return _join(part[:assign]) or None, _join(part[assign + 1 :]) or None


# ---------------------------------------------------------------------------
# Раскладка -> XML
# ---------------------------------------------------------------------------


@dataclass
class Result:
    """Итог преобразования: текст XML (пустой при ошибках раскладки) и замечания."""

    xml: str
    issues: list[Issue]
    objects: int

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]


def collect_objects(
    root: str, subdirs: Sequence[tuple[str, Sequence[str]]], exclude: Iterable[str] = ()
) -> tuple[list[tuple[L.StObject, list[str]]], list[Issue]]:
    """Объекты раскладки с папкой проекта: [(объект, [папка, ...])]; tests/ — в папку с префиксом."""
    excluded = {name.lower() for name in exclude}
    placed: list[tuple[L.StObject, list[str]]] = []
    issues: list[Issue] = []
    seen: dict[str, str] = {}
    for subdir, prefix in subdirs:
        scanned = L.scan(root, subdir)
        for lay in scanned.issues:
            issues.append(Issue(lay.severity, f"{lay.path}:{lay.line}", f"{lay.code} {lay.message}"))
        for obj in scanned.objects:
            if obj.name.lower() in excluded:
                continue
            key = obj.name.lower()
            if key in seen:
                issues.append(Issue("error", obj.main_path(), f"объект {obj.name} уже объявлен в {seen[key]}"))
                continue
            seen[key] = obj.main_path()
            placed.append((obj, list(prefix) + list(obj.folder)))
    return placed, issues


def convert_objects(placed: Sequence[tuple[L.StObject, list[str]]], options: Options) -> Result:
    conv = Converter(options)
    root = conv.convert(placed)
    return Result(serialize(root), conv.issues, len(placed))


def convert_layout(
    root: str,
    options: Options,
    src: str = "src",
    tests: str | None = None,
    tests_folder: str = "Tests",
    exclude: Iterable[str] = (),
) -> Result:
    """Раскладка root/src (и root/tests в папку tests_folder) -> PLCopen XML."""
    subdirs: list[tuple[str, Sequence[str]]] = [(src, [])]
    if tests:
        subdirs.append((tests, [tests_folder]))
    placed, issues = collect_objects(root, subdirs, exclude)
    if any(i.severity == "error" for i in issues):
        return Result("", issues, len(placed))
    result = convert_objects(placed, options)
    result.issues[:0] = issues
    return result


# ---------------------------------------------------------------------------
# XML -> раскладка (по текстам объявлений)
# ---------------------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(elem: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in elem if _local(c.tag) == name]


def _child(elem: ET.Element, name: str) -> ET.Element | None:
    found = _children(elem, name)
    return found[0] if found else None


def _xhtml_text(elem: ET.Element | None) -> str | None:
    if elem is None:
        return None
    for node in elem.iter():
        if _local(node.tag) == "xhtml":
            return node.text or ""
    return None


def _plaintext_of(elem: ET.Element) -> str | None:
    """Текст объявления: прямой <InterfaceAsPlainText> или addData/data[interfaceasplaintext]."""
    direct = _child(elem, "InterfaceAsPlainText")
    if direct is not None:
        return _xhtml_text(direct)
    add = _child(elem, "addData")
    if add is not None:
        for data in _children(add, "data"):
            if data.get("name") == CDS_PLAINTEXT:
                return _xhtml_text(_child(data, "InterfaceAsPlainText"))
    return None


def _body_text(elem: ET.Element) -> str | None:
    body = _child(elem, "body")
    if body is None:
        return None
    st = _child(body, "ST")
    return _xhtml_text(st) if st is not None else None


def _non_st_language(elem: ET.Element) -> str | None:
    """Язык тела, если тело есть и оно не на ST (FBD, LD, SFC, CFC...), иначе None."""
    body = _child(elem, "body")
    if body is None or _child(body, "ST") is not None:
        return None
    languages = [_local(child.tag) for child in body if _local(child.tag) not in ("documentation", "addData")]
    return languages[0] if languages else None


def _object_id(elem: ET.Element) -> str | None:
    if elem.get("ObjectId"):
        return elem.get("ObjectId")
    add = _child(elem, "addData")
    if add is not None:
        for data in _children(add, "data"):
            if data.get("name") == CDS_OBJECTID:
                oid = _child(data, "ObjectId")
                return (oid.text or "").strip() if oid is not None else None
    return None


def _folders_by_id(root: ET.Element) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}

    def walk(elem: ET.Element, path: list[str]) -> None:
        for child in elem:
            tag = _local(child.tag)
            if tag == "Folder":
                walk(child, [*path, child.get("Name") or ""])
            elif tag == "Object":
                if child.get("ObjectId"):
                    found.setdefault(child.get("ObjectId") or "", list(path))
                walk(child, path)

    for elem in root.iter():
        if _local(elem.tag) == "ProjectStructure":
            walk(elem, [])
    return found


def _accessor(elem: ET.Element | None, in_interface: bool) -> tuple[str | None, str | None]:
    """(объявление или None, тело или None) аксессора; объявление по умолчанию — None, как в раскладке."""
    if elem is None:
        return None, None
    decl = _plaintext_of(elem) or ""
    body = None if in_interface else (_body_text(elem) or "")
    if in_interface:
        return L.normalize_text(decl), None
    norm = L.normalize_text(decl)
    if L.squash_ws(norm) == L.squash_ws(DEFAULT_ACCESSOR_DECL):
        return None, L.normalize_text(body or "")
    return norm, L.normalize_text(body or "")


def read_xml(text: str) -> tuple[list[L.StObject], list[Issue]]:
    """PLCopen XML с текстами объявлений -> объекты раскладки (папки — из projectstructure).

    Понимает свой формат и экспорт CODESYS/Astra.IDE с флагом «объявления как обычный текст» (в том числе
    экспорт приложения целиком). Объект без текста объявления — ошибка: восстанавливать текст по структурной
    части TC6 инструмент не берётся (она неполная).
    """
    root = ET.fromstring(text)
    folders = _folders_by_id(root)
    parents = {child: parent for parent in root.iter() for child in parent}
    objects: list[L.StObject] = []
    issues: list[Issue] = []

    def folder_of(elem: ET.Element) -> list[str]:
        oid = _object_id(elem)
        return list(folders.get(oid or "", []))

    def need(name: str, decl: str | None) -> str | None:
        if decl is None:
            issues.append(Issue("error", name, "нет текста объявления (экспорт без «объявлений как обычный текст»?)"))
        return decl

    for elem in root.iter():
        tag = _local(elem.tag)
        if tag in ("dataType", "union"):
            decl = need(elem.get("name") or "?", _plaintext_of(elem))
            if decl is not None:
                objects.append(L.StObject(L.KIND_DUT, elem.get("name") or "", L.normalize_text(decl), folder_of(elem)))
        elif tag == "globalVars":
            # объекты-списки: в data globalvars (экспорт объектов) или в resource (экспорт приложения);
            # не секции VAR_STAT интерфейса POU и не копии блоков в mixedattrsvarlist
            parent = parents.get(elem)
            if parent is None:
                continue
            parent_tag = _local(parent.tag)
            if not (parent_tag == "resource" or (parent_tag == "data" and parent.get("name") == CDS_GLOBALVARS)):
                continue
            decl = need(elem.get("name") or "?", _plaintext_of(elem))
            if decl is None:
                continue
            kind = L.KIND_PVL if elem.get("persistent") == "true" else L.KIND_GVL
            objects.append(L.StObject(kind, elem.get("name") or "", L.normalize_text(decl), folder_of(elem)))
        elif tag == "Interface":
            decl = need(elem.get("name") or "?", _plaintext_of(elem))
            if decl is None:
                continue
            obj = L.StObject(L.KIND_ITF, elem.get("name") or "", L.normalize_text(decl), folder_of(elem))
            methods = _child(elem, "Methods")
            for itf_method in _children(methods, "Method") if methods is not None else []:
                mdecl = need(f"{obj.name}.{itf_method.get('name')}", _plaintext_of(itf_method))
                if mdecl is not None:
                    obj.methods.append(L.StMethod(itf_method.get("name") or "", L.normalize_text(mdecl)))
            props = _child(elem, "Properties")
            for itf_prop in _children(props, "Property") if props is not None else []:
                pdecl = need(f"{obj.name}.{itf_prop.get('name')}", _plaintext_of(itf_prop))
                if pdecl is None:
                    continue
                get_decl, _ = _accessor(_child(itf_prop, "GetAccessor"), True)
                set_decl, _ = _accessor(_child(itf_prop, "SetAccessor"), True)
                obj.properties.append(
                    L.StProperty(
                        itf_prop.get("name") or "", L.normalize_text(pdecl), get_decl=get_decl, set_decl=set_decl
                    )
                )
            obj.sorted_members()
            objects.append(obj)
        elif tag == "pou":
            name = elem.get("name") or ""
            decl = need(name, _plaintext_of(elem))
            if decl is None:
                continue
            language = _non_st_language(elem)
            if language is not None:
                issues.append(Issue("warning", name, f"тело на {language}: в раскладке только ST — объект пропущен"))
                continue
            kind = {v: k for k, v in POU_TYPES.items()}.get(elem.get("pouType") or "", L.POU_PROGRAM)
            obj = L.StObject(
                L.KIND_POU,
                name,
                L.normalize_text(decl),
                folder_of(elem),
                impl=L.normalize_text(_body_text(elem) or ""),
                pou_kind=kind,
            )
            add = _child(elem, "addData")
            for data in _children(add, "data") if add is not None else []:
                if data.get("name") == CDS_METHOD:
                    m = _child(data, "Method")
                    if m is None:
                        continue
                    mdecl = need(f"{name}.{m.get('name')}", _plaintext_of(m))
                    if mdecl is None:
                        continue
                    language = _non_st_language(m)
                    if language is not None:
                        where = f"{name}.{m.get('name')}"
                        issues.append(
                            Issue("warning", where, f"тело на {language}: в раскладке только ST — метод пропущен")
                        )
                        continue
                    method = L.StMethod(
                        m.get("name") or "", L.normalize_text(mdecl), L.normalize_text(_body_text(m) or "")
                    )
                    if method.is_abstract and not method.impl:
                        method.impl = None
                    obj.methods.append(method)
                elif data.get("name") == CDS_PROPERTY:
                    p = _child(data, "Property")
                    if p is None:
                        continue
                    pdecl = need(f"{name}.{p.get('name')}", _plaintext_of(p))
                    if pdecl is None:
                        continue
                    get_decl, get_impl = _accessor(_child(p, "GetAccessor"), False)
                    set_decl, set_impl = _accessor(_child(p, "SetAccessor"), False)
                    obj.properties.append(
                        L.StProperty(
                            p.get("name") or "",
                            L.normalize_text(pdecl),
                            get_decl=get_decl,
                            get_impl=get_impl,
                            set_decl=set_decl,
                            set_impl=set_impl,
                        )
                    )
            obj.sorted_members()
            objects.append(obj)
    return objects, issues


# ---------------------------------------------------------------------------
# Проверка по XSD TC6 2.01 (lxml; схема скачивается с plcopen.org)
# ---------------------------------------------------------------------------

# Официальная схема PLCopen XML 2.01: plcopen.org, раздел «XML Exchange» -> Downloads, файл
# «PLCopen XML version 2.01 xsd file» (zip с tc6_xml_v201.xsd от 2009-04-28). Условия распространения в
# файле не указаны, поэтому схема в репозиторий не кладётся: скачивается в build/xsd/ и сверяется по SHA-256.
XSD_URL = "https://www.plcopen.org/download_file/force/d397ab98-6a21-47d5-9fb1-37da9e94ef34/342/"
XSD_INFO_URL = "https://www.plcopen.org/standards/xml-echange/"
XSD_MEMBER = "tc6_xml_v201.xsd"
XSD_SHA256 = "591b92ba65018a77c32ab9e606abf27bd810cb1f7761d972a85689531c51e20f"
XSD_ENV = "PLCOPEN_XSD"


class XsdError(RuntimeError):
    """Схему TC6 2.01 не удалось получить или она не та (сеть, хэш, архив)."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_xsd(xml_text: str, xsd_path: str) -> list[str]:
    """Ошибки проверки XML по XSD TC6 2.01 (пустой список — файл валиден).

    Схема TC6 2.01 объявляет пространство имён tc6_0201; файл с tc6_0200 (так пишут CODESYS и Astra.IDE)
    проверяется после замены пространства имён: структура элементов, которые пишет конвертер, в схеме 2.01
    та же. Нужен lxml (requirements-dev.txt).
    """
    etree: Any = importlib.import_module("lxml.etree")  # lxml нужен только для проверки

    schema = etree.XMLSchema(etree.parse(xsd_path))
    data = xml_text.replace(NS_0200, NS_0201).encode("utf-8")
    doc = etree.fromstring(data)
    if schema.validate(doc):
        return []
    return [f"строка {e.line}: {e.message}" for e in schema.error_log]
