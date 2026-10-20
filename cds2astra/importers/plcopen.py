"""PLCopen XML (TC6 0200/0201 с расширениями 3S) -> IR.

Три размещения объектов (docs/FORMAT-NOTES.md):

- `types` — `types/pous`, `types/dataTypes` и `project/addData` (globalvars, interface, union): экспорт
  выбранных объектов из пула POU, файлы раскладки (`importers/layout`);
- `resource` — `instances/configurations/configuration/resource` (`addData/data[pou]`, `globalVars`,
  `task`): экспорт CODESYS с устройством и экспорт Astra.IDE (образец niksosov);
- `application` — `project/addData/data[.../application]/resource`: экспорт узла Application в CODESYS
  3.5.17.30 (локальный экспорт kns); той же формой пишет TwinCAT — для него только распознавание.

Тела: ST, IL, FBD, LD, SFC, CFC (`body/addData/data[cfc]` при пустом `ST/xhtml` — это CFC, а не пустой
ST), действия, переходы, методы, свойства и аксессоры, интерфейсы. Устройства — `<data name="Device">`
и вложенные `configurations`. Неизвестные `addData` сохраняются (UnknownData).
"""

from __future__ import annotations

import re

from .. import xmltree as X
from ..ir import st
from ..ir.model import (
    Body,
    CodeText,
    Device,
    Dut,
    GRef,
    Gvl,
    Issue,
    LibRef,
    Mapping,
    Origin,
    Pou,
    Project,
    Task,
    UnknownData,
    Var,
)

NS_0200 = "http://www.plcopen.org/xml/tc6_0200"
NS_0201 = "http://www.plcopen.org/xml/tc6_0201"
CDS = "http://www.3s-software.com/plcopenxml/"

# addData, которые импортёр понимает (или осознанно пропускает как служебные)
KNOWN_DATA = {
    "pou",
    "datatype",
    "interface",
    "union",
    "globalvars",
    "libraries",
    "objectid",
    "interfaceasplaintext",
    "projectstructure",
    "projectinformation",
    "tasksettings",
    "application",
    "attributes",
    "method",
    "property",
    "cfc",
    "cfcpage",
    "cfcpageinfo",
    "cfccalltype",
    "cfcelementtype",
    "Device",
    "configurations",
    "buildproperties",
    "accessmodifiers",
    "pouinheritance",
    "datatypeinheritance",
    "mixedattrsvarlist",
    "enumvaluedocumentation",
    "fbdcalltype",
    "fbdelementtype",
    "ldelementtype",
    "sfc",
    "sfcsettings",
    "sfcimplicitvariable",
    "sfcvariable",
    "inputassignments",
    "outputassignments",
    "fbdnetworkcomment",
    "negated",
    "edge",
    "storage",
    "action",
    "transition",
    "tasks",
    "taskconfiguration",
    "coordinateinfo",
}

LANG_TAGS = ("ST", "IL", "FBD", "LD", "SFC")
# имена addData тела, которые не являются CFC: признак нового редактора LD SP20 (формат не опубликован)
LD20_HINTS = ("ladder", "ld20", "ldnew", "newld", "ldeditor")

_INTERVAL_RE = re.compile(r"^(?:T|TIME|LT|LTIME)#(.+)$", re.IGNORECASE)
_UNIT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)(ms|us|ns|s|m|h|d)", re.IGNORECASE)
_PT_RE = re.compile(r"^PT(?:([0-9.]+)H)?(?:([0-9.]+)M)?(?:([0-9.]+)S)?$", re.IGNORECASE)
_LIBNAME_RE = re.compile(r"^\s*(.+?)\s*,\s*([^\s(]+)\s*\((.+)\)\s*$")


class ImportError_(ValueError):
    """Вход не PLCopen XML (код выхода 2)."""


def _short(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def parse_interval_ms(text: str | None, unit: str | None = None) -> float | None:
    """`100` (с IntervalUnit), `t#1000ms`, `T#1s500ms`, `PT0.1S` -> миллисекунды."""
    if not text:
        return None
    s = text.strip()
    m = _PT_RE.match(s)
    if m and any(m.groups()):
        h, mi, se = (float(g) if g else 0.0 for g in m.groups())
        return round((h * 3600 + mi * 60 + se) * 1000, 6)
    m = _INTERVAL_RE.match(s)
    if m:
        total = 0.0
        body = m.group(1).replace("_", "")
        found = False
        for num, u in _UNIT_RE.findall(body):
            found = True
            k = {"d": 86400000, "h": 3600000, "m": 60000, "s": 1000, "ms": 1, "us": 0.001, "ns": 0.000001}[u.lower()]
            total += float(num) * k
        return round(total, 6) if found else None
    try:
        value = float(s)
    except ValueError:
        return None
    factor = {"ms": 1.0, "us": 0.001, "s": 1000.0, "ns": 0.000001}.get((unit or "ms").lower(), 1.0)
    return round(value * factor, 6)


def parse_libname(name: str) -> tuple[str, str | None, str | None]:
    """'PsTechEE, 1.7.0.4 (RegLab)' -> (title, version, company); '#Standard' -> ('Standard', None, None)."""
    if name.startswith("#"):
        return name[1:], None, None
    m = _LIBNAME_RE.match(name)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return name.strip(), None, None


class _Importer:
    def __init__(self, doc: X.Document, file: str) -> None:
        self.doc = doc
        self.file = file
        root = doc.root
        if root.tag != "project":
            raise ImportError_(f"{file}: корневой элемент <{root.tag}>, ожидался <project> PLCopen XML")
        if root.ns not in (NS_0200, NS_0201):
            raise ImportError_(f"{file}: пространство имён {root.ns!r} не TC6 (tc6_0200/tc6_0201)")
        self.p = Project(file=file, doc=doc, namespace=root.ns)

    # -- служебное -------------------------------------------------------
    def origin(self, el: X.Elem, local_id: str | None = None) -> Origin:
        return Origin(self.file, el.line, el.column, local_id, el.start, el.end)

    def code(self, kind: str, xhtml: X.Elem, owner: str) -> CodeText:
        return CodeText(kind, xhtml, X.text_map(self.doc, xhtml), owner)

    def plaintexts(self, el: X.Elem, owner: str) -> list[CodeText]:
        """Тексты объявления: addData[interfaceasplaintext] у элемента, у списков interface и InterfaceAsPlainText."""
        found: list[X.Elem] = []
        direct = el.child("InterfaceAsPlainText")
        if direct is not None:
            x = direct.child("xhtml")
            if x is not None:
                found.append(x)
        d = el.data("interfaceasplaintext")
        if d is not None:
            ipt = d.child("InterfaceAsPlainText")
            x = ipt.child("xhtml") if ipt is not None else None
            if x is not None:
                found.append(x)
        itf = el.child("interface")
        if itf is not None:
            for lst in itf.children:
                dd = lst.data("interfaceasplaintext")
                if dd is not None:
                    ipt = dd.child("InterfaceAsPlainText")
                    x = ipt.child("xhtml") if ipt is not None else None
                    if x is not None:
                        found.append(x)
        out = [self.code("decl", x, owner) for x in found]
        if out:
            self.p.has_plaintext = True
        return out

    def object_id(self, el: X.Elem) -> str | None:
        if "ObjectId" in el.attrs:
            return el.attrs["ObjectId"]
        d = el.data("objectid")
        if d is not None:
            oid = d.child("ObjectId")
            if oid is not None:
                return oid.text.strip()
        return None

    def note_unknown(self, container: X.Elem) -> None:
        add = container.child("addData")
        if add is None:
            return
        for d in add.kids("data"):
            short = _short(d.attrs.get("name", ""))
            if short not in KNOWN_DATA:
                self.p.unknown.append(UnknownData(d.attrs.get("name", ""), d, d.path()))

    # -- переменные ------------------------------------------------------
    def vars_from_text(self, ct: CodeText) -> list[Var]:
        text = ct.text
        tokens = st.tokenize(text)
        out: list[Var] = []
        try:
            blocks = st.parse_var_blocks(text)
        except Exception:  # pragma: no cover - лексер раскладки не бросает на произвольном тексте
            return out
        for block in blocks:
            for decl in block.decls:
                start = tokens[decl.first_index].pos if decl.first_index < len(tokens) else 0
                end_tok = decl.semi_index if decl.semi_index is not None else decl.last_index
                end = tokens[end_tok].end if end_tok < len(tokens) else len(text)
                address = None
                at_span = None
                if decl.address_index is not None:
                    address = tokens[decl.address_index].text
                    at_idx = decl.address_index - 1
                    while at_idx >= 0 and tokens[at_idx].kind in st.TRIVIA:
                        at_idx -= 1
                    at_start = tokens[at_idx].pos
                    # вместе с пробелами перед AT
                    j = at_idx - 1
                    while j >= 0 and tokens[j].kind == st.TK_WS and "\n" not in tokens[j].text:
                        j -= 1
                    at_start = tokens[j + 1].pos
                    at_span = (at_start, tokens[decl.address_index].end)
                attrs = _attributes_before(tokens, decl.first_index)
                mods = {m.upper() for m in decl.modifiers}
                for name, _idx in decl.names:
                    out.append(
                        Var(
                            name=name,
                            type_text=decl.type_text,
                            section=decl.section,
                            address=address,
                            retain="RETAIN" in mods,
                            persistent="PERSISTENT" in mods,
                            constant="CONSTANT" in mods,
                            init=decl.init_text,
                            attributes=attrs,
                            code=ct,
                            decl_span=(start, end),
                            at_span=at_span,
                            line=ct.line_of(start),
                        )
                    )
        return out

    def vars_from_structure(self, el: X.Elem) -> list[Var]:
        """Переменные структурной части TC6 (interface/*Vars/variable, globalVars/variable)."""
        out: list[Var] = []
        lists: list[tuple[str, X.Elem]] = []
        if el.tag == "globalVars":
            lists.append(("VAR_GLOBAL", el))
        else:
            itf = el.child("interface")
            if itf is not None:
                for lst in itf.children:
                    section = {
                        "localVars": "VAR",
                        "tempVars": "VAR_TEMP",
                        "inputVars": "VAR_INPUT",
                        "outputVars": "VAR_OUTPUT",
                        "inOutVars": "VAR_IN_OUT",
                        "externalVars": "VAR_EXTERNAL",
                        "globalVars": "VAR_STAT",
                    }.get(lst.tag)
                    if section:
                        lists.append((section, lst))
        for section, lst in lists:
            flags = {k for k in ("retain", "persistent", "constant") if lst.attrs.get(k) == "true"}
            for v in lst.kids("variable"):
                out.append(
                    Var(
                        name=v.attrs.get("name", ""),
                        type_text=_type_text(v.child("type")),
                        section=section,
                        address=v.attrs.get("address"),
                        retain="retain" in flags,
                        persistent="persistent" in flags,
                        constant="constant" in flags,
                        elem=v,
                        line=v.line,
                    )
                )
        return out

    # -- тела ------------------------------------------------------------
    def body(self, el: X.Elem, owner: str) -> Body | None:
        b = el.child("body")
        if b is None:
            return None
        lang_el = None
        for c in b.children:
            if c.tag in LANG_TAGS:
                lang_el = c
                break
        vendor = None
        vendor_el = None
        add = b.child("addData")
        if add is not None:
            for d in add.kids("data"):
                short = _short(d.attrs.get("name", ""))
                if short == "cfc" or short.lower() in LD20_HINTS or short not in KNOWN_DATA:
                    vendor, vendor_el = short, d
                    break
        if lang_el is None and vendor_el is None:
            return Body("NONE", b)
        tag = lang_el.tag if lang_el is not None else ""
        if tag in ("ST", "IL"):
            x = lang_el.child("xhtml") if lang_el is not None else None
            text_empty = x is None or not x.text.strip()
            if vendor_el is not None and text_empty:
                if vendor == "cfc":
                    body = Body("CFC", b, vendor_el.child("CFC") or vendor_el, vendor="cfc")
                    self.graph_refs(body, body.lang_elem or vendor_el)
                    return body
                lang = "LD20" if vendor and vendor.lower() in LD20_HINTS else "UNKNOWN"
                return Body(lang, b, vendor_el, vendor=vendor)
            body = Body(tag, b, lang_el)
            if x is not None:
                body.code = self.code("il" if tag == "IL" else "body", x, owner)
            return body
        body = Body(tag or "UNKNOWN", b, lang_el, vendor=vendor)
        if lang_el is not None:
            self.graph_refs(body, lang_el)
        return body

    def graph_refs(self, body: Body, root: X.Elem) -> None:
        networks: set[int] = set()
        for el in root.iter():
            lid = el.attrs.get("localId")
            net = None
            if lid and lid.isdigit():
                net = int(lid) // 10**10 if len(lid) > 10 else None
                if net is not None:
                    networks.add(net)
            if el.tag == "block":
                body.refs.append(
                    GRef("block", el.attrs.get("typeName", ""), el, "typeName", lid, net, el.attrs.get("instanceName"))
                )
            elif el.tag in ("inVariable", "outVariable", "inOutVariable"):
                ex = el.child("expression")
                if ex is not None and ex.text.strip():
                    body.refs.append(GRef("var", ex.text.strip(), el, None, lid, net, text_elem=ex))
            elif el.tag in ("contact", "coil"):
                v = el.child("variable")
                if v is not None and v.text.strip():
                    body.refs.append(GRef(el.tag, v.text.strip(), el, None, lid, net, text_elem=v))
            elif el.tag == "step":
                body.refs.append(GRef("step", el.attrs.get("name", ""), el, "name", lid, net))
            elif el.tag == "transition" and root.tag == "SFC":
                cond = el.child("condition")
                ref = cond.child("reference") if cond is not None else None
                if ref is not None:
                    body.refs.append(GRef("transition", ref.attrs.get("name", ""), ref, "name", lid, net))
            elif el.tag == "action" and el.parent is not None and el.parent.tag == "actionBlock":
                ref = el.child("reference")
                if ref is not None:
                    body.refs.append(GRef("action", ref.attrs.get("name", ""), ref, "name", lid, net))
            elif el.tag == "jumpStep":
                body.refs.append(GRef("jump", el.attrs.get("targetName", ""), el, "targetName", lid, net))
        body.networks = len(networks)

    # -- объекты ---------------------------------------------------------
    def pou(self, el: X.Elem, placement: str, parent: Pou | None = None, kind: str | None = None) -> Pou:
        name = el.attrs.get("name", "")
        k = kind or el.attrs.get("pouType", "unknown")
        owner = name if parent is None else f"{parent.path}.{name}"
        pou = Pou(name, k, el, placement, parent, origin=self.origin(el))
        pou.object_id = self.object_id(el)
        decls = self.plaintexts(el, owner)
        pou.decl = decls[0] if decls else None
        pou.decl_copies = decls
        pou.vars = self.vars_from_text(pou.decl) if pou.decl else self.vars_from_structure(el)
        if pou.decl is not None:
            hdr = st.parse_header(pou.decl.text)
            if hdr is not None:
                pou.extends = hdr.extends[0] if hdr.extends else None
                pou.implements = list(hdr.implements)
                pou.return_type = hdr.return_type
        pou.body = self.body(el, owner)
        actions = el.child("actions")
        if actions is not None:
            for a in actions.kids("action"):
                pou.children.append(self.pou(a, "nested", pou, "action"))
        trans = el.child("transitions")
        if trans is not None:
            for t in trans.kids("transition"):
                pou.children.append(self.pou(t, "nested", pou, "transition"))
        for d in el.datas("method"):
            for m in d.kids("Method"):
                pou.children.append(self.pou(m, "nested", pou, "method"))
        for d in el.datas("property"):
            for pr in d.kids("Property"):
                pou.children.append(self.prop(pr, pou))
        self.note_unknown(el)
        return pou

    def prop(self, el: X.Elem, parent: Pou) -> Pou:
        pr = self.pou(el, "nested", parent, "property")
        for tag, kind in (("GetAccessor", "get"), ("SetAccessor", "set")):
            acc = el.child(tag)
            if acc is not None:
                a = Pou(kind.capitalize(), kind, acc, "nested", pr, origin=self.origin(acc))
                decls = self.plaintexts(acc, f"{pr.path}.{kind}")
                a.decl = decls[0] if decls else None
                a.decl_copies = decls
                a.body = self.body(acc, f"{pr.path}.{kind}")
                pr.children.append(a)
        return pr

    def interface(self, el: X.Elem, placement: str) -> Pou:
        itf = Pou(el.attrs.get("name", ""), "interface", el, placement, origin=self.origin(el))
        itf.object_id = self.object_id(el)
        decls = self.plaintexts(el, itf.name)
        itf.decl = decls[0] if decls else None
        itf.decl_copies = decls
        inh = el.child("Inheritance")
        if inh is not None:
            ext = inh.child("Extends")
            if ext is not None:
                itf.extends = ext.text.strip()
        methods = el.child("Methods")
        if methods is not None:
            for m in methods.kids("Method"):
                itf.children.append(self.pou(m, "nested", itf, "method"))
        props = el.child("Properties")
        if props is not None:
            for pr in props.kids("Property"):
                itf.children.append(self.prop(pr, itf))
        return itf

    def gvl(self, el: X.Elem, placement: str) -> Gvl:
        g = Gvl(el.attrs.get("name", ""), el, placement, origin=self.origin(el))
        g.object_id = self.object_id(el)
        decls = self.plaintexts(el, g.name)
        g.decl = decls[0] if decls else None
        g.decl_copies = decls
        g.persistent = el.attrs.get("persistent") == "true"
        g.constant = el.attrs.get("constant") == "true"
        g.vars = self.vars_from_text(g.decl) if g.decl else self.vars_from_structure(el)
        if g.decl is None:
            mixed = el.data("mixedattrsvarlist")
            if mixed is not None:
                for sub in mixed.iter("globalVars"):
                    if sub is not mixed:
                        g.vars.extend(self.vars_from_structure(sub))
        ad = el.data("attributes")
        if ad is not None:
            for a in ad.iter("Attribute"):
                g.attributes.append(a.attrs.get("Name", ""))
        return g

    def dut(self, el: X.Elem, placement: str) -> Dut:
        base = el.child("baseType")
        kind = "unknown"
        if base is not None and base.children:
            first = base.children[0].tag
            kind = {"struct": "struct", "enum": "enum", "union": "union"}.get(first, "alias")
        if el.tag == "union":
            kind = "union"
        d = Dut(el.attrs.get("name", ""), el, kind, placement=placement, origin=self.origin(el))
        decls = self.plaintexts(el, d.name)
        d.decl = decls[0] if decls else None
        return d

    def task(self, el: X.Elem, resource: str) -> Task:
        prio_raw = el.attrs.get("priority")
        try:
            prio = int(prio_raw) if prio_raw is not None else None
        except ValueError:
            prio = None
        settings = None
        kind = "Cyclic" if el.attrs.get("interval") else "unknown"
        interval_raw = el.attrs.get("interval")
        interval = parse_interval_ms(interval_raw)
        d = el.data("tasksettings")
        if d is not None:
            settings = d.child("TaskSettings")
            if settings is not None:
                kind = settings.attrs.get("KindOfTask", kind)
                raw = settings.attrs.get("Interval")
                if raw:
                    interval_raw = raw
                    interval = parse_interval_ms(raw, settings.attrs.get("IntervalUnit"))
        if el.attrs.get("single") is not None and kind == "unknown":
            kind = "Event"
        t = Task(
            el.attrs.get("name", ""),
            el,
            prio,
            interval,
            interval_raw,
            kind,
            settings_elem=settings,
            resource=resource,
            origin=self.origin(el),
        )
        for pi in el.kids("pouInstance"):
            t.pous.append(pi.attrs.get("name", ""))
        return t

    def libraries(self, d: X.Elem) -> None:
        libs = d.child("Libraries")
        if libs is None:
            return
        self.p.libraries_elem = libs
        for lib in libs.kids("Library"):
            name = lib.attrs.get("Name", "")
            title, version, company = parse_libname(name)
            self.p.libraries.append(
                LibRef(
                    name,
                    lib,
                    lib.attrs.get("Namespace"),
                    lib.attrs.get("DefaultResolution"),
                    name.startswith("#"),
                    title,
                    version,
                    company,
                    self.origin(lib),
                )
            )

    def device(self, d: X.Elem, name: str, parent: Device | None) -> Device | None:
        dev_el = d.child("Device")
        if dev_el is None:
            return None
        ident = None
        dtype = dev_el.child("DeviceType")
        if dtype is not None:
            ident = dtype.child("DeviceIdentification")

        def txt(tag: str) -> str:
            c = ident.child(tag) if ident is not None else None
            return c.text.strip() if c is not None else ""

        dev = Device(name, txt("Type"), txt("Id"), txt("Version"), d, parent, origin=self.origin(d))
        if dtype is not None:
            for con in dtype.kids("Connector"):
                dev.connectors.append(con.attrs.get("interface", ""))
            for prm in dtype.iter("Parameter"):
                dev.parameters += 1
                mp = prm.child("Mapping")
                if mp is not None and mp.text.strip():
                    nm = prm.child("Name")
                    at = prm.child("Attributes")
                    dev.mappings.append(
                        Mapping(
                            mp.text.strip(),
                            nm.text.strip() if nm is not None else prm.attrs.get("ParameterId", ""),
                            at.attrs.get("channel") if at is not None else None,
                            prm.attrs.get("type"),
                            mp,
                        )
                    )
        return dev

    def devices_under(self, holder: X.Elem, parent: Device | None, holder_name: str) -> list[Device]:
        """Устройства в addData элемента configuration: свой Device и вложенные configurations."""
        out: list[Device] = []
        own = holder.data("Device")
        current = parent
        if own is not None:
            dev = self.device(own, holder_name, parent)
            if dev is not None:
                if parent is not None:
                    parent.children.append(dev)
                else:
                    out.append(dev)
                current = dev
        confs = holder.data("configurations")
        if confs is not None:
            box = confs.child("configurations")
            for c in box.kids("configuration") if box is not None else []:
                out.extend(self.devices_under(c, current, c.attrs.get("name", "")))
        return out

    # -- контейнеры ------------------------------------------------------
    def container(self, el: X.Elem, placement: str) -> None:
        """Общий обход: pou/dataType/globalVars/task напрямую и в addData."""
        found = False
        for c in el.children:
            if c.tag == "pou":
                self.p.pous.append(self.pou(c, placement))
                found = True
            elif c.tag == "dataType":
                self.p.duts.append(self.dut(c, placement))
                found = True
            elif c.tag == "globalVars":
                self.p.gvls.append(self.gvl(c, placement))
                found = True
            elif c.tag == "task":
                self.p.tasks.append(self.task(c, el.attrs.get("name", "")))
        add = el.child("addData")
        if add is not None:
            for d in add.kids("data"):
                short = _short(d.attrs.get("name", ""))
                if short == "pou":
                    for c in d.kids("pou"):
                        self.p.pous.append(self.pou(c, placement))
                        found = True
                elif short == "datatype":
                    for c in d.kids("dataType"):
                        self.p.duts.append(self.dut(c, placement))
                        found = True
                elif short == "union":
                    for c in d.kids("union"):
                        self.p.duts.append(self.dut(c, placement))
                        found = True
                elif short == "interface":
                    for c in d.kids("Interface"):
                        self.p.pous.append(self.interface(c, placement))
                        found = True
                elif short == "globalvars":
                    for c in d.kids("globalVars"):
                        self.p.gvls.append(self.gvl(c, placement))
                        found = True
                elif short == "libraries":
                    self.libraries(d)
                elif short == "projectstructure":
                    self.p.structure = d
                elif short not in KNOWN_DATA:
                    self.p.unknown.append(UnknownData(d.attrs.get("name", ""), d, d.path()))
        if found and placement not in self.p.placements:
            self.p.placements.append(placement)

    def run(self) -> Project:
        root = self.doc.root
        fh = root.child("fileHeader")
        if fh is not None:
            self.p.company = fh.attrs.get("companyName")
            self.p.product = fh.attrs.get("productName")
            self.p.product_version = fh.attrs.get("productVersion")
        ch = root.child("contentHeader")
        if ch is not None:
            self.p.project_name = ch.attrs.get("name")
        types = root.child("types")
        if types is not None:
            for sec in types.children:
                self.container(sec, "types")
        self.container(root, "types")
        # project/addData/data[application]/resource — экспорт узла приложения (CODESYS), форма TwinCAT
        app = root.data("application")
        if app is not None:
            for res in app.kids("resource"):
                self.p.resources.append(res.attrs.get("name", ""))
                self.container(res, "application")
            if self.p.product and "twincat" in self.p.product.lower():
                self.p.issues.append(
                    Issue(
                        "C2A-IMP-TC", "экспорт TwinCAT: размещение project/addData/application распознано, не проверено"
                    )
                )
        inst = root.child("instances")
        confs = inst.child("configurations") if inst is not None else None
        for conf in confs.kids("configuration") if confs is not None else []:
            cname = conf.attrs.get("name", "")
            self.p.configurations.append(cname)
            for res in conf.kids("resource"):
                self.p.resources.append(res.attrs.get("name", ""))
                self.container(res, "resource")
            self.p.devices.extend(self.devices_under(conf, None, cname))
        if not self.p.has_plaintext and (self.p.pous or self.p.gvls or self.p.duts):
            self.p.issues.append(
                Issue(
                    "C2A-FMT001",
                    "во входе нет текстов объявлений (interfaceasplaintext): часть объявлений восстановлена из "
                    "структуры TC6 с потерями",
                    severity="info",
                )
            )
        return self.p


def _attributes_before(tokens: list[st.Token], index: int) -> list[str]:
    out: list[str] = []
    j = index - 1
    while j >= 0 and tokens[j].kind in st.TRIVIA:
        if tokens[j].kind == st.TK_PRAGMA:
            out.append(tokens[j].text)
        j -= 1
    out.reverse()
    return out


def _type_text(t: X.Elem | None) -> str:
    """Тип из структуры TC6 в текст ST (derived, string(len), array, pointer)."""
    if t is None or not t.children:
        return ""
    c = t.children[0]
    if c.tag == "derived":
        return c.attrs.get("name", "")
    if c.tag in ("string", "wstring"):
        length = c.attrs.get("length")
        base = c.tag.upper()
        return f"{base}({length})" if length else base
    if c.tag == "array":
        dims = ", ".join(f"{d.attrs.get('lower', '')}..{d.attrs.get('upper', '')}" for d in c.kids("dimension"))
        return f"ARRAY [{dims}] OF {_type_text(c.child('baseType'))}"
    if c.tag == "pointer":
        return f"POINTER TO {_type_text(c.child('baseType'))}"
    return c.tag


def load(raw: bytes, file: str = "<вход>") -> Project:
    """Байты PLCopen XML -> Project. Не XML или не TC6 -> ImportError_ / xmltree.XmlError."""
    doc = X.parse(raw)
    return _Importer(doc, file).run()
