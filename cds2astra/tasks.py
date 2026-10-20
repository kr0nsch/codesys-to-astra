"""Переназначение приоритетов задач для REGUL (C2A-TASK001), детерминированно — PROMPT §7.5.

1. Задачи визуализации (VISU_TASK и аналоги по имени) получают 15.
2. При резервировании синхронизируемая задача (sync_task из target-spec или циклическая с наивысшим
   приоритетом) получает 1 (ЦП I/III) или 4 (ЦП II).
3. Полоса для остальных: 2–13 (без резервирования или I/III), 5–13 (II с резервированием); 14 автоматически
   не назначается.
4. Остальные задачи сортируются по (приоритет источника, имя); различные уровни получают ранги 0..k−1.
   При k ≤ ширины полосы приоритет = начало + ранг, иначе начало + floor(ранг·ширина/k); совпадения
   разных исходных уровней — check с перечнем.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .profiles import Profile

_VISU_RE = re.compile(r"visu", re.IGNORECASE)


@dataclass
class TaskIn:
    name: str
    priority: int | None
    kind: str = "Cyclic"
    interval_ms: float | None = None


@dataclass
class TaskOut:
    name: str
    before: int | None
    after: int
    reason: str
    collision: bool = False


def reassign(
    tasks: list[TaskIn],
    profile: Profile,
    redundancy: bool = False,
    cpu_type: str = "I",
    sync_task: str | None = None,
) -> list[TaskOut]:
    visu_prio = int(profile.value("tasks.visu", 15))
    type2 = cpu_type == "II" and redundancy
    band_start = int(profile.value("tasks.type2_band_start" if type2 else "tasks.band_start", 5 if type2 else 2))
    band_end = int(profile.value("tasks.band_end", 13))
    sync_prio = int(profile.value("tasks.type2_sync" if cpu_type == "II" else "tasks.redundancy_sync", 1))
    default = int(profile.value("tasks.priority_default", 2))
    out: dict[str, TaskOut] = {}
    rest: list[TaskIn] = []
    for t in tasks:
        if _VISU_RE.search(t.name):
            out[t.name] = TaskOut(t.name, t.priority, visu_prio, "визуализация")
    if redundancy:
        candidates = [t for t in tasks if t.name not in out]
        chosen = None
        if sync_task:
            chosen = next((t for t in candidates if t.name.lower() == sync_task.lower()), None)
        if chosen is None:
            cyc = [t for t in candidates if t.kind.lower() == "cyclic"]
            if cyc:
                chosen = sorted(cyc, key=lambda t: (t.priority if t.priority is not None else default, t.name))[0]
        if chosen is not None:
            out[chosen.name] = TaskOut(
                chosen.name, chosen.priority, sync_prio, "синхронизируемая задача резервирования"
            )
    rest = [t for t in tasks if t.name not in out]
    levels = sorted({t.priority if t.priority is not None else default for t in rest})
    width = band_end - band_start + 1
    k = len(levels)
    rank_of = {lvl: i for i, lvl in enumerate(levels)}
    new_of: dict[int, int] = {}
    if levels and all(band_start <= lvl <= band_end for lvl in levels):
        # уточнение алгоритма (docs/ASSUMPTIONS.md A7): уровни источника уже в полосе цели — без изменений
        new_of = {lvl: lvl for lvl in levels}
    for lvl, r in rank_of.items():
        if lvl in new_of:
            continue
        new_of[lvl] = band_start + r if k <= width else band_start + (r * width) // k
    used: dict[int, set[int]] = {}
    for lvl, new in new_of.items():
        used.setdefault(new, set()).add(lvl)
    for t in sorted(rest, key=lambda t: (t.priority if t.priority is not None else default, t.name)):
        lvl = t.priority if t.priority is not None else default
        new = new_of[lvl]
        collision = len(used[new]) > 1
        reason = "полоса реального времени, порядок сохранён" if not collision else "сжатие полосы: совпадение уровней"
        out[t.name] = TaskOut(t.name, t.priority, new, reason, collision)
    return [out[t.name] for t in tasks]
