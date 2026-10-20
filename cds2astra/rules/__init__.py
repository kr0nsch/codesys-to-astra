"""Правила платформы C2A-* и их порядок выполнения."""

from __future__ import annotations

import re

from ..session import Session
from . import lang_rules, project_rules, st_rules
from .registry import RULES, RuleInfo

__all__ = ["RULES", "RuleInfo", "is_sp18plus", "run_all"]

_SP_RE = re.compile(r"SP\s?(\d+)|3\.5\.(\d+)\.", re.IGNORECASE)


def is_sp18plus(product_version: str | None) -> bool:
    """Вход из CODESYS SP18–SP21 (по productVersion fileHeader)."""
    if not product_version:
        return False
    if "astra" in product_version.lower():
        return False
    for m in _SP_RE.finditer(product_version):
        n = int(m.group(1) or m.group(2))
        if n >= 18:
            return True
    return False


def run_all(s: Session) -> None:
    """Все правила по порядку; правки копятся в сеансе, применяются эмиттером."""
    p = s.project
    for pou in p.all_pous():
        s.register_decl_copies(pou.decl_copies)
    for g in p.gvls:
        s.register_decl_copies(g.decl_copies)
    sp18 = is_sp18plus(p.product_version)
    st_rules.mark(s)
    lang_rules.lang(s)
    st_rules.lib001(s)
    st_rules.io001(s)
    st_rules.sp18_utf8(s, sp18)
    st_rules.sp18_generic(s)
    st_rules.sp19_bit(s)
    st_rules.ret001(s)
    st_rules.sym001(s)
    st_rules.ptr001(s)
    st_rules.red001(s)
    st_rules.oop(s)
    project_rules.task001(s)
    project_rules.task002(s)
    project_rules.lib002(s)
    project_rules.devices(s)
    project_rules.fmt001(s)
