"""IL -> ST для подмножества (C2A-LANG-IL): импорт <IL> не работает ни в Astra.IDE 1.7.2.2, ни в CODESYS
3.5.17.30 (проба P4), поэтому тело на IL переписывается в ST.

Поддержано: LD/LDN, ST/STN, S, R, AND/ANDN/OR/ORN/XOR/XORN, NOT, ADD/SUB/MUL/DIV/MOD, GT/GE/EQ/NE/LE/LT,
JMP/JMPC/JMPCN, CAL/CALC/CALCN, RET/RETC/RETCN, метки. Текущий результат ведётся как выражение ST
(символьно), присваивания появляются на ST/S/R/CAL/JMP/RET. Скобочные операции `AND(` … `)`, после метки
не LD, неизвестные операторы -> неподдержано (todo), перевод не выполняется.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_LINE_RE = re.compile(r"^\s*(?:(?P<label>[A-Za-z_][A-Za-z0-9_]*)\s*:)?\s*(?P<op>[A-Za-z]+)?\s*(?P<arg>.*?)\s*$")
_COMMENT_RE = re.compile(r"\(\*.*?\*\)|//.*$")
LOGIC = {"AND": "AND", "OR": "OR", "XOR": "XOR"}
ARITH = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "MOD"}
CMP = {"GT": ">", "GE": ">=", "EQ": "=", "NE": "<>", "LE": "<=", "LT": "<"}


@dataclass
class IlResult:
    ok: bool
    st: str
    unsupported: list[tuple[int, str]] = field(default_factory=list)


def _atom(expr: str) -> bool:
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\[\]^]*|[-+]?[0-9.#A-Za-z_]+|'[^']*'|TRUE|FALSE", expr) is not None


def _wrap(expr: str) -> str:
    return expr if _atom(expr) else f"({expr})"


def translate(il: str) -> IlResult:
    out: list[str] = []
    bad: list[tuple[int, str]] = []
    cr: str | None = None
    after_label = False
    for no, raw in enumerate(il.splitlines(), start=1):
        line = _COMMENT_RE.sub("", raw).strip()
        if not line:
            continue
        m = _LINE_RE.match(line)
        if m is None:
            bad.append((no, raw.strip()))
            continue
        label, op, arg = m.group("label"), (m.group("op") or "").upper(), m.group("arg").strip()
        if label:
            out.append(f"{label}:")
            cr = None
            after_label = True
        if not op:
            continue
        if arg.endswith("(") or arg[:1] == "(" or op.endswith("("):
            bad.append((no, raw.strip()))
            continue
        neg = (
            op.endswith("N")
            and op not in ("RETCN",)
            and op[:-1] in ("LD", "ST", "AND", "OR", "XOR", "JMPC", "CALC", "RETC")
        )
        base = op[:-1] if neg else op
        if after_label and base not in ("LD", "JMP", "RET", "CAL"):
            bad.append((no, raw.strip()))
            continue
        after_label = False
        operand = f"NOT {_wrap(arg)}" if neg and base in ("LD", "AND", "OR", "XOR") else arg
        if base == "LD":
            cr = operand
        elif base == "ST":
            if cr is None:
                bad.append((no, raw.strip()))
                continue
            out.append(f"{arg} := {'NOT ' + _wrap(cr) if neg else cr};")
        elif base in ("S", "R") and not neg:
            if cr is None:
                bad.append((no, raw.strip()))
                continue
            out.append(f"IF {cr} THEN {arg} := {'TRUE' if base == 'S' else 'FALSE'}; END_IF;")
        elif base in LOGIC:
            if cr is None:
                bad.append((no, raw.strip()))
                continue
            cr = f"{_wrap(cr)} {LOGIC[base]} {_wrap(operand) if neg else operand}"
        elif base == "NOT" and not arg:
            if cr is None:
                bad.append((no, raw.strip()))
                continue
            cr = f"NOT {_wrap(cr)}"
        elif base in ARITH and not neg:
            if cr is None:
                bad.append((no, raw.strip()))
                continue
            cr = f"{_wrap(cr)} {ARITH[base]} {_wrap(arg)}"
        elif base in CMP and not neg:
            if cr is None:
                bad.append((no, raw.strip()))
                continue
            cr = f"{_wrap(cr)} {CMP[base]} {_wrap(arg)}"
        elif op in ("JMP", "JMPC", "JMPCN"):
            if op == "JMP":
                out.append(f"JMP {arg};")
            else:
                cond = cr if op == "JMPC" else f"NOT {_wrap(cr or 'FALSE')}"
                out.append(f"IF {cond} THEN JMP {arg}; END_IF;")
        elif op in ("CAL", "CALC", "CALCN"):
            call = arg if arg.endswith(")") else f"{arg}()"
            if op == "CAL":
                out.append(f"{call};")
            else:
                cond = cr if op == "CALC" else f"NOT {_wrap(cr or 'FALSE')}"
                out.append(f"IF {cond} THEN {call}; END_IF;")
        elif op in ("RET", "RETC", "RETCN"):
            if op == "RET":
                out.append("RETURN;")
            else:
                cond = cr if op == "RETC" else f"NOT {_wrap(cr or 'FALSE')}"
                out.append(f"IF {cond} THEN RETURN; END_IF;")
        else:
            bad.append((no, raw.strip()))
    return IlResult(not bad, "\n".join(out) + ("\n" if out else ""), bad)
