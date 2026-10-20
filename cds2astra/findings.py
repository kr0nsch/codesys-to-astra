"""Находки и исходы.

Родные исходы проекта: auto | check | todo | impossible | info (маркеры s7conv `MIGRATION-CHECK` /
`MIGRATION-TODO`). В JSON рядом — `family_outcome` по словарю семейства (00-INDEX §4.1):
check -> review, если поведение цели описано (статус профиля documented / observed_in_sample /
verified_local / owner_verified), и verify — при unknown или пробе; todo -> manual; остальные как есть.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

OUTCOMES = ("auto", "check", "todo", "impossible", "info")
FAMILY = ("auto", "review", "verify", "manual", "impossible", "info")
# тяжесть для «одна находка на место» и --fail-on
SEVERITY = {"info": 0, "auto": 1, "check": 2, "todo": 3, "impossible": 4}
FAMILY_SEVERITY = {"info": 0, "auto": 1, "review": 2, "verify": 3, "manual": 4, "impossible": 5}
LANGS = ("ST", "IL", "LD", "FBD", "CFC", "SFC", "DECL", "PROJECT")


def family_outcome(outcome: str, described: bool) -> str:
    if outcome == "check":
        return "review" if described else "verify"
    if outcome == "todo":
        return "manual"
    return outcome


@dataclass
class Finding:
    rule: str
    outcome: str
    language: str
    message: str
    file: str
    line: int = 0
    column: int = 0
    pou: str | None = None
    local_id: str | None = None
    described: bool = True
    related: list[str] = field(default_factory=list)
    source_ref: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"исход {self.outcome!r} не из {OUTCOMES}")
        if self.language not in LANGS:
            raise ValueError(f"язык {self.language!r} не из {LANGS}")

    @property
    def family(self) -> str:
        return family_outcome(self.outcome, self.described)

    @property
    def sort_key(self) -> tuple[str, int, int, str, str]:
        return (self.file, self.line, self.column, self.rule, self.message)


def at_least(outcome: str, threshold: str) -> bool:
    """Исход не ниже порога --fail-on (todo | check | never)."""
    if threshold == "never":
        return False
    return SEVERITY[outcome] >= SEVERITY[threshold]
