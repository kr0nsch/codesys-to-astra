"""Профили IDE: цель (Astra.IDE 1.7.2.2) и источники (ОВЕН SP17, CODESYS SP18+).

Значение профиля — таблица с `value`, `status`, `source`, `date` (и `since`, `conflict`, `note`).
Статусы: documented | observed_in_sample | verified_local | owner_verified | unknown. Правила берут
значения только отсюда: копия профиля с другим значением меняет вывод без правки кода (тест).

`probe_profile_xml` разбирает `Profiles/*.profile.xml` IDE (CODESYS и Astra.IDE) и достаёт версии
компилятора и PLCopenXML — `cds2astra probe --ide-profile` сверяет их с профилем.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from . import resources
from . import xmltree as X

STATUSES = ("documented", "observed_in_sample", "verified_local", "owner_verified", "unknown")
DESCRIBED = ("documented", "observed_in_sample", "verified_local", "owner_verified")

COMPILER_PLUGIN = "973a3934-1ec6-4770-83a4-59677803015a"  # «Compiler for the compiler Version 3.5.17.0»
PLCOPEN_PLUGIN = "108e8974-276a-4f0c-9865-280e52999083"  # «PLCopenXML»


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class PValue:
    key: str
    value: Any
    status: str
    source: str
    date: str = ""
    extra: tuple[tuple[str, Any], ...] = ()

    @property
    def described(self) -> bool:
        return self.status in DESCRIBED

    def get(self, name: str, default: Any = None) -> Any:
        for k, v in self.extra:
            if k == name:
                return v
        return default


@dataclass
class Profile:
    id: str
    kind: str
    title: str
    meta: dict[str, Any]
    values: dict[str, PValue] = field(default_factory=dict)

    def __getitem__(self, key: str) -> PValue:
        if key not in self.values:
            raise KeyError(f"профиль {self.id}: нет значения {key}")
        return self.values[key]

    def value(self, key: str, default: Any = None) -> Any:
        pv = self.values.get(key)
        return default if pv is None else pv.value

    def status(self, key: str) -> str:
        pv = self.values.get(key)
        return "unknown" if pv is None else pv.status

    def described(self, key: str) -> bool:
        pv = self.values.get(key)
        return pv is not None and pv.described


def _walk(table: dict[str, Any], prefix: str) -> Iterator[tuple[str, dict[str, Any]]]:
    for k, v in table.items():
        if not isinstance(v, dict):
            continue
        key = f"{prefix}{k}"
        if "status" in v:
            yield key, v
        else:
            yield from _walk(v, key + ".")


def parse(text: str, name: str = "<профиль>") -> Profile:
    data = tomllib.loads(text)
    for req in ("id", "kind", "title"):
        if req not in data:
            raise ProfileError(f"{name}: нет поля {req}")
    meta = {k: v for k, v in data.items() if not isinstance(v, dict)}
    prof = Profile(str(data["id"]), str(data["kind"]), str(data["title"]), meta)
    for key, v in _walk(data, ""):
        status = v.get("status")
        if status not in STATUSES:
            raise ProfileError(f"{name}: {key}: статус {status!r} не из {STATUSES}")
        if "value" not in v:
            raise ProfileError(f"{name}: {key}: нет value")
        source = str(v.get("source", ""))
        if status == "documented" and "http" not in source:
            raise ProfileError(f"{name}: {key}: у documented нет URL в source")
        if status != "unknown" and not v.get("date"):
            raise ProfileError(f"{name}: {key}: нет даты")
        extra = tuple(sorted((k, val) for k, val in v.items() if k not in ("value", "status", "source", "date")))
        prof.values[key] = PValue(key, v["value"], str(status), source, str(v.get("date", "")), extra)
    return prof


def builtin_names() -> list[str]:
    return [n for n in resources.list_dir("profiles") if n.endswith(".toml")]


def load_builtin(name_or_id: str) -> Profile:
    for fname in builtin_names():
        text = resources.read_text("profiles", fname)
        prof = parse(text, fname)
        if name_or_id in (prof.id, fname, fname.removesuffix(".toml")):
            return prof
    raise ProfileError(f"нет встроенного профиля {name_or_id!r}")


def load(spec: str, text: str | None = None) -> Profile:
    """Встроенный профиль по id или содержимое файла (text) — для подмены профиля пользователем."""
    if text is not None:
        return parse(text, spec)
    return load_builtin(spec)


def all_builtin() -> list[Profile]:
    return [parse(resources.read_text("profiles", n), n) for n in builtin_names()]


def diff(a: Profile, b: Profile) -> list[tuple[str, Any, Any]]:
    out: list[tuple[str, Any, Any]] = []
    for key in sorted(set(a.values) | set(b.values)):
        va = a.values[key].value if key in a.values else None
        vb = b.values[key].value if key in b.values else None
        if va != vb:
            out.append((key, va, vb))
    return out


def probe_profile_xml(raw: bytes) -> dict[str, str]:
    """Profiles/*.profile.xml -> {'compiler': '3.5.17.30', 'plcopenxml': '3.5.17.20'} (что найдено)."""
    doc = X.parse(raw)
    found: dict[str, str] = {}
    for el in doc.root.iter():
        if el.tag != "Exact":
            continue
        plug = el.child("PlugIn")
        if plug is None:
            continue
        guid = plug.text.strip().lower()
        if guid == COMPILER_PLUGIN:
            found["compiler"] = el.attrs.get("Version", "")
        elif guid == PLCOPEN_PLUGIN:
            found["plcopenxml"] = el.attrs.get("Version", "")
    return found


def check_probe(prof: Profile, found: dict[str, str]) -> list[str]:
    """Расхождения версий из profile.xml IDE с профилем (пустой список — совпадают)."""
    problems = []
    for key in ("compiler", "plcopenxml"):
        want = prof.value(key)
        got = found.get(key)
        if got is None:
            problems.append(f"{key}: в profile.xml не найден")
        elif want != got:
            problems.append(f"{key}: в профиле {want}, в IDE {got}")
    return problems
