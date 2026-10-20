"""Данные пакета (профили, таблицы замен, карты модулей, схемы) — через importlib.resources.

Так данные читаются одинаково из рабочей копии, из установленного колеса и в Pyodide.
"""

from __future__ import annotations

import json
import tomllib
from importlib import resources
from typing import Any

_PKG = "cds2astra"


def _node(*parts: str) -> Any:
    node = resources.files(_PKG)
    for p in parts:
        node = node.joinpath(p)
    return node


def read_text(*parts: str) -> str:
    return str(_node(*parts).read_text(encoding="utf-8"))


def read_toml(*parts: str) -> dict[str, Any]:
    return tomllib.loads(read_text(*parts))


def read_json(*parts: str) -> Any:
    return json.loads(read_text(*parts))


def list_dir(*parts: str) -> list[str]:
    node = _node(*parts)
    return sorted(p.name for p in node.iterdir() if p.is_file())
