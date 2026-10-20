"""Модель трудоёмкости семейства (00-INDEX §4.3): треугольное распределение минут на находку, находки
независимы, Монте-Карло 10 000 проб, seed 20261019; итог — P50/P90 в часах по проекту и по POU.

Генератор — свой линейный конгруэнтный (MMIX, Кнут) поверх целых: числа одинаковы в CPython и Pyodide
и не зависят от версии `random`. Подпись в отчёте — «модель», с источником калибровки.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from . import resources
from .findings import Finding

_A = 6364136223846793005
_C = 1442695040888963407
_M = 2**64


class Lcg:
    def __init__(self, seed: int) -> None:
        self.state = seed % _M

    def random(self) -> float:
        self.state = (_A * self.state + _C) % _M
        return (self.state >> 11) / float(1 << 53)


def triangular(u: float, lo: float, mode: float, hi: float) -> float:
    if hi <= lo:
        return lo
    c = (mode - lo) / (hi - lo)
    if u < c:
        return lo + math.sqrt(u * (hi - lo) * (mode - lo))
    return hi - math.sqrt((1 - u) * (hi - lo) * (hi - mode))


@dataclass
class Effort:
    model: str
    runs: int
    seed: int
    p50_h: float
    p90_h: float
    calibrated: bool
    calibration: str
    by_pou: dict[str, tuple[float, float]] = field(default_factory=dict)
    by_rule_minutes: dict[str, float] = field(default_factory=dict)  # сумма mode по правилу (для графика)


def table() -> dict[str, object]:
    return resources.read_toml("data", "effort.toml")


def minutes_for(f: Finding, eff: dict[str, object]) -> tuple[float, float, float]:
    rules = eff.get("rules", {})
    assert isinstance(rules, dict)
    default = eff["default"]
    assert isinstance(default, dict)
    row = rules.get(f.rule, {})
    tri = row.get(f.outcome) if isinstance(row, dict) else None
    if tri is None:
        tri = default[f.outcome]
    lo, mode, hi = (float(x) for x in tri)
    k = float(eff.get("calibration_factor", 1.0))  # type: ignore[arg-type]
    return lo * k, mode * k, hi * k


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    idx = min(len(vs) - 1, max(0, math.ceil(q * len(vs)) - 1))
    return vs[idx]


def estimate(findings: Sequence[Finding], runs: int | None = None, seed: int | None = None) -> Effort:
    eff = table()
    n_runs = runs if runs is not None else int(str(eff.get("runs", 10000)))
    n_seed = seed if seed is not None else int(str(eff.get("seed", 20261019)))
    tris = [minutes_for(f, eff) for f in findings]
    by_rule: dict[str, float] = {}
    for f, (_lo, mode, _hi) in zip(findings, tris, strict=True):
        by_rule[f.rule] = by_rule.get(f.rule, 0.0) + mode
    rng = Lcg(n_seed)
    pou_names = sorted({f.pou or "(проект)" for f in findings})
    totals: list[float] = []
    per_pou: dict[str, list[float]] = {p: [] for p in pou_names}
    active = [(f.pou or "(проект)", t) for f, t in zip(findings, tris, strict=True) if t[2] > 0]
    for _ in range(n_runs):
        total = 0.0
        acc = dict.fromkeys(pou_names, 0.0)
        for pou, (lo, mode, hi) in active:
            v = triangular(rng.random(), lo, mode, hi)
            total += v
            acc[pou] += v
        totals.append(total)
        for p in pou_names:
            per_pou[p].append(acc[p])
    return Effort(
        model="triangular-mc",
        runs=n_runs,
        seed=n_seed,
        p50_h=round(_quantile(totals, 0.5) / 60.0, 2),
        p90_h=round(_quantile(totals, 0.9) / 60.0, 2),
        calibrated=bool(eff.get("calibrated", False)),
        calibration=str(eff.get("calibration", "")),
        by_pou={
            p: (round(_quantile(v, 0.5) / 60.0, 2), round(_quantile(v, 0.9) / 60.0, 2)) for p, v in per_pou.items()
        },
        by_rule_minutes={k: round(v, 1) for k, v in sorted(by_rule.items())},
    )
