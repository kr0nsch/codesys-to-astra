#!/usr/bin/env python3
"""Порог покрытия cds2astra (PROMPT §8): строки >= 85 %, ветви >= 75 % по coverage.json pytest-cov.

python -m pytest cds2astra/tests --cov=cds2astra --cov-branch --cov-report=json:build/coverage.json
python tools/check/coverage_gate.py build/coverage.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LINES_MIN = 85.0
BRANCHES_MIN = 75.0


def main(argv: list[str]) -> int:
    path = Path(argv[1] if len(argv) > 1 else "build/coverage.json")
    totals = json.loads(path.read_text(encoding="utf-8"))["totals"]
    lines = 100.0 * totals["covered_lines"] / max(totals["num_statements"], 1)
    branches = 100.0 * totals["covered_branches"] / max(totals["num_branches"], 1)
    ok = lines >= LINES_MIN and branches >= BRANCHES_MIN
    print(
        f"покрытие: строки {lines:.1f} % (порог {LINES_MIN}), ветви {branches:.1f} % (порог {BRANCHES_MIN}) — "
        + ("OK" if ok else "НИЖЕ ПОРОГА")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
