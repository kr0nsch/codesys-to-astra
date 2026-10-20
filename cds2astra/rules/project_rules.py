"""Правила уровня проекта: задачи, библиотеки, устройства и ввод-вывод, Modbus, исключения."""

from __future__ import annotations

import re
from typing import Any

from .. import resources
from ..ir.model import Device, Mapping
from ..session import Session
from ..tasks import TaskIn, reassign

MX210_RE = re.compile(r"M([VUKD])210[-_ ]?(\d{3})", re.IGNORECASE)
REGUL_TYPES = {"4096"} | {str(t) for t in range(40000, 51000)}
OWEN_STANDARD = re.compile(r"^Standard$", re.IGNORECASE)
REGLAB_RENAMES = {
    # DPA-302 прил. Л: с 1.7.2.0 у EXTERNAL-функций библиотек РегЛаб — префикс компонента (примеры из документа)
    "timestampnow": "PsLogTimeStampNow",
    "getmode": "PsRddRtGetMode",
}
NEWER_LIBS = re.compile(r"String Libraries|IIoT Libraries|StringUtils SL|Generic String", re.IGNORECASE)


def _version_tuple(v: str | None) -> tuple[int, ...]:
    if not v:
        return ()
    out = []
    for part in v.split("."):
        if part.isdigit():
            out.append(int(part))
        else:
            break
    return tuple(out)


# --------------------------------------------------------------------------- TASK001 / TASK002
def task001(s: Session) -> None:
    p = s.project
    if not p.tasks:
        return
    ins = [TaskIn(t.name, t.priority, t.kind, t.interval_ms) for t in p.tasks]
    outs = reassign(ins, s.target, s.spec.redundancy, s.spec.cpu_type, s.spec.sync_task)
    collisions = [o.name for o in outs if o.collision]
    for t, o in zip(p.tasks, outs, strict=True):
        row = {
            "task": t.name,
            "kind": t.kind,
            "interval_ms": t.interval_ms,
            "interval_raw": t.interval_raw,
            "before": o.before,
            "after": o.after,
            "reason": o.reason,
            "pous": list(t.pous),
        }
        s.task_table.append(row)
        line = t.origin.line if t.origin else 0
        if o.before == o.after:
            s.add(
                "C2A-TASK001",
                "info",
                "PROJECT",
                f"задача {t.name}: приоритет {o.after} без изменений",
                line,
                None,
                status_key="tasks.priority_max",
                data=row,
            )
        else:
            extra = f"; совпадение уровней: {', '.join(collisions)}" if o.collision else ""
            s.add(
                "C2A-TASK001",
                "check",
                "PROJECT",
                f"задача {t.name}: приоритет {o.before} -> {o.after} ({o.reason}){extra}",
                line,
                None,
                status_key="tasks.priority_max",
                data=row,
            )


def task002(s: Session) -> None:
    p = s.project
    bus = s.spec.bus_cycle_ms
    io_pous = _pous_with_io(s)
    for t in p.tasks:
        line = t.origin.line if t.origin else 0
        if t.kind.lower() in ("freewheeling", "free") and any(x.lower() in io_pous for x in t.pous):
            s.add(
                "C2A-TASK002",
                "check",
                "PROJECT",
                f"свободная задача {t.name} обновляет ввод-вывод: на REGUL — циклическая",
                line,
                None,
            )
        if t.interval_ms is not None and t.kind.lower() == "cyclic" and t.interval_ms < bus:
            s.add(
                "C2A-TASK002",
                "check",
                "PROJECT",
                f"задача {t.name} ({t.interval_ms} мс) быстрее цикла RegulBus ({bus} мс)",
                line,
                None,
            )
    max_tasks = int(s.target.value("tasks.max_tasks", 100))
    if len(p.tasks) > max_tasks:
        s.add(
            "C2A-TASK002",
            "todo",
            "PROJECT",
            f"задач {len(p.tasks)} > {max_tasks}",
            0,
            None,
            status_key="tasks.max_tasks",
        )
    apps = sorted(set(p.resources))
    if len(apps) > int(s.target.value("memory.max_apps", 1)):
        s.add(
            "C2A-TASK002",
            "todo",
            "PROJECT",
            f"приложений {len(apps)} ({', '.join(apps)}), на ЦП REGUL — одно",
            0,
            None,
            status_key="memory.max_apps",
        )


def _pous_with_io(s: Session) -> set[str]:
    out: set[str] = set()
    names = {
        m.variable.split(".")[-2].lower() for d in s.project.all_devices() for m in d.mappings if "." in m.variable
    }
    for pou in s.project.pous:
        text = (pou.body.code.text if pou.body and pou.body.code else "").lower()
        if any(n in text for n in names) or any(v.address for v in pou.vars):
            out.add(pou.name.lower())
    return out


# --------------------------------------------------------------------------- LIB002 / SPxx-LIB
def lib002(s: Session) -> None:
    used_ns = _used_namespaces(s)
    for lib in s.project.libraries:
        line = lib.origin.line if lib.origin else 0
        vendor = s.libmap.vendor_library(lib.title)
        ver = _version_tuple(lib.version)
        if vendor is not None:
            s.add(
                "C2A-LIB002",
                "info",
                "PROJECT",
                f"{lib.name}: библиотека ОВЕН не переносится (замены — AstraCompat)",
                line,
                None,
                data={"library": lib.name},
            )
        elif NEWER_LIBS.search(lib.title) or (ver and ver[:3] > (3, 5, 17) and lib.company in ("System", "CODESYS")):
            s.add(
                "C2A-SPxx-LIB",
                "todo",
                "PROJECT",
                f"{lib.name}: библиотека новее компилятора 3.5.17",
                line,
                None,
                data={"library": lib.name},
            )
        elif OWEN_STANDARD.match(lib.title) and ver[:3] == (3, 5, 9):
            s.add("C2A-LIB002", "auto", "PROJECT", f"{lib.name} (Standard ОВЕН) -> плейсхолдер #Standard", line, None)
        elif (
            lib.namespace
            and lib.namespace.lower() not in used_ns
            and not lib.placeholder
            and lib.company not in ("Prosoft-Systems Ltd", "RegLab")
        ):
            s.add("C2A-LIB002", "info", "PROJECT", f"{lib.name}: не используется в коде — не переносится", line, None)
    # РегЛаб до 1.7.2.0: старые имена внешних функций
    for code, pou, _kind in _codes(s):
        low = code.text.lower()
        for old, new in REGLAB_RENAMES.items():
            idx = low.find(old + "(")
            if idx >= 0 and (idx == 0 or not (low[idx - 1].isalnum() or low[idx - 1] in "_.")):
                s.edit(code, idx, idx + len(old), new, "C2A-LIB002")
                s.add(
                    "C2A-LIB002",
                    "auto",
                    "ST",
                    f"{old} -> {new} (переименование РегЛаб 1.7.2.0, DPA-302 прил. Л)",
                    code.line_of(idx),
                    pou.path if pou else None,
                )


def _codes(s: Session) -> list[Any]:
    from ..session import all_codes

    return all_codes(s.project)


def _used_namespaces(s: Session) -> set[str]:
    used: set[str] = set()
    for code, _p, _k in _codes(s):
        for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*\.", code.text):
            used.add(m.group(1).lower())
    for pou in s.project.all_pous():
        if pou.body:
            for r in pou.body.refs:
                if "." in r.name:
                    used.add(r.name.split(".")[0].lower())
    return used


# --------------------------------------------------------------------------- устройства
def _is_regul(dev: Device) -> bool:
    return dev.type in REGUL_TYPES and dev.id.upper().startswith("109B")


def _owen_nodes() -> dict[str, Any]:
    data: dict[str, Any] = resources.read_toml("data", "owen_modules.toml")
    return data


def _strip_app(var: str) -> str:
    return var.split(".", 1)[1] if var.lower().startswith("application.") else var


def devices(s: Session) -> None:
    """IO002 / IO003 / IO004 / MB001 / EXC001 по дереву устройств источника (если оно есть)."""
    data = _owen_nodes()
    nodes: dict[str, Any] = data["nodes"]
    modules: dict[str, Any] = data["modules"]
    for dev in s.project.all_devices():
        if _is_regul(dev):
            continue
        name = dev.name
        line = dev.origin.line if dev.origin else 0
        node = next((k for k in nodes if name.lower().startswith(k.lower())), None)
        mx = MX210_RE.search(name)
        if node is not None:
            _target_node(s, dev, node, nodes[node], line)
        elif mx is not None:
            model = f"M{mx.group(1).upper()}210-{mx.group(2)}"
            _mx210(s, dev, model, modules.get(model), line)
        elif "modbus" in name.lower() or any("modbus" in c.lower() for c in dev.connectors):
            _modbus3s(s, dev, line)
    _io_update_header(s)


def _target_node(s: Session, dev: Device, node: str, spec: dict[str, Any], line: int) -> None:
    page = spec.get("page")
    if node == "OwenRTC":
        outputs: dict[str, str] = spec.get("outputs", {})
        if dev.mappings and "    fbC2aRtc : FB_C2aRtc; // замена узла OwenRTC (C2A-IO002)" not in s.io_update_decl:
            s.io_update_decl.append("    fbC2aRtc : FB_C2aRtc; // замена узла OwenRTC (C2A-IO002)")
            s.io_update_body.append("fbC2aRtc();")
        for m in dev.mappings:
            var = _strip_app(m.variable)
            out = outputs.get(m.parameter)
            if out:
                s.io_update_body.append(f"{var} := fbC2aRtc.{out}; // OwenRTC «{m.parameter}»")
                s.io_map.append(_row(m, var, f"OwenRTC «{m.parameter}»", "FB_C2aRtc." + out, "check", "C2A-IO002"))
                s.add(
                    "C2A-IO002",
                    "check",
                    "PROJECT",
                    f"{var} <- OwenRTC «{m.parameter}» -> FB_C2aRtc.{out}",
                    m.elem.line,
                    None,
                    source_ref=f"{spec.get('doc')} с. {page}",
                )
            else:
                s.io_map.append(_row(m, var, f"OwenRTC «{m.parameter}»", "—", "todo", "C2A-IO002"))
                s.add(
                    "C2A-IO002",
                    "todo",
                    "PROJECT",
                    f"{var} <- OwenRTC «{m.parameter}»: канала в FB_C2aRtc нет",
                    m.elem.line,
                    None,
                )
        return
    kind = spec.get("kind")
    note = spec.get("note", "")
    if node == "Watchdog":
        s.add(
            "C2A-EXC001",
            "todo",
            "PROJECT",
            "узел Watchdog: обработка исключений на REGUL — системные события задач и PsSysExcept (каркас — "
            "IMPORT_STEPS, DPA-302 прил. И)",
            line,
            None,
        )
    for m in dev.mappings:
        var = _strip_app(m.variable)
        if kind == "module":
            s.io_map.append(
                _row(
                    m,
                    var,
                    f"{node} «{m.parameter}»",
                    "канал модуля REGUL (DI/DO) по мастеру конфигурации",
                    "check",
                    "C2A-IO002",
                )
            )
            s.add(
                "C2A-IO002",
                "check",
                "PROJECT",
                f"{var} <- {node} «{m.parameter}»: встроенный ввод-вывод ПЛК210 -> модуль REGUL",
                m.elem.line,
                None,
            )
        else:
            s.io_map.append(_row(m, var, f"{node} «{m.parameter}»", "—", "todo", "C2A-IO002"))
            s.add(
                "C2A-IO002",
                "todo",
                "PROJECT",
                f"{var} <- {node} «{m.parameter}»: аналога нет ({note})",
                m.elem.line,
                None,
            )


def _row(m: Mapping, var: str, owen: str, regul: str, outcome: str, rule: str, **extra: Any) -> dict[str, Any]:
    row = {
        "source": m.variable,
        "variable": var,
        "type": m.param_type or "",
        "owen": owen,
        "direction": "вход" if (m.channel or "input") == "input" else "выход",
        "regul": regul,
        "outcome": outcome,
        "rule": rule,
    }
    row.update(extra)
    return row


def _ident(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def _mx210(s: Session, dev: Device, model: str, spec: dict[str, Any] | None, line: int) -> None:
    slave = _ident(dev.name)
    if spec is None:
        s.add("C2A-IO003", "todo", "PROJECT", f"{dev.name}: модель {model} нет в data/owen_modules.toml", line, None)
        return
    regs = spec.get("registers", [])
    word_known = s.target.status("modbus.word_order_float32") != "unknown"
    reads: list[tuple[int, int, str, str, str]] = []  # (регистр, слов, тип, переменная, канал)
    writes: list[tuple[int, int, str, str, str]] = []
    for m in dev.mappings:
        var = _strip_app(m.variable)
        hit = None
        for r in regs:
            pattern = re.escape(r["name"]).replace(r"\{n\}", r"(\d+)")
            mm = re.search(pattern + r"$", m.parameter)
            if mm:
                n = int(mm.group(1)) if mm.groups() else 1
                if 1 <= n <= int(r["count"]):
                    hit = (int(r["first"]) + (n - 1) * int(r["step"]), int(r["words"]), str(r["type"]), int(r["page"]))
                break
        if hit is None:
            s.io_map.append(_row(m, var, f"{model} «{m.parameter}»", "—", "todo", "C2A-IO003"))
            s.add(
                "C2A-IO003",
                "todo",
                "PROJECT",
                f"{var} <- {model} «{m.parameter}»: регистр по РЭ не найден",
                m.elem.line,
                None,
            )
            continue
        reg, words, typ, _page = hit
        target = writes if (m.channel or "input") == "output" else reads
        target.append((reg, words, typ, var, m.parameter))
    status_type = str(s.target.value("modbus.status_type_tcp", "PsIoDrvModbusTcpMaster_OS.ChannelStatus"))
    for direction, items in (("read", reads), ("write", writes)):
        tag = "R" if direction == "read" else "W"
        for nblock, block in enumerate(_split_blocks(items)):
            first = min(r for r, _w, _t, _v, _c in block)
            last = max(r + w - 1 for r, w, _t, _v, _c in block)
            length = last - first + 1
            suffix = f"{slave}" if nblock == 0 else f"{slave}_{nblock + 1}"
            arr = f"awMb{tag}_{suffix}"
            status = f"eMbSt{tag}_{suffix}"
            valid = f"x{tag}Valid_{suffix}"
            s.gvl_io.append(
                f"    {arr} : ARRAY [0..{length - 1}] OF WORD; // {model} {dev.name}: регистры {first}..{last}"
            )
            s.gvl_io.append(f"    {status} : {status_type}; // статус канала Modbus (DPA-302.1 с. 15–16)")
            s.gvl_io.append(f"    {valid} : BOOL; // достоверность канала (C2A-IO004)")
            fc = "4 (Read Input Registers)" if direction == "read" else "16 (Write Multiple Registers)"
            ch = f"Modbus TCP Outer Slave OS «{dev.name}»: FC {fc}, смещение {first}, длина {length}, период — цикл задачи"
            ok = f"GVL_IO.{status} = {status_type}.Ok"
            if direction == "read":
                s.io_update_body.append(f"// {model} {dev.name}: регистры {first}..{last} (C2A-IO003, C2A-IO004)")
                s.io_update_body.append(f"GVL_IO.{valid} := {ok};")
                s.io_update_body.append(f"IF GVL_IO.{valid} THEN")
                for reg, words, typ, var, chan in sorted(block):
                    k = reg - first
                    if typ == "REAL" and words == 2:
                        expr = f"F_C2aMbToReal(GVL_IO.{arr}[{k}], GVL_IO.{arr}[{k + 1}], GVL_IO.eC2aWordOrder)"
                    elif typ == "INT":
                        expr = f"WORD_TO_INT(GVL_IO.{arr}[{k}])"
                    elif typ == "UINT":
                        expr = f"WORD_TO_UINT(GVL_IO.{arr}[{k}])"
                    else:
                        expr = f"GVL_IO.{arr}[{k}]"
                    s.io_update_body.append(f"    {var} := {expr}; // «{chan}», регистр {reg}")
                    s.io_map.append(
                        {
                            "source": f"{dev.name}/{chan}",
                            "variable": var,
                            "type": typ,
                            "owen": f"{model} «{chan}»",
                            "direction": "вход",
                            "regul": f"{ch}; слово {k}",
                            "outcome": "check",
                            "rule": "C2A-IO003",
                            "register": reg,
                            "words": words,
                        }
                    )
                    why = "" if word_known else "; порядок слов FLOAT32 unknown — сверить (HARDWARE_VALIDATION)"
                    s.add(
                        "C2A-IO003",
                        "check",
                        "PROJECT",
                        f"{var} <- {model} «{chan}» (рег. {reg}): канал REGUL ARRAY OF WORD{why}",
                        line,
                        None,
                        status_key="modbus.word_order_float32",
                    )
                s.io_update_body.append("END_IF")
                s.add(
                    "C2A-IO004",
                    "check",
                    "PROJECT",
                    f"{dev.name}, регистры {first}..{last}: при отказе канала значения не обновляются "
                    f"(флаг GVL_IO.{valid})",
                    line,
                    None,
                    status_key="modbus.channel_data",
                )
            else:
                s.io_update_body.append(f"// {model} {dev.name}: запись {first}..{last} (C2A-IO003)")
                for reg, _words, typ, var, chan in sorted(block):
                    k = reg - first
                    expr = var if typ == "WORD" else f"TO_WORD({var})"
                    s.io_update_body.append(f"GVL_IO.{arr}[{k}] := {expr}; // «{chan}», регистр {reg}")
                    s.io_map.append(
                        {
                            "source": f"{dev.name}/{chan}",
                            "variable": var,
                            "type": typ,
                            "owen": f"{model} «{chan}»",
                            "direction": "выход",
                            "regul": f"{ch}; слово {k}",
                            "outcome": "check",
                            "rule": "C2A-IO003",
                            "register": reg,
                            "words": 1,
                        }
                    )
                    s.add(
                        "C2A-IO003",
                        "check",
                        "PROJECT",
                        f"{var} -> {model} «{chan}» (рег. {reg}): канал записи REGUL",
                        line,
                        None,
                        status_key="modbus.channel_data",
                    )
                s.io_update_body.append(f"GVL_IO.{valid} := {ok};")
    clients = spec.get("max_clients")
    if clients:
        s.notes.append(
            f"{dev.name}: {model} обслуживает до {clients} клиентов Modbus TCP — резервированная пара, SCADA "
            "и сервисный ПК могут упереться в лимит (конспект §4.3)"
        )


MAX_GAP = 4  # пропуск регистров, при котором блок ещё не делится (чтение несуществующих адресов — ошибка 02)


def _split_blocks(items: list[tuple[int, int, str, str, str]]) -> list[list[tuple[int, int, str, str, str]]]:
    """Регистры -> блоки каналов Modbus: соседние (с пропуском до MAX_GAP) — в один канал, до 120 регистров."""
    blocks: list[list[tuple[int, int, str, str, str]]] = []
    for it in sorted(items):
        if blocks:
            cur = blocks[-1]
            end = max(r + w - 1 for r, w, _t, _v, _c in cur)
            start = min(r for r, _w, _t, _v, _c in cur)
            if it[0] - end - 1 <= MAX_GAP and it[0] + it[1] - start <= 120:
                cur.append(it)
                continue
        blocks.append([it])
    return blocks


def _modbus3s(s: Session, dev: Device, line: int) -> None:
    text = " ".join(m.parameter for m in dev.mappings).lower()
    params = []
    for el in dev.elem.iter("Value"):
        params.append(el.text)
    blob = (text + " " + " ".join(params)).lower()
    if "slave" in dev.name.lower() and "device" not in dev.name.lower():
        s.add(
            "C2A-MB001",
            "todo",
            "PROJECT",
            f"{dev.name}: slave 3S -> PsModbusTcpSlave/PsModbusSerialSlave (области данных — на уровне библиотеки)",
            line,
            None,
            status_key="modbus.channel_data",
        )
        return
    if "23" in blob and ("read/write" in blob or "fc 23" in blob or "fc23" in blob):
        s.add(
            "C2A-MB001",
            "check",
            "PROJECT",
            f"{dev.name}: FC 23 -> ФБ ModbusUserRequest (DPA-302.1 прил. А)",
            line,
            None,
            status_key="modbus.channel_data",
        )
    s.add(
        "C2A-MB001",
        "check",
        "PROJECT",
        f"{dev.name}: Modbus 3S -> Modbus TCP Master OS + Outer Slave OS, каналы Data (ARRAY OF WORD) / Status",
        line,
        None,
        status_key="modbus.channel_data",
    )
    for m in dev.mappings:
        var = _strip_app(m.variable)
        s.io_map.append(
            _row(
                m,
                var,
                f"{dev.name} «{m.parameter}»",
                "канал Modbus TCP Outer Slave OS (Data/Status)",
                "check",
                "C2A-MB001",
            )
        )


def _io_update_header(s: Session) -> None:
    if any("eC2aWordOrder" in line for line in s.gvl_io):
        return
    if any(line.strip().startswith("awMbR_") or "awMbR_" in line for line in s.gvl_io):
        s.gvl_io.insert(
            0,
            "    eC2aWordOrder : E_C2aWordOrder := E_C2aWordOrder.HighWordFirst; "
            "// MIGRATION-CHECK(C2A-IO003): порядок слов FLOAT32 Mx210 через драйвер REGUL не сверен",
        )


def fmt001(s: Session) -> None:
    for issue in s.project.issues:
        if issue.code == "C2A-FMT001":
            s.add(
                "C2A-FMT001",
                "info",
                "PROJECT",
                issue.message + ". Переэкспортируйте с флагом «объявления как простой "
                "текст»: потери TC6 — VAR_INST, ABSTRACT, METHOD FINAL PRIVATE, комментарии, прагмы",
                0,
                None,
            )
