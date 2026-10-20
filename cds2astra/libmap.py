"""Таблица замен POU вендорных библиотек (data/libmap/*.toml) и сигнатуры ОВЕН (data/owen_signatures.toml).

Строка: source, kind (map | wrap | stub | none), target, pins (переименование пинов), source_url,
confidence. Исход C2A-LIB001: map -> auto, wrap -> check, stub/none -> todo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import resources

KINDS = ("map", "wrap", "stub", "none")
OUTCOME_OF_KIND = {"map": "auto", "wrap": "check", "stub": "todo", "none": "todo"}


@dataclass(frozen=True)
class Entry:
    library: str
    namespace: str
    source: str
    kind: str
    target: str | None
    source_url: str
    confidence: str
    note: str = ""
    pins: tuple[tuple[str, str], ...] = ()

    @property
    def outcome(self) -> str:
        return OUTCOME_OF_KIND[self.kind]


@dataclass
class LibMap:
    entries: list[Entry] = field(default_factory=list)
    libraries: dict[str, dict[str, Any]] = field(default_factory=dict)
    signatures: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def by_namespace(self) -> dict[str, str]:
        """Пространство имён -> библиотека (OSU -> OwenStringUtils)."""
        return {v["namespace"].lower(): k for k, v in self.libraries.items() if v.get("namespace")}

    def find(self, library: str, name: str) -> Entry | None:
        low = name.lower()
        lib = library.lower()
        for e in self.entries:
            if e.library.lower() == lib and (e.source.lower() == low or e.source == "*"):
                return e
        return None

    def find_by_namespace(self, ns: str, name: str) -> Entry | None:
        lib = self.by_namespace().get(ns.lower())
        return self.find(lib, name) if lib else None

    def find_unqualified(self, name: str) -> Entry | None:
        """POU без пространства имён (CODESYS разрешает вызов без префикса, если библиотека не qualified_only)."""
        low = name.lower()
        for e in self.entries:
            if e.source.lower() == low and e.source != "*":
                return e
        return None

    def vendor_library(self, title: str) -> str | None:
        """Библиотека ОВЕН по названию ссылки Library Manager (без версии/компании)."""
        t = title.lower()
        for name in self.libraries:
            if name.lower() == t:
                return name
        for e in self.entries:
            if e.library.lower() == t:
                return e.library
        return None

    def signature(self, library: str, name: str) -> dict[str, Any] | None:
        return self.signatures.get((library.lower(), name.lower()))


def load() -> LibMap:
    lm = LibMap()
    for fname in resources.list_dir("data", "libmap"):
        if not fname.endswith(".toml"):
            continue
        data = resources.read_toml("data", "libmap", fname)
        lib = data.get("library", {})
        lname = str(lib.get("name", fname.removesuffix(".toml")))
        if lib.get("namespace"):
            lm.libraries[lname] = dict(lib)
        for row in data.get("pou", []):
            kind = str(row["kind"])
            if kind not in KINDS:
                raise ValueError(f"{fname}: kind {kind!r} не из {KINDS}")
            if not row.get("source_url"):
                raise ValueError(f"{fname}: {row.get('source')}: нет source_url")
            pins = tuple(sorted((str(k), str(v)) for k, v in dict(row.get("pins", {})).items()))
            lm.entries.append(
                Entry(
                    library=str(row.get("library", lname)),
                    namespace=str(lib.get("namespace", "")),
                    source=str(row["source"]),
                    kind=kind,
                    target=row.get("target"),
                    source_url=str(row["source_url"]),
                    confidence=str(row.get("confidence", "M")),
                    note=str(row.get("note", "")),
                    pins=pins,
                )
            )
    sig = resources.read_toml("data", "owen_signatures.toml")
    for p in sig.get("pou", []):
        lm.signatures[(str(p["library"]).lower(), str(p["name"]).lower())] = dict(p)
    return lm
