"""Промежуточное представление (IR) проекта CODESYS: объекты, тела шести языков, задачи, библиотеки, устройства.

IR не копирует XML: каждый объект держит ссылку на свой элемент `xmltree.Elem` (байтовые границы в
исходнике), а тексты ST/IL и объявлений — `CodeText` с картой смещений. Поэтому правка в IR сразу
переводится в байтовую сшивку исходного файла, и всё, чего правила не коснулись, остаётся побайтно.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..xmltree import Document, Elem, TextMap

LANGUAGES = ("ST", "IL", "LD", "FBD", "CFC", "SFC")


@dataclass(frozen=True)
class Origin:
    """Происхождение: файл, строка и столбец (с 1), localId графического элемента, байтовый диапазон."""

    file: str
    line: int
    column: int = 1
    local_id: str | None = None
    byte_start: int = 0
    byte_end: int = 0


@dataclass(eq=False)
class CodeText:
    """Текст ST/IL или объявления внутри элемента XML (`xhtml`) с картой «символ → байт»."""

    kind: str  # body | decl | transition | il
    elem: Elem
    tmap: TextMap
    owner: str  # полное имя объекта: MAIN, MAIN.Init, FB_X.Method, GVL

    @property
    def text(self) -> str:
        return self.tmap.text

    def line_of(self, pos: int) -> int:
        """Строка в XML-файле для символа pos текста (по байтовой карте и строке элемента)."""
        return self.elem.line + self.tmap.text.count("\n", 0, pos)

    def local_line(self, pos: int) -> int:
        """Строка внутри текста (с 1) — так её показывает IDE (Строка N (Реализ./Объявл.))."""
        return self.tmap.text.count("\n", 0, pos) + 1


@dataclass(eq=False)
class Var:
    """Переменная объявления (из текста объявления или из структуры TC6)."""

    name: str
    type_text: str
    section: str  # VAR, VAR_INPUT, VAR_GLOBAL, ...
    address: str | None = None
    retain: bool = False
    persistent: bool = False
    constant: bool = False
    init: str | None = None
    attributes: list[str] = field(default_factory=list)  # {attribute '...'} перед объявлением
    elem: Elem | None = None  # <variable> структурной части TC6
    code: CodeText | None = None  # текст объявления, где найдена
    decl_span: tuple[int, int] | None = None  # символы объявления в code.text (до ';' включительно)
    at_span: tuple[int, int] | None = None  # символы «AT %IX0.0» (с пробелом перед AT)
    line: int = 0


@dataclass(eq=False)
class GRef:
    """Ссылка в графическом теле: блок, переменная, контакт, катушка, шаг, переход, действие."""

    kind: str  # block | var | contact | coil | step | transition | action | jump | label | connector
    name: str
    elem: Elem
    attr: str | None  # атрибут с именем (typeName, instanceName, name) или None — текст элемента
    local_id: str | None
    network: int | None
    instance: str | None = None  # instanceName блока
    text_elem: Elem | None = None  # элемент, чей текст — имя (expression, variable, reference)


@dataclass(eq=False)
class Body:
    """Тело объекта. language — ST/IL/LD/FBD/CFC/SFC, LD20 (новый LD SP20), NONE (нет тела)."""

    language: str
    elem: Elem | None
    lang_elem: Elem | None = None
    code: CodeText | None = None
    refs: list[GRef] = field(default_factory=list)
    networks: int = 0
    il_lost: bool = False  # POU на IL экспортирован с пустым <ST> (IL был выключен в IDE)
    vendor: str | None = None  # имя addData тела (cfc, ld20 …)


@dataclass(eq=False)
class Pou:
    """POU и его вложенные объекты (действия, переходы, методы, свойства, аксессоры)."""

    name: str
    kind: str  # program | function | functionBlock | interface | method | property | get | set | action | transition
    elem: Elem
    placement: str  # types | resource | twincat | nested | project
    parent: Pou | None = None
    decl: CodeText | None = None  # interfaceasplaintext (первая копия)
    decl_copies: list[CodeText] = field(default_factory=list)  # все копии текста объявления (CODESYS дублирует)
    vars: list[Var] = field(default_factory=list)
    body: Body | None = None
    children: list[Pou] = field(default_factory=list)
    object_id: str | None = None
    return_type: str | None = None
    extends: str | None = None
    implements: list[str] = field(default_factory=list)
    origin: Origin | None = None

    @property
    def path(self) -> str:
        if self.parent is None:
            return self.name
        return f"{self.parent.path}.{self.name}"

    def walk(self) -> list[Pou]:
        out: list[Pou] = [self]
        for c in self.children:
            out.extend(c.walk())
        return out


@dataclass(eq=False)
class Gvl:
    name: str
    elem: Elem
    placement: str
    decl: CodeText | None = None
    decl_copies: list[CodeText] = field(default_factory=list)
    vars: list[Var] = field(default_factory=list)
    persistent: bool = False
    constant: bool = False
    attributes: list[str] = field(default_factory=list)
    object_id: str | None = None
    origin: Origin | None = None


@dataclass(eq=False)
class Dut:
    name: str
    elem: Elem
    kind: str  # struct | enum | alias | union | unknown
    decl: CodeText | None = None
    placement: str = "types"
    origin: Origin | None = None


@dataclass(eq=False)
class Task:
    name: str
    elem: Elem
    priority: int | None
    interval_ms: float | None
    interval_raw: str | None
    kind: str  # Cyclic | Freewheeling | Event | Status | unknown
    pous: list[str] = field(default_factory=list)
    settings_elem: Elem | None = None
    resource: str = ""
    origin: Origin | None = None


@dataclass(eq=False)
class LibRef:
    name: str  # как в файле: '#Standard' или 'PsTechEE, 1.7.0.4 (RegLab)'
    elem: Elem
    namespace: str | None
    default_resolution: str | None
    placeholder: bool
    title: str
    version: str | None
    company: str | None
    origin: Origin | None = None


@dataclass(eq=False)
class Mapping:
    variable: str  # Application.MODULE.CH01
    parameter: str  # Name параметра
    channel: str | None  # input | output
    param_type: str | None
    elem: Elem


@dataclass(eq=False)
class Device:
    name: str
    type: str
    id: str
    version: str
    elem: Elem  # <data name="Device">
    parent: Device | None = None
    children: list[Device] = field(default_factory=list)
    connectors: list[str] = field(default_factory=list)
    parameters: int = 0
    mappings: list[Mapping] = field(default_factory=list)
    origin: Origin | None = None

    @property
    def path(self) -> str:
        return self.name if self.parent is None else f"{self.parent.path}/{self.name}"

    def walk(self) -> list[Device]:
        out: list[Device] = [self]
        for c in self.children:
            out.extend(c.walk())
        return out


@dataclass(eq=False)
class UnknownData:
    """`addData/data`, которого импортёр не знает: сохраняется как есть и попадает в отчёт."""

    name: str
    elem: Elem
    path: str


@dataclass(eq=False)
class Issue:
    """Замечание импорта (не правило переноса): кодировка, неизвестная форма, потери TC6."""

    code: str
    message: str
    line: int = 0
    severity: str = "warning"


@dataclass(eq=False)
class Project:
    """Проект целиком."""

    file: str
    doc: Document
    namespace: str
    company: str | None = None
    product: str | None = None
    product_version: str | None = None
    project_name: str | None = None
    pous: list[Pou] = field(default_factory=list)
    gvls: list[Gvl] = field(default_factory=list)
    duts: list[Dut] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    libraries: list[LibRef] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)
    unknown: list[UnknownData] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    placements: list[str] = field(default_factory=list)  # types | resource | twincat
    configurations: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    has_plaintext: bool = False
    structure: Elem | None = None  # addData projectstructure
    libraries_elem: Elem | None = None
    source_kind: str = "plcopen-xml"  # plcopen-xml | st-layout

    def all_pous(self) -> list[Pou]:
        out: list[Pou] = []
        for p in self.pous:
            out.extend(p.walk())
        return out

    def all_devices(self) -> list[Device]:
        out: list[Device] = []
        for d in self.devices:
            out.extend(d.walk())
        return out

    def find_pou(self, name: str) -> Pou | None:
        low = name.lower()
        for p in self.pous:
            if p.name.lower() == low:
                return p
        return None

    def object_names(self) -> set[str]:
        names = {p.name.lower() for p in self.pous}
        names |= {g.name.lower() for g in self.gvls}
        names |= {d.name.lower() for d in self.duts}
        return names
